import itertools
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt

orig_cash = 100000


class Backtest:

    def run_On_tkr(ticker):

        df = yf.download(ticker, period='60d', interval='30m',
                         auto_adjust=False, progress=False)

        def backtest(sma_window, band_multiplier, take_profit, stop_loss):
            data = df.copy()
            # === Backtest State ===
            position = None  # 'long', 'short', or None
            entry_price = 0
            cash = orig_cash
            shares = 0
            portfolio_values = []
            # === Calculate Bollinger Bands ===
            data['sma'] = data['Close'].rolling(window=sma_window).mean()
            data['std'] = data['Close'].rolling(window=sma_window).std()
            data['upper'] = data['sma'] + band_multiplier * data['std']
            data['lower'] = data['sma'] - band_multiplier * data['std']
            data = data.dropna()

            # === Backtest Logic ===
            for idx, row in data.iterrows():
                price = float(row['Close'])
                upper = float(row['upper'])
                lower = float(row['lower'])
                sma = float(row['sma'])
                date = idx

                change = 0

                if position == 'long':
                    change = (price - entry_price) * shares
                else:
                    change = (entry_price - price) * shares

                sell = False
                if change < stop_loss:
                    sell = True
                if change > take_profit:
                    sell = True

                # Buy Signal
                if position is None and price < lower:
                    position = 'long'
                    entry_price = price
                    shares = cash // price
                    # print(f"[{date.date()}] BUY @ {price:.2f}")

                # Sell Signal
                elif position is None and price > upper:
                    position = 'short'
                    entry_price = price
                    shares = cash // price
                    # print(f"[{date.date()}] SHORT @ {price:.2f}")

                # Close Long
                elif (position == 'long' and price >= sma) or (sell and position == 'long'):
                    profit = (price - entry_price) * shares
                    cash += profit
                    # print(f"[{date.date()}] CLOSE LONG @ {price:.2f}")
                    position = None
                    shares = 0

                # Close Short
                elif (position == 'short' and price <= sma) or (sell and position == 'short'):
                    profit = (entry_price - price) * shares
                    cash += profit
                    # print(f"[{date.date()}] CLOSE SHORT @ {price:.2f}")
                    position = None
                    shares = 0

                # Track portfolio value
                """
                if position == 'long':
                    portfolio_value = cash + shares * price
                elif position == 'short':
                    portfolio_value = cash - shares * price
                else:
                    portfolio_value = cash
                """
                portfolio_value = cash
                portfolio_values.append(
                    {'Date': date, 'Portfolio': portfolio_value})

            # === Results ===
            # print(portfolio_values[-1])
            result_df = portfolio_values[-1]['Portfolio']
            return result_df

        sma_windows = [10, 20, 30, 40]
        band_multipliers = [1.5, 2.0, 2.5]
        take_profits = [200, 500, 800]
        stop_losses = [200, 500, 800]

        parameter_grid = list(itertools.product(
            sma_windows, band_multipliers, take_profits, stop_losses))

        results = []
        for sma, mult, tp, sl in parameter_grid:
            final_value = backtest(sma, mult, tp, sl)
            results.append({
                'sma': sma,
                'band_multiplier': mult,
                'take_profit': tp,
                'stop_loss': sl,
                'final_value': final_value
            })

        top = 0
        inx = 0
        for outcome in results:
            if outcome['final_value'] > top:
                top = outcome['final_value']
                inx = results.index(outcome)

        return (results[inx])


"""
# all_symbols = ['MCD', 'YUM', 'PEP', 'KO', 'GS', 'MS','JPM', 'BAC', 'SPY', 'IVV', 'XOM', 'CVX']
all_symbols = ['GS']

final = []
for sym in all_symbols:
    best = Backtest.run_On_tkr(sym)
    toApp = [sym, best]
    final.append(toApp)
    pct = (all_symbols.index(sym) / len(all_symbols)) * 100
    print(f'Percent Completed: {pct:.2f}%')

for x in final:
    print('='*50)
    print(x[0])
    final_val = x[1]['final_value']
    profit = ((final_val - orig_cash) / orig_cash) * 100
    print(f"Return: {profit:.2f}%")
    for key, value in x[1].items():
        print(f"{key}: {value}")
"""

"""
print(f"\nFinal Portfolio Value: ${result_df['Portfolio'].iloc[-1]:,.2f}")
result_df.plot(title='Bollinger Band Strategy Portfolio Value',
               figsize=(12, 5))
plt.ylabel("Portfolio Value ($)")
plt.grid()
plt.tight_layout()
plt.show()
"""
