import configparser
from binance.client import Client
import pandas as pd
import math


# url = "https://min-api.cryptocompare.com/data/price?fsym=ETH&tsyms=EUR&e=Coinbase"
# result = requests.get(url)
# print(result.content.decode())


class BClient:

    def __init__(self):
        config = configparser.ConfigParser()
        config.read("./password.dat")
        api_key = config['configuration']['api_key']
        api_secret = config['configuration']['api_secret']
        self.client = Client(api_key, api_secret)

    def get_client(self):
        return self.client


class PublicBinance:
    def __init__(self, client):
        self.client = client

    def get_base_assets(self, quote_c):
        products = self.client.get_exchange_info()
        products = products['symbols']
        products = [product['baseAsset'] for product in products if product['quoteAsset'] == quote_c]
        return products

    def get_buy_opportunities(self, quote_c):
        products = self.get_base_assets(quote_c)
        sorted_products = []
        for product in products:
            pair = Pair(self.client, product, quote_c)
            diff = (pair.last_price - pair.mean_high_price) * 100 / pair.mean_high_price
            sorted_products.append({"base_c": pair.base_c, "mean_high_price": pair.mean_high_price, "last_price": pair.last_price, "diff": diff})
        sorted_products_df = pd.DataFrame(sorted_products)
        return sorted_products_df.sort_values(by="diff")


class Account:
    def __init__(self, client):
        self.client = client
        self.all_balances = self.client.get_account()['balances']
        self.balances = [asset for asset in self.all_balances if (float(asset['free']) + float(asset['locked']) > 0) &
                         (asset['asset'] not in ('ETH', 'GAS', 'ETF'))]


