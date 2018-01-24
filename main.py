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


def brain_strategy(pair, quote_c, base_c_balance):
    if quote_c is 'ETH':
        min_quote_sell_price = 0.02
    else:
        exit(quote_c + ' currency is not controlled yet. Chaka chaka')
    current_pair_price = client.get_symbol_ticker(symbol=pair)['price']
    my_pair_value = float(current_pair_price) * base_c_balance
    print(type(my_pair_value))
    number_of_parts = math.floor(my_pair_value / min_quote_sell_price)
    print(number_of_parts)
    price_strategy = 0
    part_strategy = 0
    return price_strategy, part_strategy



    price_strategy = [5, 10, 15, 20, 30]
    part_strategy = [10, 15, 20, 25, 30]


def generate_sells(base_c, pair, mean_price):
    """

    :param asset:
    :param mean_price:
    :return: sells to create
    """
    # Get base_c balance to  dispatch in several sells
    asset_bal = client.get_asset_balance(base_c)


    sells = []
    for i in range(0, len(price_strategie)):
        sells.append([pair,
                      generate_sell_price(mean_price, price_strategie[i]),
                      generate_sell_part(float(asset_bal['free']), part_strategie[i])
                      ])
    return sells


## TODO
# Il faut gerer le nombre de virgule pour la quantite de vente. Mais trouver une autre methode que l'arrondi.
# Gérer un montant minimum car parfois il est trop petit
# Gerer la derniere part pour prendre le reste dans le cas ou l'on "arrondi" la qte de vente.
if __name__ == '__main__':
    exit
    base_c= 'REQ'
    quote_c = 'ETH'
    pair = base_c + quote_c
    mean_price = get_mean_price(pair)
    sells = generate_sells(base_c, pair, mean_price)
    print(sells)
    for i in sells:
        print(i[0],i[2],round(i[1], 8))
        client.create_test_order(symbol=i[0],
                                 side='SELL',
                                 type='LIMIT_MAKER',
                                 quantity=i[2],
                                 price=round(i[1], 8)
                                 )




# TODO :
# annuler tous les ordres
# boucler sur la liste des sells et creer les sells associés
# boucler automatiquement sur toutes les devises
# voir comment éviter les sells trop petits.



