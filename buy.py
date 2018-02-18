import crypto_lib as cl


client = cl.BClient().get_client()
myaccount = cl.PublicBinance(client)
print(myaccount.get_buy_opportunities('ETH'))



#todo : récuopérer la liste de toutes les pairs eth de binance
#todo : calculer pour chacun le mean_high_price
#todo : comparer pour chacun le mean higne price avec le last peice
#todo : trier les pairs dans l'ordre décroissant en terme de pourcentage de difference entre ces 2 valeurs.

