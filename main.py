from binance.client import Client
import requests
import configparser
import pandas as pd
import numpy as np
import math


config = configparser.ConfigParser()
config.read("./password.dat")
api_key = config['configuration']['api_key']
api_secret = config['configuration']['api_secret']
client = Client(api_key, api_secret)


# url = "https://min-api.cryptocompare.com/data/price?fsym=ETH&tsyms=EUR&e=Coinbase"
# result = requests.get(url)
# print(result.content.decode())

decs_part = {'NEOETH': 2, 'BATETH': 0, 'VENETH': 0}
decs_price = {'NEOETH': 6}


def get_mean_price(pair):
    """
    :param pair
    :return: mean price of the pair
    """
    # Get all trades & apply types
    all_trades = client.get_my_trades(symbol=pair)
    df = pd.DataFrame(all_trades)
    df[['commission', 'price', 'qty', 'commission']] = df[['commission', 'price', 'qty', 'commission']].apply(pd.to_numeric)
    # Add a total_price column
    df['total_price'] = df['qty'] * df['price']
    # Get bought (not transfer) remaining qty
    remaining_qty = df.loc[df['isBuyer']]['qty'].sum() - df.loc[df['isBuyer']]['commission'].sum() \
        - df.loc[df['isBuyer'] == False]['qty'].sum()
    # get total price of remaining_qty
    total_prices_w_commissions = df.loc[df['isBuyer']]['total_price'].sum() - \
        df.loc[df['isBuyer'] == False]['total_price'].sum() \
        - df.loc[df['isBuyer'] == False]['commission'].sum()
    # return mean_price
    return 0 if (total_prices_w_commissions < 0.1) else (total_prices_w_commissions / remaining_qty)


def generate_sell_price(price, rate):
    return (price * rate / 100) + price


def generate_sell_part(qty, rate):
    return qty * rate / 100


def brain_strategy(price_strat_1, base_qty, benef, mean_price, step):
    """

    :param price_strat_1:
    :param base_qty:
    :param benef:
    :param mean_price:
    :param step:
    :return: 2 series with the part and price partitions which will be used to create sell orders.
    """
    price_strategy = []
    part_strategy = []
    price_strategy.append(price_strat_1)
    part_strategy.append(get_part_strat(base_qty, benef, mean_price, price_strat_1))
    if part_strategy[0] > 100:
        return 0, 0
    else:
        j = 0
        while get_part_strat(base_qty, benef, mean_price, price_strategy[j] * step) + sum(part_strategy) < 100:
            price_strategy.append(price_strategy[j] * step)
            part_strategy.append(round(get_part_strat(base_qty, benef, mean_price, price_strategy[j+1]), 0))
            j = j+1
        if j == 1:
            part_strategy[0] = 100
        else:
            part_strategy[j] = 100 - sum(part_strategy[:j])
            print("price strategy", "part_strategy", price_strategy, part_strategy)
    return price_strategy, part_strategy


def generate_sells(base_qty, pair, mean_price, price_strategy, part_strategy):
    """

    :param base_qty:
    :param pair:
    :param mean_price:
    :param price_strategy:
    :param part_strategy:
    :return:
    """
    sells = []
    for i in range(0, len(price_strategy)):
        dec_part = 8 if (pair not in decs_part) else decs_part[pair]
        dec_part = math.pow(10, dec_part)
        dec_price = 8 if (pair not in decs_price) else decs_price[pair]
        dec_price = math.pow(10, dec_price)
        sells.append([pair,
                      math.floor(generate_sell_price(mean_price, price_strategy[i]) * dec_price) / dec_price,
                      math.floor(generate_sell_part(base_qty, part_strategy[i]) * dec_part) / dec_part
                      ])
    return sells


def get_mean_high_price(pair):
    start_date = "1 month ago UTC"
    end_date = "now UTC"
    historical_klines = client.get_historical_klines(symbol=pair,
                                                     interval=client.KLINE_INTERVAL_1DAY,
                                                     start_str=start_date,
                                                     end_str=end_date)
    # historical_kline[4] c'est le close price
    # historical_kline[2] c'est le high price
    # OHLCV
    top_prices = [float(historical_kline[2]) for historical_kline in historical_klines]
    return sum(top_prices)/len(top_prices)


def get_part_strat(base_qty, benef, mean_price, price_strat):
    sell_price = mean_price + (mean_price * price_strat / 100)
    return round(benef / (sell_price - mean_price) * 100 / base_qty, 0)


def sell_pair(base_c, quote_c, benef, step):
    pair = base_c + quote_c
    base_qty = float(client.get_asset_balance(base_c)['free'])
    mean_price = get_mean_price(pair)
    mean_high_price = get_mean_high_price(pair)
    if mean_high_price > mean_price:
        diff_mean_price_vs_mean_high_price = (mean_high_price - mean_price)/mean_price * 100
        price_strategy, part_strategy = brain_strategy(price_strat_1=diff_mean_price_vs_mean_high_price,
                                                       base_qty=base_qty,
                                                       benef=benef,
                                                       mean_price=mean_price,
                                                       step=step)
        if price_strategy != 0:
            sells = generate_sells(base_qty, pair, mean_price, price_strategy, part_strategy)
            print("Mean price :", mean_price)
            print("Current price:", client.get_ticker(symbol=pair)['lastPrice'])
            print("Sells :", sells)
            for i in sells:
                client.create_test_order(symbol=i[0],
                                    side='SELL',
                                    type='LIMIT',
                                    timeInForce='GTC',
                                    quantity=i[2],
                                    price=round(i[1], 8)
                                    )
        else:
            print("Not enough balance to generate interesting sells for pair ", pair, " with such mean high price: ",
                  " \n\r - balance: ", base_qty,
                  " \n\r - calculated percentage diff: ", round(diff_mean_price_vs_mean_high_price, 2), "%",
                  " \n\r - mean price: ", mean_price,
                  " \n\r - mean high price: ", mean_high_price,
                  " \n\r - min benef: ", mean_high_price * base_qty - mean_price * base_qty)
    else:
        print("Mean high price ", mean_high_price, " is lower than mean price ", mean_price, " for pair : ", pair)


if __name__ == '__main__':
    # minimum value of the asset in ETH in order to be checked & sold
    min_balance_value = 0.1
    # The smaller the step, the less you may gain money but the tighter your sells are gonna be
    step = 1.05
    # get non zero assets and remove NA assets
    my_account = client.get_account()['balances']
    my_account = [asset for asset in my_account if
                  (float(asset['free']) + float(asset['locked']) > 0) &
                  (asset['asset'] not in ('ETH', 'GAS', 'ETF'))
                  ]
    for asset in my_account:
        symbol = asset['asset']+'ETH'
        try:

            balance_value = float(client.get_ticker(symbol=symbol)['lastPrice']) * float(asset['free'])
            # we may consider more tresholds to define minbenef when I will assets with higher balance_values
            benef = 0.1 if balance_value <= 1 else 0.2
            print("\n\rChecking asset", asset['asset'])
            # checking only assets whose value is > min_value
            if balance_value >= min_balance_value:
                print('Generating ' + asset['asset'] + " sells")
                sell_pair(asset['asset'], 'ETH', benef, step)
            else:
                print('Balance ', balance_value,  ' too low for :', asset['asset'])
        except Exception as e:
            print("Exception : ", e)


