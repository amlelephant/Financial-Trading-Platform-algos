from paperInterface import PaperBroker
import yfinance as yf
import statsmodels.api as sm
import numpy as np
import time

broker = PaperBroker()

all_symbols = [['GS', 'MS'], ['KO', 'PEP']]
entry_threshold = 1.7
exit_threshold = 0.5
bars_to_use = 200
start_date = "2024-01-01"
end_date = "2025-07-09"
shares_to_trade = 1
cash = (broker.get_balance()/2) / len(all_symbols)

wait_time = 60


def get_latest_price(sym):
    ticker = yf.Ticker(sym)
    data = ticker.history(period="1d", interval="1m")
    return data['Close'].dropna().iloc[-1]


def in_market(tkr1, tkr2):
    for pos in broker.positions:
        if pos.tkr == tkr1 or pos.tkr == tkr2:
            return True
    return False


def can_afford(cash, trade1, trade2):
    def trade_cost(side, qty, price):
        cost = qty * price
        return cost if side == 'long' else -cost  # short sells add cash

    cost1 = trade_cost(trade1['side'], trade1['qty'], trade1['price'])
    cost2 = trade_cost(trade2['side'], trade2['qty'], trade2['price'])

    total_cost = cost1 + cost2
    return (cash >= total_cost, total_cost)


def run(entry, exit, symbols):
    global sym1, sym2, hedge_ratio, adj_close, spread_z

    # ======= Download Data =======
    data = yf.download(symbols, period="10d", interval='5m',
                       auto_adjust=False, progress=False)['Adj Close']
    adj_close = data.dropna()

    # ======= Safety Check =======
    if len(symbols) != 2:
        raise ValueError("This strategy only works with exactly 2 symbols.")

    sym1, sym2 = symbols[0], symbols[1]

    # ======= Regression =======
    regression_data = adj_close[[sym1, sym2]].dropna()
    X = sm.add_constant(regression_data[sym2])
    y = regression_data[sym1]

    model = sm.OLS(y, X).fit()
    hedge_ratio = model.params[sym2]

    # ======= Live Price Update =======
    live_price1 = get_latest_price(sym1)
    live_price2 = get_latest_price(sym2)

    shares_to_trade = cash / live_price1

    if live_price1 is None or live_price2 is None:
        print(f"Skipping {sym1}, {sym2} due to missing live price.")
        return

    # ======= Spread & Z-score Calculation (with live price) =======
    spread_series = regression_data[sym1] - hedge_ratio * regression_data[sym2]
    spread_mean = spread_series.mean()
    spread_std = spread_series.std()

    latest_spread = live_price1 - hedge_ratio * live_price2
    zscore = (latest_spread - spread_mean) / spread_std

    print(
        f"({sym1}[{live_price1}]/{sym2}[{live_price2}]) Hedge Ratio: {hedge_ratio:.4f}, Z-score: {zscore:.4f}")

    in_mkt = in_market(sym1, sym2)

    if zscore > entry and not in_mkt:
        print("SHORT Spread")

        trade1 = {'side': 'short', 'qty': shares_to_trade,
                  'price': live_price1}  # sym1
        trade2 = {'side': 'long',  'qty': int(
            shares_to_trade * abs(hedge_ratio)), 'price': live_price2}

        can_trade, cost = can_afford(broker.cash, trade1, trade2)

        if can_trade:
            broker.open_position(sym1, 'short', trade1['qty'], live_price1)
            broker.open_position(sym2, 'long',  trade2['qty'], live_price2)
        else:
            print("Cannot afford trade")

    elif zscore < -entry and not in_mkt:
        print("LONG Spread")
        trade1 = {'side': 'long', 'qty': shares_to_trade,
                  'price': live_price1}  # sym1
        trade2 = {'side': 'short',  'qty': int(
            shares_to_trade * abs(hedge_ratio)), 'price': live_price2}

        can_trade, cost = can_afford(broker.cash, trade1, trade2)

        if can_trade:
            broker.open_position(sym1, 'long', trade1['qty'], live_price1)
            broker.open_position(sym2, 'short',  trade2['qty'], live_price2)
        else:
            print("Cannot afford trade")

    elif abs(zscore) < exit and in_mkt:
        print("EXIT")

        for symbol in [sym1, sym2]:
            for side in ['long', 'short']:
                pos = broker.get_position(symbol, side)
                if pos:  # Only close if a position exists
                    broker.close_position(
                        symbol, side, pos.units, live_price1 if symbol == sym1 else live_price2)

    else:
        print("HOLD")


while True:
    for sym in all_symbols:
        run(entry_threshold, exit_threshold, sym)
    broker.exit()
    time.sleep(wait_time)
