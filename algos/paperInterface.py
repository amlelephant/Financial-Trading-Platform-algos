import time
import yfinance as yf


class position:
    def __init__(self, tkr, units, costBasis, timestamp, side):
        self.tkr = tkr
        self.units = units
        self.costBasis = costBasis
        self.timestamp = timestamp
        self.side = side

    def str_data(self):
        return self.tkr + " " + str(self.units) + " " + str(self.costBasis) + " " + self.timestamp + " " + self.side


def price_lookup(tkr):
    stock = yf.Ticker(tkr)
    price = stock.info['regularMarketPrice']
    return price


class PaperBroker:
    def __init__(self, algo):
        self.algo = algo
        try:
            file = open(
                f"PATH TO BALANCE\\{algo}.txt")
            self.cash = float(file.readline().strip())
            lines = file.readlines()
            self.positions = []
            for line in lines:
                stripped = line.strip()
                values = stripped.split(" ")
                if (len(values) < 5):
                    continue
                self.positions.append(
                    position(values[0], float(values[1]), float(values[2]), values[3], values[4]))
        except FileNotFoundError:
            with open(f'{algo}.txt', 'w') as f:
                print("new file created")
        
        

    def in_market(self, tkr1, tkr2):
        for pos in self.positions:
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

    def log_trade(pos):
        with open("PATH TO TRADE HISTORY", "a") as file:
            file.write(pos.str_data)

    def open_position(self, symbol, side, qty, price):
        cost = qty * price
        date = time.strftime("%Y%m%d_%H%M%S")

        if side == 'long':
            if self.cash < cost:
                raise ValueError("Not enough cash to buy")
            self.cash -= cost
        elif side == 'short':
            self.cash += cost  # we receive cash for selling borrowed shares

        pos = None

        existing = self.get_position(symbol, side)
        if existing:
            # Combine positions (simple logic, not averaging for now)
            existing.units += qty
        else:
            pos = position(symbol, qty, price, date, side)
            self.positions.append(pos)

        print(f"Opened {side} {symbol}: {qty} @ {price:.2f}")
        # self.log_trade(pos)

    def close_position(self, symbol, side, qty, price):
        pos = self.get_position(symbol, side)
        # print(pos.units < qty)
        # print(not pos)
        if not pos or pos.units < qty:
            raise ValueError(f"Not enough position to close: {symbol} {side}")

        proceeds = float(qty) * float(price)
        entry_cost = float(qty) * float(pos.costBasis)

        if side == 'long':
            self.cash += proceeds
            pnl = proceeds - entry_cost
        elif side == 'short':
            self.cash -= proceeds  # need to buy back borrowed shares
            pnl = entry_cost - proceeds

        pos.units -= qty
        if pos.units == 0:
            self.positions.remove(pos)

        print(f"Closed {side} {symbol}: {qty} @ {price:.2f}, PnL: ${pnl:.2f}")

    def get_position(self, symbol, side):
        for pos in self.positions:
            if pos.tkr == symbol and pos.side == side:
                return pos
        return None

    def get_balance(self):
        return self.cash

    def get_portfolio_value(self, price_lookup):
        value = self.cash
        for symbol, qty in self.positions.items():
            price = price_lookup(symbol)
            value += qty * price
        return value

    def exit(self):
        with open(f"PATH TO ALGO\\{self.algo}.txt", "w") as file:
            file.write(str(self.cash) + '\n')
            for pos in self.positions:
                file.write(pos.str_data() + '\n')

    def close_all_positions(self):
        # Copy list to avoid mutation during iteration
        for pos in self.positions[:]:
            price = price_lookup(pos.tkr)
            if pos.side == 'long':
                self.cash += float(pos.units) * float(price)

            elif pos.side == 'short':
                self.cash -= float(pos.units) * \
                    float(price)  # Buy to close short

            print(
                f"Closed {pos.side} position: {pos.tkr}, {pos.units} units at {price}")
            self.positions.remove(pos)

