from meanReversionClass import meanReversion
from paperInterface import PaperBroker
import yfinance as yf
import time
import alpaca_trade_api as tradeapi
from meanReversionBacktestClass import Backtest

broker = PaperBroker('Mean_Reversion')

all_symbols = ['PEP', 'KO', 'GS', 'MS', 'JPM', 'BAC']
# all_symbols = ['GS']

algos = []

for sym in all_symbols:
    algos.append(meanReversion(sym))

full_params = []

for sym in all_symbols:
    result = Backtest.run_On_tkr(sym)
    inx = all_symbols.index(sym)
    result['algo'] = algos[inx]
    full_params.append(result)
    print('='*50)
    print(f"tkr: {sym}")
    for key, value in result.items():
        print(f"{key}: {value}")

wait_time = 60
cash = broker.cash
position = None
positions = broker.positions
entry = 0
shares = 0

# Alpaca stuff
API_KEY = 'PK9JPD2GEODC258EU0T7'
SECRET_KEY = 'QgOomZbX97g762LSmfwfTHCBkLmAWV48zHLpew22'
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


def close(sym1):
    for pos in api.list_positions():
        if pos.symbol in [sym1]:
            side = 'sell' if int(pos.qty) > 0 else 'buy'
            api.submit_order(
                symbol=pos.symbol,
                qty=abs(int(pos.qty)),
                side=side,
                type='market',
                time_in_force='gtc'
            )


def trade(tkr, algo, band_multiplier, sma_window, stop_loss, take_profit):
    # live_price = price_lookup(tkr)

    # alpaca price for more accuracy
    live_price = get_latest_price(tkr)

    result = algo.run(live_price, band_multiplier, sma_window,
                      stop_loss, take_profit, (cash / len(all_symbols)), position, entry, shares)
    if result == 'HOLD':
        print(f"{tkr}[{live_price}]: HOLD")
    elif result == 'EXIT':
        print(f"{tkr}[{live_price}]: EXIT")
        broker.close_position(tkr, position, shares, live_price)
        close(tkr)
    else:
        broker.open_position(tkr, result['side'], result['qty'], live_price)
        if result['side'] == 'short':
            result['side'] = 'sell'
        else:
            result['side'] = 'buy'
        api.submit_order(
            symbol=tkr, qty=result['qty'], side=result['side'], type='market', time_in_force='gtc')


while True:
    print('=' * 50)
    print()
    for algo in full_params:
        for pos in positions:
            if pos.tkr == algo['algo'].tkr:
                position = pos.side
                entry = pos.costBasis
                shares = pos.units
        trade(algo['algo'].tkr, algo['algo'], algo['band_multiplier'],
              algo['sma'], algo['stop_loss'], algo['take_profit'])
        shares = 0
        position = None
        entry = 0
        print()

    broker.exit()
    time.sleep(wait_time)
