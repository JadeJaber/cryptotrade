import crypto_lib as cl

# minimum value of the asset in ETH in order to be checked & sold
min_balance_value = 0.1
# The smaller the step, the less you may gain money but the tighter your sells are gonna be
step = 1.05
client = cl.BClient().get_client()
myaccount = cl.Account(client)

for asset in myaccount.balances:
    pair = cl.Pair(client=client, base_c=asset['asset'], quote_c='ETH', step=step, start_date="1 month ago UTC")
    symbol = asset['asset']+'ETH'
    try:
        print("\n\rChecking asset", asset['asset'])
        # checking only assets whose value is > min_value
        if pair.my_balance_value >= min_balance_value:
            print('Generating ' + asset['asset'] + " sells")
            pair.sell_pair()
        else:
            print('Balance ', pair.my_balance_value, ' too low for :', pair.pair)
    except Exception as e:
        print("Exception : ", e)
