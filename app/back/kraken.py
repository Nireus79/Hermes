from pykrakenapi import KrakenAPI
import krakenex
from datetime import datetime
import requests
import urllib.parse
import hashlib
import hmac
import base64
from ta.momentum import rsi, stoch
from ta.trend import macd_diff
import os
import time

api_url = "https://api.kraken.com"
api_key = os.environ['API_KEY_KRAKEN']
api_sec = os.environ['API_SEC_KRAKEN']


def get_kraken_signature(url, data, secret):
    post_data = urllib.parse.urlencode(data)
    encoded = (str(data['nonce']) + post_data).encode()
    message = url.encode() + hashlib.sha256(encoded).digest()
    mac = hmac.new(base64.b64decode(secret), message, hashlib.sha512)
    sig_digest = base64.b64encode(mac.digest())
    return sig_digest.decode()


def kraken_request(uri_path, data, key, sec):
    headers = {'API-Key': key, 'API-Sign': get_kraken_signature(uri_path, data, sec)}
    req = requests.post((api_url + uri_path), headers=headers, data=data)
    return req


def get_private_balance():
    resp = kraken_request('/0/private/Balance', {
        "nonce": str(int(1000 * time.time()))
    }, api_key, api_sec)
    return resp.json()


def get_condition(crypto_currency):
    """
    Takes the private user's account balance and gives condition to buy or sell to the bot.
    If balance has no crypto returns condition "buy" for the bot to look for good crypto buy conditions.
    If balance has crypto returns condition "sell" for the bot to look for good crypto sell conditions.
    :return: Conditions to buy/sell crypto.
    """
    balance = get_private_balance()
    crypto = balance['result'][crypto_currency]
    if float(crypto) == 0:
        return 'buy'
    elif float(crypto) > 0:
        return 'sell'


def volume(fiat_currency, crypto_currency):
    balance = get_private_balance()
    return {crypto_currency: balance['result'][crypto_currency],
            fiat_currency: balance['result'][fiat_currency + '.HOLD']}


def add_order(ordertype, cond, vol, price, crypto_currency, fiat_currency):
    """
    https://support.kraken.com/hc/en-us/articles/360022839631-Open-Orders
    :param crypto_currency:
    :param fiat_currency:
    :param ordertype: market / limit
    :param cond: buy / sell
    :param vol: vol of fiat or crypto
    :param price: order price
    :return: order response
    """
    pair = crypto_currency + fiat_currency
    resp = kraken_request('/0/private/AddOrder', {
        "nonce": str(int(1000 * time.time())),
        "ordertype": ordertype,
        "type": cond,
        "volume": vol,
        "pair": pair,
        "price": price
    }, key=api_key, sec=api_sec)
    return resp.json()


def cancel_order():
    """
    Cancel all orders
    :return:
    """
    resp = kraken_request('/0/private/CancelAll', {
        "nonce": str(int(1000 * time.time()))
    }, api_key, api_sec)
    """
    or cancel specific order (needs txid)
    resp = kraken_request('/0/private/CancelOrder', {
    "nonce": str(int(1000*time.time())),
    "txid": "OG5V2Y-RYKVL-DT3V3B"
    }, api_key, api_sec)
    """
    return resp.json()


def get_order_info(txid):
    resp = kraken_request('/0/private/QueryOrders', {
        "nonce": str(int(1000 * time.time())),
        "txid": txid,
        "trades": True
    }, api_key, api_sec)
    print(resp.json())
    return resp.json()


def time_stamp(unix):
    """
    Takes unix time and gives datetime format.
    :param unix: unix time.time()
    :return: Readable datetime format.
    """
    ts = int(unix) + 7200  # (7200 2 hours winter) for local time Athens
    return datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')


def high_frame_indicators(hdf):
    """
    Takes a pandas dataframe provided by Kraken rest api containing ohlc data,
    adding columns to each row with the technical indicators of ohlc (stochastic %k, stochastic%d, macd),
    by using the "ta" library.
    Then after comparing the indicators of the last df row, is adding columns with triggers and buy/sell flags.
    : param hdf: raw api dataframe
    :return: df with technical indicators and flags
    """
    hdf['EMA13'] = hdf['close'].rolling(13).mean()
    hdf['EMA30'] = hdf['close'].rolling(30).mean()
    hdf['macd'] = macd_diff(hdf['close'], window_slow=26, window_fast=12, window_sign=9, fillna=False)
    hdf['trend'] = hdf.apply(lambda x: (x['EMA13'] > x['EMA30']) and x['macd'] > 0, axis=1)
    return hdf


def mid_frame_indicators(mdf):
    """
    Takes a pandas dataframe provided by Kraken rest api containing ohlc data,
    adding columns to each row with the technical indicators of ohlc (stochastic %k, stochastic%d, macd),
    by using the "ta" library.
    : param mdf: raw api dataframe
    :return: df with technical indicators and flags
    """
    mdf['%K'] = stoch(mdf['high'], mdf['low'], mdf['close'], window=14, smooth_window=3, fillna=False)
    mdf['%D'] = mdf['%K'].rolling(3).mean()
    mdf['%DS'] = mdf['%D'].rolling(3).mean()  # Stochastic slow.
    mdf['rsi'] = rsi(mdf['close'], window=14, fillna=False)
    mdf['buy flag'] = mdf.apply(lambda x: x['%D'] > x['%DS'] > 20 and (x['rsi'] < 70), axis=1)
    mdf['sell flag'] = mdf.apply(lambda x: x['%D'] < x['%DS'] < 80, axis=1)
    return mdf


class Api:
    """
    crypto: the name of crypto
    fiat: the name of monetary currency
    interval: candle in min
    frame_len: the length of frame (how many candles)
    """

    def __init__(self, crypto, fiat, interval, frame_len):
        self.frame_len = frame_len
        self.crypto = crypto
        self.fiat = fiat
        self.interval = interval  # candle in minutes
        self.pair = self.crypto + self.fiat
        self.candle = interval * 60  # candle in seconds
        self.last_candle = int(time.time()) - self.candle  # 1 candle in seconds
        self.frame = int(time.time()) - self.candle * self.frame_len
        self.key = os.environ['API_KEY_KRAKEN']
        self.sec = os.environ['API_SEC_KRAKEN']

    def get_frame(self):
        api = krakenex.API()
        k = KrakenAPI(api)
        ohlc, last = k.get_ohlc_data(self.pair, interval=self.interval, since=self.frame)
        return ohlc.iloc[::-1]  # reverse rows
