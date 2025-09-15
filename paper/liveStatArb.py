from paperInterface import PaperBroker
import yfinance as yf
from statArbClass import StatisticalArbitrage
import time
import alpaca_trade_api as tradeapi


entry = 2.0
exit = 0.5
all_symbols = [['MCD', 'YUM'], ['PEP', 'KO'], ['GS', 'MS'],
               ['JPM', 'BAC'], ['SPY', 'IVV'], ['XOM', 'CVX']]
wait_time = 300
start = None
end = None
inter = '1h'
broker = PaperBroker('Statistical_Arbitrage')
print(broker.cash)
algo = StatisticalArbitrage(broker.cash/len(all_symbols), broker.positions)

# Alpaca stuff
API_KEY = ''
SECRET_KEY = ''
BASE_URL = 'https://paper-api.alpaca.markets'
api = tradeapi.REST(API_KEY, SECRET_KEY, base_url=BASE_URL)


def price_lookup(tkr, retries=3, delay=5):
    for i in range(retries):
        try:
            stock = yf.Ticker(tkr)
            return stock.info['regularMarketPrice']
        except Exception as e:
            print(
                f"[{tkr}] Price lookup failed ({e}) — retrying ({i+1}/{retries})...")
            time.sleep(delay)
    print(f"[{tkr}] Failed after {retries} retries.")
    return None


def get_latest_price(symbol):
    bar = api.get_latest_bar(symbol)
    return bar.c  # 'c' is the close price


def close_pair(sym1, sym2):
    for pos in api.list_positions():
        if pos.symbol in [sym1, sym2]:
            side = 'sell' if int(pos.qty) > 0 else 'buy'
            api.submit_order(
                symbol=pos.symbol,
                qty=abs(int(pos.qty)),
                side=side,
                type='market',
                time_in_force='gtc'
            )


def trade(symbols):
    sym1, sym2 = symbols
    # live_price1 = price_lookup(sym1)
    # live_price2 = price_lookup(sym2)

    # with alpaca to make it a little more accurate
    live_price1 = get_latest_price(sym1)
    live_price2 = get_latest_price(sym2)

    if live_price1 is None or live_price2 is None:
        print(f"Skipping {sym1}/{sym2} due to price lookup failure.")
        return
    result = algo.run(entry, exit, symbols, live_price1, live_price2)
    if len(result) == 1:
        if result[0] == "HOLD":
            print(f"{sym1}/{sym2} : HOLD")
        else:
            close_pair(sym1, sym2)
            for symbol in [sym1, sym2]:
                for side in ['long', 'short']:
                    pos = broker.get_position(symbol, side)
                    if pos:  # Only close if a position exists

                        broker.close_position(
                            symbol, side, pos.units, live_price1 if symbol == sym1 else live_price2)
    else:
        trade1 = result[0]
        trade2 = result[1]
        broker.open_position(sym1, trade1['side'], trade1['qty'], live_price1)
        broker.open_position(sym2, trade2['side'], trade2['qty'], live_price2)
        trades = [trade1, trade2]
        for x in trades:
            if x['side'] == 'short':
                x['side'] = 'sell'
            else:
                x['side'] = 'buy'
        api.submit_order(
            symbol=sym1, qty=trade1['qty'], side=trade1['side'], type='market', time_in_force='gtc')
        api.submit_order(
            symbol=sym2, qty=trade2['qty'], side=trade2['side'], type='market', time_in_force='gtc')


while True:
    for x in all_symbols:
        trade(x)
        print()
    broker.exit()
    print('=' * 50)
    print()
    time.sleep(wait_time)