# TODO : mettre les decs_price et decs_part dans un fichier de config. ou les recuperer via client.get_exchange_info()
class Pair:

    def __init__(self, client, base_c, quote_c="ETH", step="1,05", start_date="1 month ago UTC"):
        self.decs_part = {'NEOETH': 2, 'BATETH': 0, 'VENETH': 0, 'SNGLSETH': 0}
        self.decs_price = {'NEOETH': 6}
        self.client = client
        self.base_c = base_c
        self.quote_c = quote_c
        self.pair = base_c + quote_c
        self.step = step
        self.my_base_qty = float(self.client.get_asset_balance(base_c)['free'])
        self.my_mean_price = self.get_mean_price()
        self.mean_high_price = self.get_mean_high_price(start_date)
        self.last_price = float(client.get_ticker(symbol=self.pair)['lastPrice'])
        self.my_balance_value = self.last_price * float(self.my_base_qty)
        self.min_benef = 0.05 if self.my_balance_value <= 1 else 0.1

    def get_mean_price(self):
        """

        :return:
        """
        # Get all trades & apply types
        all_trades = self.client.get_my_trades(symbol=self.pair)
        df = pd.DataFrame(all_trades)
        if df.empty is False:
            df[['commission', 'price', 'qty', 'commission']] = df[['commission', 'price', 'qty', 'commission']].apply(pd.to_numeric)
        else:
            return 0
        # Add a total_price column
        df['total_price'] = df['qty'] * df['price']
        # Get bought (not transfer) remaining qty
        remaining_qty = df.loc[df['isBuyer']]['qty'].sum() - df.loc[df['isBuyer']]['commission'].sum() \
            - df.loc[df['isBuyer'] == False]['qty'].sum()
        # get total price of remaining_qty
        total_prices_w_commissions = df.loc[df['isBuyer']]['total_price'].sum() - \
            df.loc[df['isBuyer'] == False]['total_price'].sum() \
            - df.loc[df['isBuyer'] == False]['commission'].sum()
        # return my_mean_price
        return 0 if (total_prices_w_commissions < 0.1) else (total_prices_w_commissions / remaining_qty)

    def sell_pair(self):
        """

        :return:
        """
        if self.mean_high_price > self.my_mean_price:
            diff_mean_price_vs_mean_high_price = (self.mean_high_price - self.my_mean_price) / self.my_mean_price * 100
            price_strategy, part_strategy = self.brain_strategy(price_strat_1=diff_mean_price_vs_mean_high_price)

            if price_strategy != 0:
                sells, buy_value, benef = self.generate_sells(price_strategy, part_strategy)
                print("Mean price :", self.my_mean_price)
                print("Current price:", self.client.get_ticker(symbol=self.pair)['lastPrice'])
                print("Sells :", sells)
                print("Buy value : ", buy_value)
                print("Benef :", benef)
                for i in sells:
                    self.client.create_test_order(symbol=i[0],
                                                  side='SELL',
                                                  type='LIMIT',
                                                  timeInForce='GTC',
                                                  quantity=i[2],
                                                  price=round(i[1], 8)
                                                  )
            else:
                print("Not enough balance to generate sells for pair ", self.pair, " with such mean high price: ",
                      " \n\r - balance: ", self.my_base_qty,
                      " \n\r - calculated percentage diff: ", round(diff_mean_price_vs_mean_high_price, 2), "%",
                      " \n\r - mean price: ", self.my_mean_price,
                      " \n\r - mean high price: ", self.mean_high_price,
                      " \n\r - min benef: ", self.mean_high_price * self.my_base_qty - self.my_mean_price * self.my_base_qty)
        else:
            print("Mean high price ", self.mean_high_price, " lower than mean price ", self.my_mean_price, " for pair : ", self.pair)

    def get_mean_high_price(self, start_date):
        """

        :rtype: float
        """
        start_date = start_date
        end_date = "now UTC"
        historical_klines = self.client.get_historical_klines(symbol=self.pair,
                                                              interval=self.client.KLINE_INTERVAL_1DAY,
                                                              start_str=start_date,
                                                              end_str=end_date)
        # historical_kline[4] c'est le close price
        # historical_kline[2] c'est le high price
        # OHLCV
        top_prices = [float(historical_kline[4]) for historical_kline in historical_klines]
        return sum(top_prices)/len(top_prices)

    def generate_sells(self, price_strategy, part_strategy):
        """

        :param price_strategy:
        :param part_strategy:
        :return:
        """
        sells = []
        sell_value = 0
        for i in range(0, len(price_strategy)):
            dec_part = 8 if (self.pair not in self.decs_part) else self.decs_part[self.pair]
            dec_part = math.pow(10, dec_part)
            dec_price = 8 if (self.pair not in self.decs_price) else self.decs_price[self.pair]
            dec_price = math.pow(10, dec_price)
            sell_price = math.floor(self.generate_sell_price(self.my_mean_price, price_strategy[i]) * dec_price) / dec_price
            sell_qty = math.floor(self.generate_sell_part(self.my_base_qty, part_strategy[i]) * dec_part) / dec_part
            sells.append([self.pair,
                          sell_price,
                          sell_qty
                          ])
            sell_value = sell_value + (sell_price * sell_qty)
        buy_value = self.my_base_qty * self.my_mean_price
        benef = sell_value - buy_value
        return sells, buy_value, benef

    @staticmethod
    def generate_sell_price(price, rate):
        return (price * rate / 100) + price

    @staticmethod
    def generate_sell_part(qty, rate):
        return qty * rate / 100

    def brain_strategy(self, price_strat_1):
        """

        :param price_strat_1:
        :return: 2 series with the part and price partitions which will be used to create sell orders.
        """
        price_strategy = []
        part_strategy = []
        price_strategy.append(price_strat_1)
        part_strategy.append(self.get_part_strat(price_strat_1))
        if part_strategy[0] > 100:
            return 0, 0
        else:
            j = 0
            while self.get_part_strat(price_strategy[j] * self.step) + sum(part_strategy) < 100:
                price_strategy.append(price_strategy[j] * self.step)
                part_strategy.append(round(self.get_part_strat(price_strategy[j + 1]), 0))
                j = j + 1
            if j == 1:
                part_strategy[0] = 100
            else:
                part_strategy[j] = 100 - sum(part_strategy[:j])
                print("price strategy", "part_strategy", price_strategy, part_strategy)
        return price_strategy, part_strategy

    def get_part_strat(self, price_strat):
        sell_price = self.my_mean_price + (self.my_mean_price * price_strat / 100)
        return round(self.min_benef / (sell_price - self.my_mean_price) * 100 / self.my_base_qty, 0)
