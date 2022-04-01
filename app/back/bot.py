import logging
import time
import threading
import winsound
from app.back.kraken import Api, high_frame_indicators, mid_frame_indicators, time_stamp, \
    volume, add_order, get_order_info, cancel_order, get_condition

logging.basicConfig(level=logging.INFO)

condition = None
stop = 0
limit = None
new_closing = None
pillow = 0
log = None
trend_24h = None
trend_4h = None
trend_1h = None
buy_flag_4h = None
sell_flag_4h = None
buy_flag_1h = None
sell_flag_1h = None
buy_flag_15m = None
sell_flag_15m = None
crypto_balance = None
fiat_balance = None

high_frame_24h = None
high_frame_4h = None
high_frame_1h = None
mid_frame_4h = None
mid_frame_1h = None
mid_frame_15m = None

feed = None

exit_event = threading.Event()

# add_order('market', 'sell', 0, 0, 'DOT', 'EUR')


def signal_handler():
    exit_event.set()


def beeper(cond):
    if cond == 'buy':
        for _ in range(5):
            winsound.Beep(440, 500)
            time.sleep(0.5)
    elif cond == 'sell':
        for _ in range(5):
            winsound.Beep(1000, 500)
            time.sleep(0.1)
    elif cond == 'start':
        winsound.Beep(440, 2000)


def limit_manager(mid, low, cond):
    """
    Same as order_manager.
    No actual order is set.
    User is just informed for the action he has to take.
    :param mid: The middle time frame instance, used to check if buy/sell flag is still True.
    :param low: The low time frame instance, used to set limit/stop-loss borders.
    :param cond: Condition sell/buy
    """
    global pillow
    global condition
    global stop
    global limit
    global log
    global new_closing
    beeper('start')
    log = '{} Start setting {}min low frame {} limits.'.format(time_stamp(time.time()), low.interval, cond)
    logging.info(log)
    new = low.get_frame().iloc[-1]
    middle = mid_frame_indicators(mid.get_frame()).iloc[-1]
    limit = new['high']
    stop = new['low']
    pillow = middle['low']
    log = '{} limit: {}. Stop loss: {}. Pillow: {}'.format(time_stamp(time.time()), limit, stop, pillow)
    logging.info(log)
    if cond == 'buy':
        log = '{} Please give buy order when price exceeds {}. Wait {}min.' \
            .format(time_stamp(time.time()), limit, low.interval / 10)
        logging.info(log)
        time.sleep(low.candle / 10)
    elif cond == 'sell':
        log = '{} Please give sell order when price under {}. Wait {}min.' \
            .format(time_stamp(time.time()), stop, low.interval / 10)
        logging.info(log)
        time.sleep(low.candle / 10)
    while True:
        middle = mid_frame_indicators(mid.get_frame()).iloc[-1]
        new = low.get_frame().iloc[-1]
        buy_flag = middle['buy flag']
        sell_flag = middle['sell flag']
        new_pillow = middle['low']
        new_closing = new['close']
        new_limit = new['high']
        new_stop = new['low']
        if exit_event.is_set():  # thread "kill" by user
            log = '{} Operation interrupted by user.'.format(time_stamp(time.time()))
            logging.info(log)
            break
        if cond == 'buy':
            if buy_flag:
                if new_closing > limit:
                    log = '{} Closing price exceeded limit. Please add buy order'.format(time_stamp(time.time()))
                    logging.info(log)
                    pillow = new_pillow
                    beeper(cond)
                    time.sleep(10)
                    break
                elif new_closing < limit:
                    if new_limit < limit:
                        limit = new_limit
                        stop = new_stop
                        pillow = new_pillow
                        log = '{} New limit set to {}. Please wait {}min.' \
                            .format(time_stamp(time.time()), limit, low.interval / 10)
                        logging.info(log)
                        time.sleep(low.candle / 10)
                    else:
                        log = '{} Closing price not exceeded limit. Please wait {}min.'.format(
                            time_stamp(time.time()), low.interval / 10)
                        logging.info(log)
                        time.sleep(low.candle / 10)
            elif sell_flag:
                log = '{} Mid frame momentum reversed to weak. Conditions re-evaluation.' \
                    .format(time_stamp(time.time()))
                logging.info(log)
                time.sleep(1)
                break
        elif cond == 'sell':
            if sell_flag:
                if new_closing < stop:
                    log = '{} Closing price under stop loss level. Please add sell order' \
                        .format(time_stamp(time.time()))
                    logging.info(log)
                    beeper(cond)
                    time.sleep(10)
                    break
                elif new_closing > stop:
                    if new_stop > stop:
                        limit = new_limit
                        stop = new_stop
                        pillow = new_pillow
                        log = '{} New stop-loss set to {}. Please wait {}min.' \
                            .format(time_stamp(time.time()), stop, low.interval / 10)
                        logging.info(log)
                        time.sleep(low.candle / 10)
                    else:
                        log = '{} Closing price over stop-loss level. Please wait {}min.'.format(
                            time_stamp(time.time()), low.interval / 10)
                        logging.info(log)
                        time.sleep(low.candle / 10)
            elif buy_flag:
                log = '{} Mid frame momentum reversed to strong. Conditions re-evaluation.' \
                    .format(time_stamp(time.time()))
                logging.info(log)
                time.sleep(1)
                break


