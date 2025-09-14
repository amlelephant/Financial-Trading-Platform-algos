import yfinance as yf
import statsmodels.api as sm
import time
import pandas as pd


class StatisticalArbitrage:
    def __init__(self, cash, positions):
        self.positions = positions
        self.cash = cash

    def in_market(self, tkr1, tkr2):
        for pos in self.positions:
            if pos.tkr == tkr1 or pos.tkr == tkr2:
                return True
        return False

    def can_afford(self, cash, trade1, trade2):
        def trade_cost(side, qty, price):
            cost = qty * price
            return cost if side == 'long' else -cost  # short sells add cash

        cost1 = trade_cost(trade1['side'], trade1['qty'], trade1['price'])
        cost2 = trade_cost(trade2['side'], trade2['qty'], trade2['price'])
        print(cost1, cost2)
        total_cost = cost1 + cost2
        return (cash >= total_cost, total_cost)

    def safe_download(symbols, period='10d', interval='5m', retries=3, delay=2):
        for attempt in range(retries):
            try:
                data = yf.download(
                    symbols,
                    period=period,
                    interval=interval,
                    auto_adjust=False,
                    progress=False,
                    group_by='ticker'
                )

                # Ensure we return only the adjusted close values
                if isinstance(symbols, list) and len(symbols) > 1:
                    # Multiple symbols
                    adj_close = pd.concat(
                        [data[sym]['Adj Close']
                            for sym in symbols if sym in data],
                        axis=1,
                        keys=[sym for sym in symbols if sym in data]
                    )
                else:
                    # Single symbol
                    adj_close = data['Adj Close'].to_frame()

                # Drop rows with any NaNs
                adj_close = adj_close.dropna()

                if not adj_close.empty:
                    return adj_close
                else:
                    raise ValueError(
                        "Downloaded data is empty or full of NaNs")

            except Exception as e:
                print(
                    f"[Attempt {attempt+1}/{retries}] Failed to download data for {symbols}: {e}")
                time.sleep(delay)

        print(f"Final failure: Could not download data for {symbols}")
        return None

    def run(self, entry, exit, symbols, live_price1, live_price2):

        # ======= Download Data =======
        data = yf.download(symbols, period='10d', interval='5m',
                           auto_adjust=False, progress=False)['Adj Close']
        # data = self.safe_download(symbols)
        adj_close = data.dropna()

        # ======= Safety Check =======
        if len(symbols) != 2:
            raise ValueError(
                "This strategy only works with exactly 2 symbols.")

        sym1, sym2 = symbols[0], symbols[1]

        # ======= Regression =======
        regression_data = adj_close[[sym1, sym2]].dropna()
        X = sm.add_constant(regression_data[sym2])
        y = regression_data[sym1]

        model = sm.OLS(y, X).fit()
        hedge_ratio = model.params[sym2]

        shares_to_trade = int(self.cash / live_price1)

        if live_price1 is None or live_price2 is None:
            print(f"Skipping {sym1}, {sym2} due to missing live price.")
            return

        # ======= Spread & Z-score Calculation (with live price) =======
        spread_series = regression_data[sym1] - \
            hedge_ratio * regression_data[sym2]
        spread_mean = spread_series.mean()
        spread_std = spread_series.std()

        latest_spread = live_price1 - hedge_ratio * live_price2
        zscore = (latest_spread - spread_mean) / spread_std

        print(
            f"({sym1}[{live_price1}]/{sym2}[{live_price2}]) Hedge Ratio: {hedge_ratio:.4f}, Z-score: {zscore:.4f}")

        in_mkt = self.in_market(sym1, sym2)

        if zscore > entry and not in_mkt:
            print("SHORT Spread")

            trade1 = {'side': 'short', 'qty': shares_to_trade,
                      'price': live_price1}  # sym1
            trade2 = {'side': 'long',  'qty': int(
                shares_to_trade * abs(hedge_ratio)), 'price': live_price2}

            can_trade, cost = self.can_afford(self.cash, trade1, trade2)

            return [trade1, trade2]

            if can_trade:
                return [trade1, trade2]
            else:
                print("Cannot afford trade")
                return ([None])

        elif zscore < -entry and not in_mkt:
            print("LONG Spread")
            trade1 = {'side': 'long', 'qty': shares_to_trade,
                      'price': live_price1}  # sym1
            trade2 = {'side': 'short',  'qty': int(
                shares_to_trade * abs(hedge_ratio)), 'price': live_price2}

            can_trade, cost = self.can_afford(self.cash, trade1, trade2)

            if can_trade:
                return [trade1, trade2]
            else:
                print("Cannot afford trade")

        elif abs(zscore) < exit and in_mkt:
            return ["EXIT"]

        else:
            return ["HOLD"]

    def backTest(self, start, end, sym1, sym2):
        d = yf.download([sym1, sym2], start=start, end=end, interval='1h',
                        auto_adjust=False, progress=False)['Adj Close'].dropna()
