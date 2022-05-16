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
from ta.volatility import average_true_range
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


def get_condition(crypto_currency, fiat_currency, closing_price):
    """
    Takes the private user's account balance and gives condition to buy or sell to the bot.
    If balance has less crypto value than fiat returns condition "buy"
    for the bot to look for good crypto buy conditions.
    If balance has more crypto value than fiat returns condition "sell"
    for the bot to look for good crypto sell conditions.
    :return: Conditions to buy/sell crypto.
    """
    fiat_currency = 'Z' + fiat_currency
    balance = get_private_balance()
    crypto_value = float(balance['result'][crypto_currency]) * closing_price
    fiat = float(balance['result'][fiat_currency])
    if crypto_value < fiat:
        return 'buy'
    elif crypto_value >= fiat:
        return 'sell'


def volume(crypto_currency, fiat_currency):
    balance = get_private_balance()
    return {crypto_currency: float(balance['result'][crypto_currency]),
            fiat_currency: float(balance['result']['Z' + fiat_currency])}


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
    # resp = kraken_request('/0/private/CancelOrder', {
    #     "nonce": str(int(1000 * time.time())),
    #     "txid": tx
    # }, api_key, api_sec)
    return resp.json()


def get_order_info(txid):
    resp = kraken_request('/0/private/QueryOrders', {
        "nonce": str(int(1000 * time.time())),
        "txid": txid,
        "trades": True
    }, api_key, api_sec)
    return resp.json()


def time_stamp(unix):
    """
    Takes unix time and gives datetime format.
    :param unix: unix time.time()
    :return: Readable datetime format.
    """
    ts = int(unix) + 10800  # (7200 +2 hours winter, 10800 +3 hours summer) for local time Athens
    return datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')


def high_frame_indicators(hdf):
    """
    Takes a pandas dataframe provided by Kraken rest api containing ohlc data,
    adding columns to each row with the technical indicators of ohlc (stochastic %k, stochastic%d, macd),
    using the "ta" library.
    Then after comparing the indicators of the last df row, is adding columns with triggers and buy/sell flags.
    : param hdf: raw api dataframe
    :return: hdf enriched with technical indicators and flags
    """
    hdf['EMA13'] = hdf['close'].rolling(13).mean()
    hdf['EMA30'] = hdf['close'].rolling(30).mean()
    hdf['macd'] = macd_diff(hdf['close'], window_slow=26, window_fast=12, window_sign=9, fillna=False)
    hdf['trend'] = hdf.apply(lambda x: (x['EMA13'] > x['EMA30']) and x['macd'] > 0, axis=1)
    return hdf


def mid_frame_indicators(mdf, max_rsi, min_vol):
    """
    Takes a pandas dataframe provided by Kraken rest api containing ohlc data,
    adding columns to each row with the technical indicators of ohlc (stochastic %k, stochastic%d, macd),
    using the "ta" library.
    : param mdf: raw api dataframe
    :return: mdf enriched with technical indicators and flags
    """
    mdf['%K'] = stoch(mdf['high'], mdf['low'], mdf['close'], window=14, smooth_window=3, fillna=False)
    mdf['%D'] = mdf['%K'].rolling(3).mean()
    mdf['%DS'] = mdf['%D'].rolling(3).mean()  # Stochastic slow.
    mdf['rsi'] = rsi(mdf['close'], window=14, fillna=False)
    mdf['atr'] = average_true_range(mdf['high'], mdf['low'], mdf['close'], window=14, fillna=False)
    mdf['%atr'] = (mdf['atr'] / mdf['close']) * 100
    mdf['buy flag'] = mdf.apply(
        lambda x: x['%D'] > x['%DS'] > 20 and x['rsi'] < max_rsi and x['%atr'] > min_vol, axis=1)
    mdf['sell flag'] = mdf.apply(lambda x: x['%D'] < x['%DS'] < 80, axis=1)
    return mdf


def low_frame_indicators(ldf):
    """
    Takes a pandas dataframe provided by Kraken rest api containing ohlc data,
    adding column to each row with the technical indicators of atr,
    using the "ta" library.
    :param ldf: low data frame
    :return: ldf enriched with atr
    """
    ldf['atr'] = average_true_range(ldf['high'], ldf['low'], ldf['close'], window=14, fillna=False)
    return ldf


def high_data(frame):
    """
    Takes a pandas dataframe and creates a json with
    the needed values for the ChartJS candle charts.
    Axis X values are all multiplied by 1000.
    JavaScript Date object however uses milliseconds since 1 January 1970 UTC.
    Therefore, you should multiply your timestamps by 1000 prior to assign the data to the chart configuration.
    :param frame: The modified pandas dataframe from high_frame_indicators.
    :return: json and last running indicators to be displayed.
    """
    front_df = frame.copy()
    ema13 = front_df.iloc[-1]['EMA13']
    ema30 = front_df.iloc[-1]['EMA30']
    macd = front_df.iloc[-1]['macd']
    front_df['x'] = front_df['time'].apply(lambda x: x * 1000)
    del front_df['time']
    front_df['o'] = front_df['open']
    del front_df['open']
    front_df['h'] = front_df['high']
    del front_df['high']
    front_df['l'] = front_df['low']
    del front_df['low']
    front_df['c'] = front_df['close']
    del front_df['close']
    del front_df['vwap']
    del front_df['volume']
    del front_df['count']
    del front_df['EMA13']
    del front_df['EMA30']
    del front_df['macd']
    del front_df['trend']
    return front_df.to_json(orient='records'), ema13, ema30, macd


def mid_data(frame):
    """
    Same as above (high_data)
    """
    front_df = frame.copy()
    d = front_df.iloc[-1]['%D']
    ds = front_df.iloc[-1]['%DS']
    rs = front_df.iloc[-1]['rsi']
    percent_atr = front_df.iloc[-1]['%atr']
    front_df['x'] = front_df['time'].apply(lambda x: x * 1000)
    del front_df['time']
    front_df['o'] = front_df['open']
    del front_df['open']
    front_df['h'] = front_df['high']
    del front_df['high']
    front_df['l'] = front_df['low']
    del front_df['low']
    front_df['c'] = front_df['close']
    del front_df['close']
    del front_df['vwap']
    del front_df['volume']
    del front_df['count']
    del front_df['%K']
    del front_df['%D']
    del front_df['%DS']
    del front_df['rsi']
    del front_df['%atr']
    del front_df['buy flag']
    del front_df['sell flag']
    return front_df.to_json(orient='records'), d, ds, rs, percent_atr


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