def order_manager(order_type, mid, low, cond, crypto_currency, fiat_currency):
    """
    When conditions to buy or sell are aligned in higher frames (buy or sell flag True)
    order_manager is setting limit and stop loss levels.
    Then monitoring closing price.
    When looking to sell asset,
        if closing price lower stop-loss level:
            places market sell order for the asset.
    When looking to buy asset,
        if closing price exceeds limit level:
            places a market buy asset for the asset
            and sets mid-frame last candle low as pillow
    :param order_type: limit / market
    :param crypto_currency: asset a
    :param fiat_currency: asset b
    :param mid: mid-frame instance
    :param low: low-frame instance
    :param cond: buy / sell
    """
    global pillow
    global condition
    global stop
    global limit
    global log
    global fiat_balance
    global crypto_balance
    global new_closing
    beeper('start')
    log = '{} Start setting {}min low frame {} limits.'.format(time_stamp(time.time()), low.interval, cond)
    logging.info(log)
    new = low.get_frame().iloc[-1]
    vol = volume(fiat_currency, crypto_currency)
    limit = new['high']
    stop = new['low']
    new_closing = new['close']
    crypto_balance = vol[crypto_currency]
    fiat_balance = vol[fiat_currency]
    log = 'Balance: {} crypto, {} money'.format(crypto_balance, fiat_balance)
    logging.info(log)
    log = '{} Current price {}. limit {}. Stop loss-Pillow {}.' \
        .format(time_stamp(time.time()), new_closing, limit, stop)
    logging.info(log)
    log = 'Wait {}min.'.format(low.interval / 10)
    logging.info(log)
    time.sleep(low.candle / 10)
    while True:
        middle = mid_frame_indicators(mid.get_frame()).iloc[-1]
        new = low.get_frame().iloc[-1]
        buy_flag = middle['buy flag']
        sell_flag = middle['sell flag']
        new_pillow = middle['low']
        new_closing = new['close']
        if exit_event.is_set():  # thread "kill" by user
            cancel_order()
            log = '{} Break ordering.'.format(time_stamp(time.time()))
            logging.info(log)
            break
        elif cond == 'buy':
            if buy_flag:
                if new_closing > limit:
                    tx = add_order(order_type, cond, fiat_balance, new_closing, crypto_currency, fiat_currency)['txid']
                    status = get_order_info(tx)
                    pillow = new_pillow
                    beeper(cond)
                    time.sleep(10)
                    while True:
                        if buy_flag:
                            if status == 'close':
                                log = '{} Order closed.'.format(time_stamp(time.time()))
                                logging.info(log)
                                break
                            elif status == 'open':
                                middle = mid_frame_indicators(mid.get_frame()).iloc[-1]
                                new = low.get_frame().iloc[-1]
                                new_pillow = middle['low']
                                new_closing = new['close']
                                new_limit = new['high']
                                new_stop = new['low']
                                if new_limit < limit:
                                    cancel_order()
                                    limit = new_limit
                                    stop = new_stop
                                    pillow = new_pillow
                                    tx = add_order(order_type, cond,
                                                   fiat_balance, new_closing, crypto_currency, fiat_currency)['txid']
                                    status = get_order_info(tx)
                                    log = '{} New {} order added at {}.' \
                                        .format(time_stamp(time.time()), cond, new['close'])
                                    logging.info(log)
                                    time.sleep(10)
                                else:
                                    log = '{} Order is open.'.format(time_stamp(time.time()))
                                    logging.info(log)
                                    time.sleep(10)
                        elif sell_flag:
                            cancel_order()
                            log = '{} Mid frame momentum reversed to weak. Conditions re-evaluation.' \
                                .format(time_stamp(time.time()))
                            logging.warning(log)
                            time.sleep(1)
                            break
                else:
                    log = '{} Closing price under limit. Wait {}min.' \
                        .format(time_stamp(time.time()), low.interval / 10)
                    logging.warning(log)
                    time.sleep(low.candle / 10)
            elif sell_flag:
                cancel_order()
                log = '{} Mid frame momentum reversed to weak. Conditions re-evaluation.' \
                    .format(time_stamp(time.time()))
                logging.warning(log)
                time.sleep(1)
                break
        elif cond == 'sell':
            if sell_flag:
                if new_closing < stop:
                    tx = add_order(order_type, cond, fiat_balance, new_closing, crypto_currency, fiat_currency)['txid']
                    status = get_order_info(tx)
                    beeper(cond)
                    while True:
                        if sell_flag:
                            if status == 'close':
                                log = '{} Order closed.'.format(time_stamp(time.time()))
                                logging.warning(log)
                                time.sleep(10)
                                break
                            elif status == 'open':
                                new = low.get_frame().iloc[-1]
                                new_closing = new['close']
                                new_limit = new['high']
                                new_stop = new['low']
                                if new_stop > stop:
                                    cancel_order()
                                    limit = new_limit
                                    stop = new_stop
                                    tx = add_order(order_type, cond,
                                                   fiat_balance, new_closing, crypto_currency, fiat_currency)['txid']
                                    status = get_order_info(tx)
                                    log = '{} New {} order added at {}.' \
                                        .format(time_stamp(time.time()), cond, new['close'])
                                    logging.warning(log)
                                    time.sleep(10)
                                else:
                                    log = '{} Order is open.'.format(time_stamp(time.time()))
                                    logging.warning(log)
                                    time.sleep(10)
                        elif buy_flag:
                            cancel_order()
                            log = '{} Mid frame momentum reversed to strong. Conditions re-evaluation.' \
                                .format(time_stamp(time.time()))
                            logging.warning(log)
                            time.sleep(1)
                            break
                else:
                    log = '{} Closing price over stop. Wait {}min.' \
                        .format(time_stamp(time.time()), low.interval / 10)
                    logging.warning(log)
                    time.sleep(low.candle / 10)
            elif buy_flag:
                cancel_order()
                log = '{} Mid frame momentum reversed to strong. Conditions re-evaluation.' \
                    .format(time_stamp(time.time()))
                logging.warning(log)
                time.sleep(1)
                break


