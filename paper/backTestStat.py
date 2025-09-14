import matplotlib.pyplot as plt
import yfinance as yf
import statsmodels.api as sm
import pandas as pd
import numpy as np

# === Config ===
# sym1 = 'GS'
# sym2 = 'MS'
all_symbols = [['MCD', 'YUM'], ['PEP', 'KO'], ['GS', 'MS'],
               ['JPM', 'BAC'], ['SPY', 'IVV'], ['XOM', 'CVX']]
# all_symbols = [['PEP', 'KO'], ['GS', 'MS']]
start_date = '2024-01-01'
end_date = '2025-07-01'
entry_threshold = 2.0
exit_threshold = 0.5
lookback = 50

# === Initialize state ===
positions = []
cash = 100000
portfolio_value = []
open_position = None  # None / 'long_sym1' / 'short_sym1'
dollar_exposure = cash / len(all_symbols)

# === Download 5-minute historical data ===


def runOnTkr(sym1, sym2):
    global cash, portfolio_value, positions

    data = yf.download([sym1, sym2], start=start_date, end=end_date,
                       interval='1h', auto_adjust=False, progress=False)['Adj Close'].dropna()

    print(f"Loaded {len(data)} bars of 1-hour data for {sym1}/{sym2}")

    def calculate_hedge_ratio(y, x):
        X = sm.add_constant(x)
        model = sm.OLS(y, X).fit()
        return model.params[1]

    # Pair-specific state
    open_position = None
    entry_price1 = 0
    entry_price2 = 0

    for i in range(lookback, len(data)):
        window = data.iloc[i - lookback:i]
        price1 = data[sym1].iloc[i]
        price2 = data[sym2].iloc[i]
        timestamp = data.index[i]

        hedge_ratio = calculate_hedge_ratio(window[sym1], window[sym2])
        spread = window[sym1] - hedge_ratio * window[sym2]
        mean_spread = spread.mean()
        std_spread = spread.std()
        current_spread = price1 - hedge_ratio * price2
        zscore = (current_spread - mean_spread) / std_spread

        shares_to_trade = dollar_exposure / price1

        # Track value (optional: track per-pair portfolio if needed)
        value = cash
        if open_position == 'short_sym1':
            value += (entry_price1 - price1) * shares_to_trade + \
                     (price2 - entry_price2) * \
                int(shares_to_trade * hedge_ratio)
        elif open_position == 'long_sym1':
            value += (price1 - entry_price1) * shares_to_trade + \
                     (entry_price2 - price2) * \
                int(shares_to_trade * hedge_ratio)
        portfolio_value.append((timestamp, value))

        # === Entry ===
        if open_position is None:
            if zscore > entry_threshold:
                open_position = 'short_sym1'
                entry_price1 = price1
                entry_price2 = price2
                positions.append((timestamp, 'SELL', sym1, price1))
                positions.append((timestamp, 'BUY', sym2, price2))

            elif zscore < -entry_threshold:
                open_position = 'long_sym1'
                entry_price1 = price1
                entry_price2 = price2
                positions.append((timestamp, 'BUY', sym1, price1))
                positions.append((timestamp, 'SELL', sym2, price2))

        # === Exit ===
        elif abs(zscore) < exit_threshold:
            if open_position == 'short_sym1':
                pnl = (entry_price1 - price1) * shares_to_trade + \
                      (price2 - entry_price2) * \
                    int(shares_to_trade * hedge_ratio)
                cash += pnl
                positions.append((timestamp, 'BUY', sym1, price1))
                positions.append((timestamp, 'SELL', sym2, price2))

            elif open_position == 'long_sym1':
                pnl = (price1 - entry_price1) * shares_to_trade + \
                      (entry_price2 - price2) * \
                    int(shares_to_trade * hedge_ratio)
                cash += pnl
                positions.append((timestamp, 'SELL', sym1, price1))
                positions.append((timestamp, 'BUY', sym2, price2))

            open_position = None


for x in all_symbols:
    runOnTkr(x[0], x[1])

# === Results ===
df_positions = pd.DataFrame(
    positions, columns=['Time', 'Side', 'Symbol', 'Price'])
df_value = pd.DataFrame(portfolio_value, columns=['Time', 'Portfolio Value'])

print("\nFinal Cash:", round(cash, 2))
print("Final Portfolio Value:", round(df_value['Portfolio Value'].iloc[-1], 2))
print("\nTrade Log:")
print(df_positions.tail(10))

# Optional: Plot portfolio value
df_value.set_index('Time')['Portfolio Value'].plot(
    figsize=(12, 5), title='Portfolio Value Over Time')
plt.ylabel("Portfolio Value ($)")
plt.xlabel("Time")
plt.grid()
plt.tight_layout()
plt.show()
