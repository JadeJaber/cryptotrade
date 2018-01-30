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
            part_strategy.append(get_part_strat(base_qty, benef, mean_price, price_strategy[j+1]))
            j = j+1
        if j == 1:
            part_strategy[0] = 100
        else:
            part_strategy[j] = 100 - sum(part_strategy[:j])
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
        sells.append([pair,
                      generate_sell_price(mean_price, price_strategy[i]),
                      generate_sell_part(base_qty, part_strategy[i])
                      ])
    return sells


def get_mean_high_price(pair):
    start_date = "1 month ago UTC"
    end_date = "now UTC"
    historical_klines = client.get_historical_klines(symbol=pair,
                                                     interval=client.KLINE_INTERVAL_1DAY,
                                                     start_str=start_date,
                                                     end_str=end_date)
    top_prices = [float(historical_kline[2]) for historical_kline in historical_klines]
    return sum(top_prices)/len(top_prices)


def get_part_strat(base_qty, benef, mean_price, price_strat):
    sell_price = mean_price + (mean_price * price_strat / 100)
    return benef / (sell_price - mean_price) * 100 / base_qty


def sell_pair(base_c, quote_c, benef, step):
    pair = base_c + quote_c
    base_qty = float(client.get_asset_balance(base_c)['free'])
    mean_price = get_mean_price(pair)
    mean_high_price = get_mean_high_price(pair)
    if mean_high_price > mean_price:
        diff_mean_price_vs_mean_high_price = round((mean_high_price - mean_price)/mean_price * 100, 0)
        price_strategy, part_strategy = brain_strategy(price_strat_1=diff_mean_price_vs_mean_high_price,
                                                       base_qty=base_qty,
                                                       benef=benef,
                                                       mean_price=mean_price,
                                                       step=step)
        if price_strategy != 0:
            sells = generate_sells(base_qty, pair, mean_price, price_strategy, part_strategy)
            print(sells)
            for i in sells:
                client.create_test_order(symbol=i[0],
                                         side='SELL',
                                         type='LIMIT_MAKER',
                                         quantity=round(i[2], 2),
                                         price=round(i[1], 4)
                                         )
        else:
            print("No interesting sells to create for pair : ", pair)
    else:
        print("Mean high price is lower than mean price for pair : ", pair)


if __name__ == '__main__':
    benef = 0.1
    step = 1.2
    my_account = client.get_account()['balances']
    for asset in my_account:
        symbol = asset['asset']+'ETH'
        try:
            if float(client.get_ticker(symbol=symbol)['lastPrice']) * float(asset['free']) >= benef:
                sell_pair(asset['asset'], 'ETH', benef, step)
        except Exception as e:
            print(e)


# TODO : annuler tous les ordres d'une paire dès lors qu'il y a eu un achat ou une vente depuis l'open order le plus ancien.
# TODO : voir pour l'arrondi au lors de la creation de l'ordre. L'API n'aime pas avoir trop de décimales => Le problème c'est que ca depend de l'asset aussi




