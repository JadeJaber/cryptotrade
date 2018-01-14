from binance.client import Client
import requests
import configparser

config = configparser.ConfigParser()
config.read("./password.dat")
api_key = config['configuration']['api_key']
api_secret = config['configuration']['api_secret']


client = Client(api_key, api_secret)

time_res = client.get_account_status()
print(time_res)

url = "https://min-api.cryptocompare.com/data/price?fsym=ETH&tsyms=EUR&e=Coinbase"
result = requests.get(url)
print(result.content.decode())

# TODO :
# Coder les formules du fichier Excel et articuler le tout pour avoir le pourcentage de gain en focntion de la devise de base
## comment calcuer le pourcentage de gain : voir le fichier excel pour toutes les
# J'ai installé une BDD mysql et le module python pour s'y conecter : pymysql
# pour démarrer la base mysql, c'est dans les préférences de l'ordi
# pour démarrer lancer le client : "/usr/local/mysql/bin/mysql -uroot -proot"

#(depart * pourentage) = (final - depart)/depart




