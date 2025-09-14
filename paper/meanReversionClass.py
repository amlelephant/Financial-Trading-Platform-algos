import yfinance as yf


class meanReversion:
    def __init__(self, tkr):
        self.df = yf.download(tkr, period='60d', interval='30m',
                              auto_adjust=False, progress=False)
        self.tkr = tkr

    def run(self, price, band_multiplier, sma_window, stop_loss, take_profit, cash, position, entry_price, shares):
        data = self.df.copy()
        data['sma'] = data['Close'].rolling(window=sma_window).mean()
        data['std'] = data['Close'].rolling(window=sma_window).std()
        data['upper'] = data['sma'] + band_multiplier * data['std']
        data['lower'] = data['sma'] - band_multiplier * data['std']
        data = data.dropna()

        lower = data['lower'][-1]
        upper = data['upper'][-1]
        sma = data['sma'][-1]

        shares_to_trade = cash // price

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
            trade = {'side': 'long', 'qty': shares_to_trade,
                     'price': price}  # sym1
            return trade
            # print(f"[{date.date()}] BUY @ {price:.2f}")

            # Sell Signal
        elif position is None and price > upper:
            trade = {'side': 'short', 'qty': shares_to_trade,
                     'price': price}  # sym1
            return trade

            # print(f"[{date.date()}] SHORT @ {price:.2f}")

        # Close Long
        elif (position == 'long' and price >= sma) or (sell and position == 'long'):
            return 'EXIT'

        # Close Short
        elif (position == 'short' and price <= sma) or (sell and position == 'short'):
            return 'EXIT'

        return 'HOLD'
