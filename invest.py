import time
from datetime import date, datetime, timedelta
import base64
import requests
import urllib.parse
import hashlib
import hmac
import sys
import os
import csv
from dotenv import load_dotenv

load_dotenv()

api_key = os.environ.get("API_KEY")
api_secret = os.environ.get("API_SECRET")
token_pair = os.environ.get("TOKEN_PAIR")
currency = os.environ.get("CURRENCY")
live_purchase_mode = os.environ.get("LIVE_PURCHASE_MODE")=="true" or False

api_endpoint = "https://api.kraken.com"

# Minimum quantity of BTC one can buy from Kraken - see https://support.kraken.com/hc/en-us/articles/205893708-Minimum-order-size-volume-for-trading
minimum_vol =  float(os.environ.get("MINIMUM_BUY_VOLUME"))
satoshis_in_a_btc = 100000000

def append_to_transaction_csv(rows, row):
  with open('satstacker-transactions.csv', 'w', newline='') as csvfile:
    csvwriter = csv.writer(csvfile, delimiter=',')
    for oldrow in rows:
      csvwriter.writerow(oldrow)  
    csvwriter.writerow(row)

def load_previous_transactions():
  txns = []
  try:
    with open('satstacker-transactions.csv', newline='') as csvfile:
      txnreader = csv.reader(csvfile, delimiter=',')
      for row in txnreader:
        txns += [row]

  except FileNotFoundError:
    print("No previous transactions found. Initialising transaction CSV file...")
    hdr = ['Timestamp', 'Token Pair', 'Volume', 'Price', 'Total Spent', 'Balance Remaining', 'Next Purchase Date']
    append_to_transaction_csv([], hdr)
    txns += [hdr]
  return txns  

previous_transactions = load_previous_transactions()
next_txn_date = date.today()
if len(previous_transactions) > 2: #incl header
  last_txn = previous_transactions[-1]
  next_txn_date = datetime.fromisoformat(last_txn[-1])

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

def fetch_latest_price(token_pair):
  response = post_url( public_url_path('Ticker'), {"pair": token_pair} )
  price_info = response.json()
  if len(price_info['error'])>0:
    raise RuntimeError(price_info['error'][0])
  else:
    return float(price_info['result'][token_pair]['b'][0])

def current_balance(currency):
  response = post_url( private_url_path('Balance') )
  balance_info = response.json()
  try:
    return float(balance_info["result"][currency])
  except KeyError:
    return 0

def leap_year(a_date):
  return a_date.year % 100 == 0 and a_date.year % 4 == 0

def no_days_till_end_of_month(a_date):
  month = a_date.month
  if month == 4 or month == 6 or month == 9 or month == 11:
    return 30 - a_date.day 
  elif month == 2:
    if leap_year(a_date):
      return 29 - a_date.day 
    else:
      return 28 - a_date.day
  else:
    return 31 - a_date.day 

def record_txn(token_pair, purchase_vol, price, balance_remaining, next_purchase_date):
  sats = purchase_vol * satoshis_in_a_btc
  spending = price * purchase_vol
  print("Stacking {0:.2f} satoshis via {1} at {2:.2f} spending {3:.2f}".format(sats, token_pair, price, spending))
  now = datetime.today().isoformat()
  append_to_transaction_csv(previous_transactions, [now, token_pair, purchase_vol, price, spending, balance_remaining, next_purchase_date])

def buy(token_pair, purchase_vol, price, balance_remaining, next_purchase_date):
  time.sleep(1) # prevents any collision with the time-based nonce
  if live_purchase_mode:
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
      record_txn(token_pair, purchase_vol, price, balance_remaining, next_purchase_date)
      return txn
  else:
    print("TRIALMODE")
    record_txn(token_pair, purchase_vol, price, balance_remaining, next_purchase_date)

def invest(token_pair):
  # today = date.today()
  today = datetime(2021, 3, 1)

  latest_price = fetch_latest_price(token_pair)  
  balance = current_balance(currency)

  print("------------------------------------------------------------------------------")
  print("Today's date: {0}. Your balance: {1:.2f} {2}".format(today.strftime("%x"), balance, currency))
  if today.year <= next_txn_date.year and today.month <= next_txn_date.month and today.day < next_txn_date.day:
    print("Next transaction date {0}, sleeping until then.".format(next_txn_date.strftime("%x")))
    return

  no_days_left = no_days_till_end_of_month(today)
  if no_days_left==0:
    daily_budget = balance
  else:
    daily_budget = balance / no_days_left
  vol = daily_budget / latest_price

  if (vol < minimum_vol):
    print("Unable to buy daily.")
    minimum_purchase_cost = minimum_vol * latest_price
    if minimum_purchase_cost > balance:
      print("The minimum purchase cost > your balance. Add more fiat to your account.")
    else:
      vol = minimum_vol
      fiat_to_spend = vol * latest_price
      balance_remaining = (balance - fiat_to_spend)
      print("At today's price {0:.2f}, purchasing {1:.3f} {2} will cost {3:.2f}. Balance remaining {4:.2f}".format(latest_price, vol, token_pair, fiat_to_spend, balance_remaining))
      no_purchases_possible =  balance_remaining // fiat_to_spend
      if no_purchases_possible > 0:
        purchase_interval = round(no_days_left / no_purchases_possible)
        print("The {0:.0f} remaining purchases, every {1} days, assuming no price change, are as follows: ".format(no_purchases_possible, purchase_interval))
        next_purchase_date = today + timedelta(days=purchase_interval)
        buy(token_pair, vol, latest_price, balance_remaining, next_purchase_date)
        for n in range(int(no_purchases_possible)):
          balance_remaining = balance_remaining - fiat_to_spend
          skip_days = (n+1)*purchase_interval
          new_date = today + timedelta(days=skip_days)
          print("{2}. {0} Balance remaining: {1:.2f}".format(new_date.strftime("%x"), balance_remaining, n+1))

  else:
    print("You can buy daily.")
    fiat_to_spend = vol * latest_price
    balance_remaining = (balance - fiat_to_spend)
    buy(token_pair, vol, latest_price, balance_remaining, today + timedelta(days=1))

# END: TRADING SECTION 

try:
  invest(token_pair)
except RuntimeError as err:
  print(err, file=sys.stderr)