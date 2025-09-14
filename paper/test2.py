import matplotlib.pyplot as plt
import yfinance as yf
import statsmodels.api as sm
import pandas as pd
import numpy as np

# === Config ===

start_date = '2024-01-01'
end_date = '2025-07-01'
entry_threshold = 2.0
exit_threshold = 0.5
lookback = 50
shares_to_trade = 10
all_symbols = [['MCD', 'YUM'], ['PEP', 'KO'], ['GS', 'MS'],
               ['JPM', 'BAC'], ['SPY', 'IVV'], ['XOM', 'CVX']]
# all_symbols = [['GS', 'MS']]
# === Initialize state ===
positions = []
cash = 100000
portfolio_value = []
open_position = None  # None / 'long_sym1' / 'short_sym1'
dollar_exposure = cash / len(all_symbols)

# === Helper ===


def download_data(sym1, sym2):
    d = yf.download([sym1, sym2], start=start_date, end=end_date, interval='1h',
                    auto_adjust=False, progress=False)['Adj Close'].dropna()
    new_data = {'tkrs': [sym1, sym2], 'data': d}
    all_data.append(new_data)
    print(f"Downloaded {sym1}/{sym2}")


def calculate_hedge_ratio(y, x):
    X = sm.add_constant(x)
    model = sm.OLS(y, X).fit()
    return model.params[1]  # slope only


# === Download 5-minute historical data ===
all_data = []
for x in all_symbols:
    download_data(x[0], x[1])

# === Simulate over each bar ===
for i in range(lookback, len(all_data[0]['data'])):
    for x in all_symbols:
        data = None

        for pair in all_data:
            if pair['tkrs'] == x:
                data = pair['data']
                break

        sym1, sym2 = x

        window = data.iloc[i - lookback:i]
        price1 = data[sym1].iloc[i]
        price2 = data[sym2].iloc[i]
        timestamp = data.index[i]

        shares_to_trade = int(dollar_exposure / price1)

        # Recalculate hedge ratio
        hedge_ratio = calculate_hedge_ratio(window[sym1], window[sym2])

        # Spread + z-score
        spread = window[sym1] - hedge_ratio * window[sym2]
        mean_spread = spread.mean()
        std_spread = spread.std()
        current_spread = price1 - hedge_ratio * price2
        zscore = (current_spread - mean_spread) / std_spread

        # Track value
        value = cash
        if open_position == 'short_sym1':
            value += (entry_price1 - price1) * shares_to_trade + \
                (price2 - entry_price2) * int(shares_to_trade * hedge_ratio)
        elif open_position == 'long_sym1':
            value += (price1 - entry_price1) * shares_to_trade + \
                (entry_price2 - price2) * int(shares_to_trade * hedge_ratio)
        portfolio_value.append((timestamp, value))

        # === Trading logic ===
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

        elif abs(zscore) < exit_threshold:
            if open_position == 'short_sym1':
                pnl = (entry_price1 - price1) * shares_to_trade + \
                    (price2 - entry_price2) * int(shares_to_trade * hedge_ratio)
                cash += pnl
                positions.append((timestamp, 'BUY', sym1, price1))
                positions.append((timestamp, 'SELL', sym2, price2))
            elif open_position == 'long_sym1':
                pnl = (price1 - entry_price1) * shares_to_trade + \
                    (entry_price2 - price2) * int(shares_to_trade * hedge_ratio)
                cash += pnl
                positions.append((timestamp, 'SELL', sym1, price1))
                positions.append((timestamp, 'BUY', sym2, price2))
            open_position = None

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
