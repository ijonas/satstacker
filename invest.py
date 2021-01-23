import time
import base64
import requests
import urllib.parse
import hashlib
import hmac
import sys
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.environ.get("API_KEY")
api_secret = os.environ.get("API_SECRET")
token_pair = os.environ.get("TOKEN_PAIR")
fiat_to_spend = float(os.environ.get("FIAT_TO_SPEND"))

api_endpoint = "https://api.kraken.com"

# Minimum quantity of BTC one can buy from Kraken - see https://support.kraken.com/hc/en-us/articles/205893708-Minimum-order-size-volume-for-trading
minimum_vol = 0.001 
satoshis_in_a_btc = 100000000

# START: API SECTION 
# Deals with mechanics of talking to Kraken API incl. signing of requests
def nonce():
  return str(time.time_ns())[:16]

def encode_options(opts):
  return urllib.parse.urlencode(opts)

def private_url_path(method):
  return '/0/private/' + method

def public_url_path(method):
  return '/0/public/' + method

def generate_message(url_path, opts, data):
  m = hashlib.sha256()
  payload = (opts['nonce']+data).encode('utf-8')
  m.update(payload)
  digest = m.digest()
  return url_path.encode('utf-8') + digest

def generate_hmac(key, message):
  digest = hmac.new(key, msg=message, digestmod=hashlib.sha512).digest()
  return base64.b64encode(digest)

def generate_signature(url_path, post_data, opts={}):
  key = base64.b64decode(api_secret)
  message = generate_message(url_path, opts, post_data)
  return generate_hmac(key, message)

def post_url(url_path, opts={}):
  opts['nonce'] = nonce()
  post_data = encode_options(opts)
  signature = generate_signature(url_path, post_data, opts)
  headers = {
    "API-Key": api_key,
    "API-Sign": signature
  }
  return requests.post(api_endpoint+url_path, data = opts, headers = headers)

# END: API SECTION 

# START: TRADING SECTION 
# Fetches the latest price information and figures out how much to buy

def fetch_lastest_price(token_pair):
  response = post_url( public_url_path('Ticker'), {"pair": token_pair} )
  price_info = response.json()
  if len(price_info['error'])>0:
    raise RuntimeError(price_info['error'][0])
  else:
    return float(price_info['result'][token_pair]['b'][0])

def buy(token_pair, fiat_to_spend):
  price = fetch_lastest_price(token_pair)
  purchase_vol = fiat_to_spend / price
  if purchase_vol < minimum_vol:
    raise RuntimeError("Purchase volume less than minimum allowed.")
  sats = purchase_vol * satoshis_in_a_btc
  time.sleep(1) # prevents any collision with the time-based nonce
  response = post_url( private_url_path("AddOrder"), {
    "pair": token_pair,
    "type": "buy",
    "ordertype": "limit",
    "price": price,
    "volume": purchase_vol
  })
  txn = response.json()
  if len(txn['error'])>0:
    raise RuntimeError(txn['error'][0])
  else:
    print("Stacking {0:.2f} satoshis via {1} at {2:.2f} spending {3:.2f}".format(sats, token_pair, price, fiat_to_spend))
    return txn

# END: TRADING SECTION 

# Common BTC tokens on Kraken
# Common Name - Kraken Name
# BTCDAI - XBTDAI
# BTCGBP - XXBTZGBP
# BTCUSD - XXBTZUSD
# BTCEUR - XXBTZEUR
try:
  buy(token_pair, fiat_to_spend)
except RuntimeError as err:
  print(err, file=sys.stderr)