def elderbot(mode, crypto_currency, fiat_currency, depth):
    """
    elder_trading is a custom, real time, multiple time frame, consulting-trading bot application,
    interpretation of Alexander Elder's "triple screen" forex market trading strategy.
    The strategy.
    The strategy is using data from three time frames, calculating indicators on first two and acts on the third.

    First frame used for establishing a trading bias.
    Second frame applies technical indicators to identify retracements against the trading bias established earlier.
    Third frame is used for timing entries using short-term breakouts in the direction of your trading bias.
    Program starts with higher degree time frame and subsequently downgrades time frames lower progressively.

    Frames combinations:
    Combination 1: High 24hours - mid 4 hours - low 1 hour.
    Combination 2: High 4 hours - mid 1 hour - low 15 min.
    Combination 3: High 1 hour - mid 15 min - low 5 min.

    Evaluation phases
    1) Trend. The long-term trend is evaluated. – Alex Elder calls this as being the tide, and it's evaluation gives
    the general trend direction.
    2) Correction. The medium-term trend is evaluated. – This trend is also known as the wave, gives the trend momentum
    strength and position.
    3) Specification. - The short-term trend – It is also referred to as the ripple used to set limits of buy and stop
    loss. Exact entry point is corrected by closely monitoring price movement.
    High frame.
    General trend can be detected with the use of 200 periods EMA, combination of 9, 20, 50 periods EMA, macd, etc.
    According to Elder the highly profitable spectrum of a positive trend is when price overcomes a pullback,
    entering the bullish zone.
    In our case a preset combination of 13p EMA, 30p EMA and macd indicators is used to determine the high frame trend.
    Mid-frame.
    Trend momentum and position is detected with the use of stochastic slow indicator. Stochastic fast can be used for
    quicker response but in this case more force signals are generated. Stochastic slow is used as it is a 'smothered'
    version of stoch fast. An additional indicator of strength is added (rsi) for safety reasons, as when current price
    strength is above safety, price is actually 'overbought' and probability of descent is high.
    Low frame.
    When conditions are aligned in the higher frames action limits are set, according to the last low frame
    closed candle range. Next time fragment of candle price gives action flag or sets new limits.
    https://en.wikipedia.org/wiki/Alexander_Elder
    elder.com
    tradingstrategyguides.com
    www.elearnmarkets.com

    Original strategy dictates to wait the whole time of each candle to set condition flag,
        but as api provides data in real time, duration is divided to make bot faster.
        Next, condition (get_condition()) is taken from users account balance
        and bot constantly evaluates the flags in a while loop.
        if condition is 'buy':
            if 24 hour high frame trend is positive (True trend flag):
                if 4 hour mid-frame conditions are aligned (buy or sell flag True according to condition):
                    order_manager() kicks in to buy on 1 hour low frame.
                elif 4 hour mid-frame conditions are NOT aligned:
                    if 4 hour high frame trend is positive:
                        if 1 hour mid-frame conditions are aligned:
                            order_manager() kicks in to buy on 15 min low frame.
                        elif 1 hour mid-frame conditions are NOT aligned:
                            if 1 hour high frame trend is positive:
                                if 15-min mid-frame conditions are aligned:
                                    order_manager() kicks in to buy on 5 min low frame.
                                elif 15-min mid-frame conditions are NOT aligned:
                                    sleep 5 minutes to review conditions.
            elif 4 hour high frame trend is positive ...same as above for lower frames (H4 M1 L15 and H1 M15 L5)...
            elif 1 hour high frame trend is positive ... same as above for lower frames (H1 M15 L5)...
            elif conditions at all time frame combinations are not aligned:
                bot sleeps for 5 minutes to review conditions.
        elif condition is 'sell':
            if new closing price < stop:
                pillow
            elif 24 hour high frame and 4 hour mid-frame conditions are aligned (both flags True):
                order_manager() kicks in to sell on 1 hour low frame.
                if NOT waits 1 / 6 of 4 hours.
            elif 4 hour high frame and 1 hour mid-frame conditions are aligned (both flags True):
                order_manager() kicks in to sell on 15 min low frame.
                if NOT waits 1 / 6 of 1 hour.
            elif 1 hour high frame and 15min  mid-frame conditions are aligned (both flags True):
                order_manager() kicks in to sell on 5min low frame.
                if NOT waits 1 / 6 of 15 min.
            elif all high frames trend is negative:
                second pillow condition is activated.
                order_manager() kicks in to sell on 5minute low frame.
    :param mode: trading / consulting
    :param crypto_currency: the crypto asset to be traded
    :param fiat_currency: the fiat asset to be traded
    :param depth: the time periods back to be analysed
    """

    global condition
    global log
    global trend_24h
    global trend_4h
    global trend_1h
    global buy_flag_4h
    global sell_flag_4h
    global buy_flag_1h
    global sell_flag_1h
    global buy_flag_15m
    global sell_flag_15m
    global crypto_balance
    global fiat_balance
    global high_frame_24h
    global high_frame_4h
    global high_frame_1h
    global mid_frame_4h
    global mid_frame_1h
    global mid_frame_15m

    i24h_frame = Api(crypto_currency, fiat_currency, 1440, depth)
    i4h_frame = Api(crypto_currency, fiat_currency, 240, depth)
    i1h_frame = Api(crypto_currency, fiat_currency, 60, depth)
    i15m_frame = Api(crypto_currency, fiat_currency, 15, depth)
    i1h_feed = Api(crypto_currency, fiat_currency, 60, 1)
    i15m_feed = Api(crypto_currency, fiat_currency, 15, 1)
    i5m_feed = Api(crypto_currency, fiat_currency, 5, 1)
    log = '{} Elder bot start.'.format(time_stamp(time.time()))
    logging.warning(log)
    while True:
        if exit_event.is_set():  # thread "kill" by user
            cancel_order()
            log = '{} Break trading.'.format(time_stamp(time.time()))
            logging.warning(log)
            break
        condition = get_condition(crypto_currency)
        log = '{} Condition is {}.'.format(time_stamp(time.time()), condition)
        logging.info(log)
        high_frame_24h = high_frame_indicators(i24h_frame.get_frame())
        high_frame_4h = high_frame_indicators(i4h_frame.get_frame())
        high_frame_1h = high_frame_indicators(i1h_frame.get_frame())
        mid_frame_4h = mid_frame_indicators(i4h_frame.get_frame())
        mid_frame_1h = mid_frame_indicators(i1h_frame.get_frame())
        mid_frame_15m = mid_frame_indicators(i15m_frame.get_frame())
        trend_24h = high_frame_24h.iloc[-1]['trend']
        trend_4h = high_frame_4h.iloc[-1]['trend']
        trend_1h = high_frame_1h.iloc[-1]['trend']
        buy_flag_4h = mid_frame_4h.iloc[-1]['buy flag']
        sell_flag_4h = mid_frame_4h.iloc[-1]['sell flag']
        buy_flag_1h = mid_frame_1h.iloc[-1]['buy flag']
        sell_flag_1h = mid_frame_1h.iloc[-1]['sell flag']
        buy_flag_15m = mid_frame_15m.iloc[-1]['buy flag']
        sell_flag_15m = mid_frame_15m.iloc[-1]['sell flag']
        if condition == 'buy':
            if trend_24h:
                log = '{} 24hour trend is {}'.format(time_stamp(time.time()), trend_24h)
                logging.info(log)
                log = '{} mid 4hour frame buy flag is {}. mid 4hour frame sell flag is {}.' \
                    .format(time_stamp(time.time()), buy_flag_4h, sell_flag_4h)
                logging.info(log)
                if buy_flag_4h:
                    log = '{} 4hour momentum is strong.'.format(time_stamp(time.time()))
                    logging.info(log)
                    if mode == 'trading':
                        order_manager('market', i4h_frame, i1h_feed, condition, fiat_currency, crypto_currency)
                    elif mode == 'consulting':
                        limit_manager(i4h_frame, i1h_feed, condition)
                elif buy_flag_4h is not True:
                    log = '{} 4hour momentum is not strong.'.format(time_stamp(time.time()))
                    logging.info(log)
                    if trend_4h:
                        logging.info('{} 4hour trend is {}.'.format(time_stamp(time.time()), trend_4h))
                        logging.info(log)
                        log = '{} mid 1hour frame buy flag is {}. mid 1hour frame sell flag is {}.' \
                            .format(time_stamp(time.time()), buy_flag_1h, buy_flag_1h)
                        logging.info(log)
                        if buy_flag_1h:
                            log = '{} 1hour momentum is strong.'.format(time_stamp(time.time()))
                            logging.info(log)
                            if mode == 'trading':
                                order_manager('market', i1h_frame, i15m_feed, condition, fiat_currency, crypto_currency)
                            elif mode == 'consulting':
                                limit_manager(i1h_frame, i15m_feed, condition)
                        elif buy_flag_1h is not True:
                            log = '{} 1hour momentum is not strong.'.format(time_stamp(time.time()))
                            logging.info(log)
                            if trend_1h:
                                log = '{} 1hour trend is {}.'.format(time_stamp(time.time()), trend_1h)
                                logging.info(log)
                                log = '{} mid15 min frame buy flag is {}. mid15 min frame sell flag is {}.' \
                                    .format(time_stamp(time.time()), buy_flag_15m, sell_flag_15m)
                                logging.info(log)
                                if buy_flag_15m:
                                    log = '{} 15min momentum is strong.'.format(time_stamp(time.time()))
                                    logging.info(log)
                                    if mode == 'trading':
                                        order_manager('market', i15m_frame, i5m_feed, condition,
                                                      fiat_currency, crypto_currency)
                                    elif mode == 'consulting':
                                        limit_manager(i15m_frame, i5m_feed, condition)
                                elif buy_flag_15m is not True:
                                    log = '{} 15 min momentum is not strong. Wait 5 minutes.' \
                                        .format(time_stamp(time.time()))
                                    logging.info(log)
                                    time.sleep(i5m_feed.candle)
                            elif trend_1h is not True:
                                log = '{} 1hour trend is {}. No buying opportunity. Wait 5 minutes.' \
                                    .format(time_stamp(time.time()), trend_1h)
                                logging.info(log)
                                time.sleep(i5m_feed.candle)
                    elif trend_4h is not True:
                        log = '{} 4hour trend is {}.'.format(time_stamp(time.time()), trend_4h)
                        logging.info(log)
                        if trend_1h:
                            log = '{} 1hour trend is {}.'.format(time_stamp(time.time()), trend_1h)
                            logging.info(log)
                            log = '{} mid15 min frame buy flag is {}. mid15 min frame sell flag is {}.' \
                                .format(time_stamp(time.time()), buy_flag_15m, sell_flag_15m)
                            logging.info(log)
                            if buy_flag_15m:
                                log = '{} 15min momentum is strong.'.format(time_stamp(time.time()))
                                logging.info(log)
                                if mode == 'trading':
                                    order_manager('market', i15m_frame, i5m_feed, condition,
                                                  fiat_currency, crypto_currency)
                                elif mode == 'consulting':
                                    limit_manager(i15m_frame, i5m_feed, condition)
                            elif buy_flag_15m is not True:
                                log = '{} 15 min momentum is not strong. Wait 5 minutes.'\
                                    .format(time_stamp(time.time()))
                                logging.info(log)
                                time.sleep(i5m_feed.candle)
                        elif trend_1h is not True:
                            log = '{} 1hour trend is {}. No buying opportunity. Wait 5 minutes.' \
                                .format(time_stamp(time.time()), trend_1h)
                            logging.info(log)
                            time.sleep(i5m_feed.candle)
            elif trend_4h:
                log = '{} 4hour trend is {}.'.format(time_stamp(time.time()), trend_4h)
                logging.info(log)
                log = '{} mid 1hour frame buy flag is {}. mid 1hour frame sell flag is {}.' \
                    .format(time_stamp(time.time()), buy_flag_1h, buy_flag_1h)
                logging.info(log)
                if buy_flag_1h:
                    log = '{} 1hour momentum is strong.'.format(time_stamp(time.time()))
                    logging.info(log)
                    if mode == 'trading':
                        order_manager('limit', i1h_frame, i15m_feed, condition, fiat_currency, crypto_currency)
                    elif mode == 'consulting':
                        limit_manager(i1h_frame, i15m_feed, condition)
                elif buy_flag_1h is not True:
                    log = '{} 1hour momentum is not strong.'.format(time_stamp(time.time()))
                    logging.info(log)
                    if trend_1h:
                        log = '{} 1hour trend is {}.'.format(time_stamp(time.time()), trend_1h)
                        logging.info(log)
                        log = '{} mid15 min frame buy flag is {}. mid15 min frame sell flag is {}.' \
                            .format(time_stamp(time.time()), buy_flag_15m, sell_flag_15m)
                        logging.info(log)
                        if buy_flag_15m:
                            log = '{} 15min momentum is strong.'.format(time_stamp(time.time()))
                            logging.info(log)
                            if mode == 'trading':
                                order_manager('market', i15m_frame, i5m_feed, condition, fiat_currency, crypto_currency)
                            elif mode == 'consulting':
                                limit_manager(i15m_frame, i5m_feed, condition)
                        elif buy_flag_15m is not True:
                            log = '{} 15min momentum is not strong. Wait 5 minutes.'.format(time_stamp(time.time()))
                            logging.info(log)
                            time.sleep(i5m_feed.candle)
                    elif trend_1h is not True:
                        log = '1hour trend is {}. {} No buying opportunity. Wait 5 minutes.' \
                            .format(time_stamp(time.time()), trend_1h)
                        logging.info(log)
                        time.sleep(i5m_feed.candle)
            elif trend_1h:
                log = '{} 1hour trend is {}.'.format(time_stamp(time.time()), trend_1h)
                logging.info(log)
                log = '{} mid15 min frame buy flag is {}. mid15 min frame sell flag is {}.' \
                    .format(time_stamp(time.time()), buy_flag_15m, sell_flag_15m)
                logging.info(log)
                if buy_flag_15m:
                    log = '{} 15min momentum is strong.'.format(time_stamp(time.time()))
                    logging.info(log)
                    order_manager('market', i15m_frame, i5m_feed, condition, fiat_currency, crypto_currency)
                elif buy_flag_15m is not True:
                    log = '{} 15min momentum is not strong. Wait 5 minutes.'.format(time_stamp(time.time()))
                    logging.info(log)
                    time.sleep(i5m_feed.candle)
            else:
                log = '{} All high frames trends are negative. No buying opportunity. Wait 5 minutes.' \
                    .format(time_stamp(time.time()))
                logging.info(log)
                time.sleep(i5m_feed.candle)
        elif condition == 'sell':
            if i5m_feed.get_frame().iloc[-1]['close'] < pillow:  # pillow
                if mode == 'trading':
                    order_manager('market', i4h_frame, i1h_feed, condition, fiat_currency, crypto_currency)
                log = '{} Warning. Pillow activated. Sell your asset.'.format(time_stamp(time.time()))
                logging.info(log)
            elif trend_24h:
                log = '{} 24hour trend is {}.'.format(time_stamp(time.time()), trend_24h)
                logging.info(log)
                log = '{} mid 4hour frame buy flag is {}. mid 4hour frame sell flag is {}.' \
                    .format(time_stamp(time.time()), buy_flag_4h, sell_flag_4h)
                logging.info(log)
                if sell_flag_4h:
                    log = '{} 4hour momentum is weak.'.format(time_stamp(time.time()))
                    logging.info(log)
                    if mode == 'trading':
                        order_manager('market', i4h_frame, i1h_feed, condition, fiat_currency, crypto_currency)
                    elif mode == 'consulting':
                        limit_manager(i4h_frame, i1h_feed, condition)
                elif sell_flag_4h is not True:
                    log = '{} 4hour momentum is not weak. Wait {} minutes.' \
                        .format(time_stamp(time.time()), i4h_frame.interval / 10)
                    logging.info(log)
                    time.sleep(i4h_frame.candle / 10)
            elif trend_4h:
                log = '{} 4hour trend is {}.'.format(time_stamp(time.time()), trend_4h)
                logging.info(log)
                log = '{} mid 1hour frame buy flag is {}. mid 1hour frame sell flag is {}.' \
                    .format(time_stamp(time.time()), buy_flag_1h, sell_flag_1h)
                logging.info(log)
                if sell_flag_1h:
                    log = '{} 1hour momentum is weak.'.format(time_stamp(time.time()))
                    logging.info(log)
                    if mode == 'trading':
                        order_manager('market', i1h_frame, i15m_feed, condition, fiat_currency, crypto_currency)
                    elif mode == 'consulting':
                        limit_manager(i1h_frame, i15m_feed, condition)
                elif sell_flag_1h is not True:
                    log = '1hour momentum is not weak. Wait {} minutes.'.format(i1h_frame.interval / 10)
                    logging.info(log)
                    time.sleep(i1h_frame.candle / 10)
            elif trend_1h:
                log = '{} 1hour trend is {}.'.format(time_stamp(time.time()), trend_1h)
                logging.info(log)
                log = '{} mid15 min frame buy flag is {}. mid15 min frame sell flag is {}.' \
                    .format(time_stamp(time.time()), buy_flag_15m, sell_flag_15m)
                logging.info(log)
                if sell_flag_15m:
                    log = '{} 15min momentum is weak.'.format(time_stamp(time.time()))
                    logging.info(log)
                    if mode == 'trading':
                        order_manager('market', i15m_frame, i5m_feed, condition, fiat_currency, crypto_currency)
                    elif mode == 'consulting':
                        limit_manager(i15m_frame, i5m_feed, condition)
                elif sell_flag_15m is not True:
                    log = '{} 15min momentum not weak. Wait {} minutes.' \
                        .format(time_stamp(time.time()), i15m_frame.interval / 10)
                    logging.info(log)
                    time.sleep(i15m_frame.candle / 10)
            else:
                log = '{} All high frames trends are negative.' \
                    .format(time_stamp(time.time()))
                logging.info(log)
                if mode == 'trading':
                    order_manager('market', i15m_frame, i5m_feed, condition, fiat_currency, crypto_currency)
                elif mode == 'consulting':
                    log = 'Please sell your asset'
                    limit_manager(i15m_frame, i5m_feed, condition)
                    logging.info(log)


def data_feed():
    return {'log': log,
            'condition': condition,
            'crypto_balance': crypto_balance,
            'fiat_balance': fiat_balance,
            'stop': stop,
            'limit': limit,
            'pillow': pillow,
            'trend_24h': str(trend_24h),
            'trend_4h': str(trend_4h),
            'trend_1h': str(trend_1h),
            'buy_flag_4h': str(buy_flag_4h),
            'sell_flag_4h': str(sell_flag_4h),
            'buy_flag_1h': str(buy_flag_1h),
            'sell_flag_1h': str(sell_flag_1h),
            'buy_flag_15m': str(buy_flag_15m),
            'sell_flag_15m': str(sell_flag_15m)
            }
