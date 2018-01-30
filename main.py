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
    print("remaining_qty: ", remaining_qty)
    # get total price of remaining_qty
    total_prices_w_commissions = df.loc[df['isBuyer']]['total_price'].sum() - \
        df.loc[df['isBuyer'] == False]['total_price'].sum() \
        - df.loc[df['isBuyer'] == False]['commission'].sum()
    print("total_prices_w_commissions : ", total_prices_w_commissions)
    # return mean_price
    return 0 if (total_prices_w_commissions < 0.1) else (total_prices_w_commissions / remaining_qty)


    #df.loc[df['isBuyer'] == False, "qty"] = -df['qty']

    #     remaining_qty_official = client.get_asset_balance(currency)
    #print("remaining_qty_official : ", remaining_qty_official)

    #NUMPY

    # df['elderly'] = np.where(df['age']>=50, 'yes', 'no')

    # total_prices_w_commissions =
    #Formule pour calculer le solde d'un asset à partir de la liste des trades
    #somme(qty    acheté)-somme(fee    achat)-somme(qty    vendu)

    #df = df['qty']*df['price']-df['commission']
    # Pour calculer le prix moyen on fait la somme des produits des prix et des qté en mettant les ventes au négatif,
    # puis récupérer le solde actuel de la devise concernée et déviser le résultat de la somme précedente par le nombre de devise restantes.
    # = somme(price x (-)? qty) / (solde de la devise)


    # print(df)
    # df = df.loc[df['status'] == 'FILLED']
    # print(df[['status', 'price']])
    # df = df.groupby(['status']).mean()
    # print(df)
    # df[['price']] = df[['price']].apply(pd.to_numeric)
    # df = df['price'].mean()


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
            print(j)
            print(part_strategy)
            part_strategy[j-1] = 100 - sum(part_strategy[:j-1])
    return price_strategy[:j], part_strategy[:j]


def generate_sells(base_qty, pair, mean_price, price_strategy, part_strategy):
    """

    :param asset:
    :param mean_price:
    :return: sells to create
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

# todo : voir pour l'arrondi au lors de la creation de l'ordre. L'PI n'aime pas avoir trop de décimales
# Le problème c'est que ca depend de l'asset aussi
# voir pourquoi je n'ai aucune vente lorsque je le benef à 0.2

if __name__ == '__main__':
    base_c = 'NEO'
    quote_c = 'ETH'
    pair = base_c + quote_c
    base_qty = float(client.get_asset_balance(base_c)['free'])
    mean_price = get_mean_price(pair)
    mean_high_price = get_mean_high_price(pair)
    diff_mean_price_vs_mean_high_price = round((mean_high_price - mean_price)/mean_price * 100, 0)
    price_strategy, part_strategy = brain_strategy(price_strat_1=diff_mean_price_vs_mean_high_price,
                                                   base_qty=base_qty,
                                                   benef=0.2,
                                                   mean_price=mean_price,
                                                   step=1.5)
    print(base_qty, mean_price, mean_high_price, diff_mean_price_vs_mean_high_price)
    print(price_strategy, part_strategy)
    if price_strategy != 0:
        sells = generate_sells(base_qty, pair, mean_price, price_strategy, part_strategy)
        print(sells)
        for i in sells:
            print(i[0], i[2], i[1])
            client.create_test_order(symbol=i[0],
                                     side='SELL',
                                     type='LIMIT_MAKER',
                                     quantity=round(i[2], 2),
                                     price=round(i[1], 4)
                                     )
    else:
        print("No interesting sells to create")



# TODO :
# annuler tous les ordres
# boucler automatiquement sur toutes les devises



