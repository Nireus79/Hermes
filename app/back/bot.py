import logging
import time
import threading
from app.back.kraken import Api, high_frame_indicators, mid_frame_indicators, time_stamp, \
    volume, add_order, get_order_info, cancel_order, get_condition

logging.basicConfig(level=logging.INFO)

condition = None
stop = None
limit = None
new_closing = None
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


def signal_handler():
    exit_event.set()


def limit_manager(mid, instance, cond):
    """
    Same as order_manager.
    Simulator mode.
    condition (cond) variable is set manually to 'buy' from elder_cons and
    taken by arg.
    status variable is set manually to 'open'
    No actual order is set.
    Instead, in case of buy conditions fulfilled,
    user is notified and cond is set to 'sell'.
    :param mid: mid-frame instance
    :param instance: low-frame instance
    :param cond: buy / sell
    """
    global condition
    global stop
    global limit
    global log
    global new_closing
    log = '{} Start setting {}min low frame {} limits.'.format(time_stamp(time.time()), instance.interval, cond)
    logging.info(log)
    new = instance.get_frame().iloc[-1]
    limit = new['high']
    stop = new['low']
    log = '{} limit {}. Stop loss-Pillow {}.'.format(time_stamp(time.time()), limit, stop)
    logging.info(log)
    if cond == 'buy':
        status = 'open'
        if status == 'open':
            log = 'Please set limit buy order to {}. Wait {}min.'.format(limit, instance.interval / 4)
            logging.info(log)
            time.sleep(instance.candle / 4)
            while True:
                if exit_event.is_set():
                    # thread "kill" by user
                    log = '{} Operation interrupted by user.'.format(time_stamp(time.time()))
                    logging.info(log)
                    break
                if status == 'open':
                    buy_flag = mid_frame_indicators(mid.get_frame()).iloc[-1]['buy flag']
                    if buy_flag:
                        new = instance.get_frame().iloc[-1]
                        limit = new['high']
                        stop = new['low']
                        new_closing = new['close']
                        if new['close'] < stop:
                            log = 'Please set new limit order to {}. Wait {}min.'.format(limit, instance.interval / 4)
                            logging.info(log)
                            time.sleep(instance.candle / 4)
                        elif new['close'] >= stop:
                            log = '{} {} at {}. Please set sell pillow to {}. Frame {} min.' \
                                .format(time_stamp(time.time()), condition, new['close'], stop, instance.interval)
                            logging.info(log)
                            condition = 'sell'
                            break
                        else:
                            log = 'Order still open. Wait {}min.'.format(instance.interval / 4)
                            logging.info(log)
                            time.sleep(instance.candle / 4)
                    else:
                        log = '{} Mid frame momentum reversed to weak. Conditions re-evaluation.' \
                              ' Please cancel all active orders' \
                            .format(time_stamp(time.time()))
                        logging.info(log)
                        break
                else:
                    log = 'Please set sell pillow to {}'.format(stop)
                    logging.info(log)
                    break
    elif cond == 'sell':
        status = 'open'
        if status == 'open':
            log = 'Please set limit sell order to {}. Wait {}min.'.format(limit, instance.interval / 4)
            logging.info(log)
            time.sleep(instance.candle / 4)
            while True:
                if exit_event.is_set():
                    # thread "kill" by user
                    log = '{} Operation interrupted by user.'.format(time_stamp(time.time()))
                    logging.info(log)
                    break
                if status == 'open':
                    sell_flag = mid_frame_indicators(mid.get_frame()).iloc[-1]['sell flag']
                    if sell_flag:
                        new = instance.get_frame().iloc[-1]
                        limit = new['high']
                        stop = new['low']
                        new_closing = new['close']
                        if new['close'] > limit:
                            log = 'Please set new limit order to {}. Wait {}min.'.format(stop, instance.interval / 4)
                            logging.info(log)
                            time.sleep(instance.candle / 4)
                        elif new['close'] <= limit:
                            log = '{} {} at {}. Frame {}min.' \
                                .format(time_stamp(time.time()), condition, new['close'], instance.interval)
                            logging.info(log)
                            condition = 'buy'
                        else:
                            log = 'Order still open. Wait {}min.'.format(instance.interval / 4)
                            logging.info(log)
                            time.sleep(instance.candle / 4)
                    else:
                        log = '{} Mid frame momentum reversed to strong. Conditions re-evaluation.' \
                              ' Please cancel all active orders' \
                            .format(time_stamp(time.time()))
                        logging.info(log)
                        break
                # else:
                #     log = 'Limit order closed. Crypto sold.'
                #     logging.info(log)
                #     break


def order_manager(mid, instance, cond, crypto_currency, fiat_currency):
    """
    When conditions to buy or sell are aligned in higher frames (buy or sell flag True)
    order_manager takes limit, stop, and private account balance (crypto and fiat)
    then places a limit order right away
    If condition is buy, places a limit order at the price of the higher high of the current low frame period candle.
    If condition is sell places a limit order at the lower low of the current low frame period candle.
    Then waits for 1/4 of the current low frame period candle.
    if the order is still open:
        if flag is still True:
            takes new current price.
            if current price exceeds expectations *
                * (in case of sell is higher than higher high of current running candle fragment(1/4)/
                    in case of buy is lower than lower low of current running low candle fragment(1/4))
                previous order is cancelled and a new one is set.
            else:
                (That means current price is between limit order and expectations)
                Just waits another 1/4 of low candle time.
        else:
            (That means momentum is reversed in mid-frame)
            Last order is cancelled and order manager breaks the loop
            to start evaluating conditions again in welder()
    else:
        (That means initial limit order is closed)
        If that was to buy a pillow limit order is set and manager loop breaks.
        If that was to sell loop just breaks.
    :param crypto_currency:
    :param fiat_currency:
    :param mid: mid-frame instance
    :param instance: low-frame instance
    :param cond: buy / sell
    """
    global condition
    global stop
    global limit
    global log
    global fiat_balance
    global crypto_balance
    global new_closing
    log = '{} Start setting {}min low frame {} limits.'.format(time_stamp(time.time()), instance.interval, cond)
    logging.info(log)
    new = instance.get_frame().iloc[-1]
    vol = volume(fiat_currency, crypto_currency)
    limit = new['high']
    stop = new['low']
    crypto_balance = vol[crypto_currency]
    fiat_balance = vol[fiat_currency]
    log = '{} limit {}. Stop loss-Pillow {}.'.format(time_stamp(time.time()), limit, stop)
    logging.info(log)
    log = 'Balance: {} crypto, {} money'.format(crypto_balance, fiat_balance)
    logging.info(log)
    if cond == 'buy':
        tx = add_order('limit', cond, fiat_balance, limit, fiat_currency, crypto_currency)['txid']
        status = get_order_info(tx)
        if status == 'open':
            log = 'Limit order added to {}. Wait {}min.'.format(limit, instance.interval / 4)
            logging.info(log)
            time.sleep(instance.candle / 4)
            while True:
                if exit_event.is_set():
                    # thread "kill" by user
                    cancel_order()
                    log = '{} Break ordering.'.format(time_stamp(time.time()))
                    logging.info(log)
                    break
                status = get_order_info(tx)
                if status == 'open':
                    buy_flag = mid_frame_indicators(mid.get_frame()).iloc[-1]['buy flag']
                    if buy_flag:
                        new = instance.get_frame().iloc[-1]
                        limit = new['high']
                        stop = new['low']
                        new_closing = new['close']
                        if new['close'] < stop:
                            cancel_order()
                            tx = add_order('limit', cond, fiat_balance, limit, fiat_currency, crypto_currency)['txid']
                            log = 'New limit order added to {}. Wait {}min.'.format(limit, instance.interval / 4)
                            logging.info(log)
                            time.sleep(instance.candle / 4)
                        else:
                            log = 'Order still open. Wait {}min.'.format(instance.interval / 4)
                            logging.info(log)
                            time.sleep(instance.candle / 4)
                    else:
                        cancel_order()
                        log = '{} Mid frame momentum reversed to weak. Conditions re-evaluation.' \
                            .format(time_stamp(time.time()))
                        logging.info(log)
                        break
                else:
                    crypto = volume(fiat_currency, crypto_currency)[crypto_currency]
                    add_order('limit', 'sell', crypto, stop, fiat_currency, crypto_currency)  # Pillow.
                    log = 'Pillow set to {}'.format(stop)
                    logging.info(log)
                    break
    elif cond == 'sell':
        cancel_order()  # Canceling previous pillow.
        tx = add_order('limit', cond, crypto_balance, stop, fiat_currency, crypto_currency)['txid']
        status = get_order_info(tx)
        if status == 'open':
            log = 'Limit order added to {}. Wait {}min.'.format(limit, instance.interval / 4)
            logging.info(log)
            time.sleep(instance.candle / 4)
            while True:
                status = get_order_info(tx)
                if status == 'open':
                    sell_flag = mid_frame_indicators(mid.get_frame()).iloc[-1]['sell flag']
                    if sell_flag:
                        new = instance.get_frame().iloc[-1]
                        limit = new['high']
                        stop = new['low']
                        new_closing = new['close']
                        if new['close'] > limit:
                            cancel_order()
                            tx = add_order('limit', cond, crypto_balance, stop, fiat_currency, crypto_currency)['txid']
                            log = 'New limit order added to {}. Wait {}min.'.format(stop, instance.interval / 4)
                            logging.info(log)
                            time.sleep(instance.candle / 4)
                        else:
                            log = 'Order still open. Wait {}min.'.format(instance.interval / 4)
                            time.sleep(instance.candle / 4)
                    else:
                        cancel_order()
                        log = '{} Mid frame momentum reversed to strong. Conditions re-evaluation.' \
                            .format(time_stamp(time.time()))
                        logging.info(log)
                        break
                else:
                    log = 'Limit order closed. Crypto sold.'
                    logging.info(log)
                    break


def elder_cons(crypto_currency, fiat_currency, depth):
    """
    Same as elder_trading.
    In this case condition is not taken as a result of account balance.
    Is set to 'buy' from the beginning and limit_manager is called.
    No actual order is set.
    User is just informed for the simulated action.
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
    global high_frame_24h
    global high_frame_4h
    global high_frame_1h
    global mid_frame_4h
    global mid_frame_1h
    global mid_frame_15m

    i24h_frame = Api(crypto_currency, fiat_currency, 1440, depth)
    i4h_frame = Api(crypto_currency, fiat_currency, 240, depth)
    i1h_frame = Api(crypto_currency, fiat_currency, 60, depth)
    i30m_frame = Api(crypto_currency, fiat_currency, 30, depth)
    i15m_frame = Api(crypto_currency, fiat_currency, 15, depth)

    i4h_feed = Api(crypto_currency, fiat_currency, 240, 1)
    i1h_feed = Api(crypto_currency, fiat_currency, 60, 1)
    i30m_feed = Api(crypto_currency, fiat_currency, 30, 1)
    i15m_feed = Api(crypto_currency, fiat_currency, 15, 1)
    i5m_feed = Api(crypto_currency, fiat_currency, 5, 1)

    log = '{} Elder bot start.'.format(time_stamp(time.time()))
    logging.info(log)

    while True:
        if exit_event.is_set():
            # thread "kill" by user
            log = '{} Break consulting.'.format(time_stamp(time.time()))
            logging.info(log)
            break
        condition = 'buy'
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
                    limit_manager(i4h_frame, i1h_feed, condition)
                elif buy_flag_4h is not True:
                    log = '{} 4hour momentum is weak.'.format(time_stamp(time.time()))
                    logging.info(log)
                    if trend_4h:
                        log = '{} 4hour trend is {}.'.format(time_stamp(time.time()), trend_4h)
                        logging.info(log)

                        log = '{} mid 1hour frame buy flag is {}. mid 1hour frame sell flag is {}.' \
                            .format(time_stamp(time.time()), buy_flag_1h, sell_flag_1h)
                        logging.info(log)
                        if buy_flag_1h:
                            log = '{} 1hour momentum is strong.'.format(time_stamp(time.time()))
                            logging.info(log)
                            limit_manager(i1h_frame, i15m_feed, condition)
                        elif buy_flag_1h is not True:
                            log = '{} 1hour momentum is weak.'.format(time_stamp(time.time()))
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
                                    limit_manager(i15m_frame, i5m_feed, condition)
                                elif buy_flag_15m is not True:
                                    log = '{} 15 min momentum is weak. Wait 5 minutes.' \
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
                                limit_manager(i15m_frame, i5m_feed, condition)
                            elif buy_flag_15m is not True:
                                log = '{} 15 min momentum is weak. Wait 5 minutes.'.format(time_stamp(time.time()))
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
                    .format(time_stamp(time.time()), buy_flag_1h, sell_flag_1h)
                logging.info(log)
                if buy_flag_1h:
                    log = '{} 1hour momentum is strong.'.format(time_stamp(time.time()))
                    logging.info(log)
                    limit_manager(i1h_frame, i15m_feed, condition)
                elif buy_flag_1h is not True:
                    log = '{} 1hour momentum is weak.'.format(time_stamp(time.time()))
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
                            limit_manager(i15m_frame, i5m_feed, condition)
                        elif buy_flag_15m is not True:
                            log = '{} 15min momentum is weak. Wait 5 minutes.'.format(time_stamp(time.time()))
                            logging.info(log)
                            time.sleep(i5m_feed.candle)
                    elif trend_1h is not True:
                        log = '{} 1hour trend is {}. No buying opportunity. Wait 5 minutes.' \
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
                    limit_manager(i15m_frame, i5m_feed, condition)
                elif buy_flag_15m is not True:
                    log = '{} 15min momentum is weak. Wait 5 minutes.'.format(time_stamp(time.time()))
                    logging.info(log)
                    time.sleep(i5m_feed.candle)
            else:
                log = '{} All high frames trends are negative. No buying opportunity. Wait 5 minutes.' \
                    .format(time_stamp(time.time()))
                logging.info(log)
                time.sleep(i5m_feed.candle)
        elif condition == 'sell':
            if trend_24h:
                log = '{} 24hour trend is {}.'.format(time_stamp(time.time()), trend_24h)
                logging.info(log)
                log = '{} mid 4hour frame buy flag is {}. mid 4hour frame sell flag is {}.' \
                    .format(time_stamp(time.time()), buy_flag_4h, sell_flag_4h)
                logging.info(log)
                if sell_flag_4h:
                    log = '{} 4hour momentum is weak.'.format(time_stamp(time.time()))
                    logging.info(log)
                    limit_manager(i4h_frame, i1h_feed, condition)
                elif sell_flag_4h is not True:
                    log = '{} 4hour momentum is strong. Wait {} minutes.' \
                        .format(time_stamp(time.time()), i4h_frame.interval / 4)
                    logging.info(log)
                    time.sleep(i4h_frame.candle / 4)
            elif trend_4h:
                log = '{} 4hour trend is {}.'.format(time_stamp(time.time()), trend_4h)
                logging.info(log)
                log = '{} mid 1hour frame buy flag is {}. mid 1hour frame sell flag is {}.' \
                    .format(time_stamp(time.time()), buy_flag_1h, sell_flag_1h)
                logging.info(log)
                if sell_flag_1h:
                    log = '{} 1hour momentum is weak.'.format(time_stamp(time.time()))
                    logging.info(log)
                    limit_manager(i1h_frame, i15m_feed, condition)
                elif sell_flag_1h is not True:
                    log = '1hour momentum is strong. Wait {} minutes.'.format(i1h_frame.interval / 4)
                    logging.info(log)
                    time.sleep(i1h_frame.candle / 4)
            elif trend_1h:
                log = '{} 1hour trend is {}.'.format(time_stamp(time.time()), trend_1h)
                logging.info(log)
                log = '{} mid15 min frame buy flag is {}. mid15 min frame sell flag is {}.' \
                    .format(time_stamp(time.time()), buy_flag_15m, sell_flag_15m)
                logging.info(log)
                if sell_flag_15m:
                    log = '{} 15min momentum is weak.'.format(time_stamp(time.time()))
                    logging.info(log)
                    limit_manager(i15m_frame, i5m_feed, condition)
                elif sell_flag_15m is not True:
                    log = '{} 15min momentum strong. Wait {} minutes.' \
                        .format(time_stamp(time.time()), i15m_frame.interval / 4)
                    logging.info(log)
                    time.sleep(i15m_frame.candle / 4)
            else:
                log = '{} All high frames trends are negative. Safe sell activated.' \
                    .format(time_stamp(time.time()))
                logging.info(log)
                limit_manager(i15m_frame, i5m_feed, condition)


def elder_trading(crypto_currency, fiat_currency, depth):
    """
        Original strategy dictates to wait the whole time of each candle to set condition flag,
        but as api provides data in real time, duration is divided to make bot faster.
        Next, condition (get_condition()) is taken from users account balance
        and bot constantly evaluates the flags in a while loop (asynchronous to the previous functions).
        if condition is 'buy':
            if 24 hour high frame trend is positive (True trend flag):
                if 4 hour mid-frame conditions are aligned (buy or sell flag True according to condition):
                    ratchet() kicks in to buy on 1 hour low frame.
                elif 4 hour mid-frame conditions are NOT aligned:
                    if 4 hour high frame trend is positive:
                        if 1 hour mid-frame conditions are aligned:
                            ratchet() kicks in to buy on 15 min low frame.
                        elif 1 hour mid-frame conditions are NOT aligned:
                            if 1 hour high frame trend is positive:
                                if 15-min mid-frame conditions are aligned:
                                    ratchet() kicks in to buy on 5 min low frame.
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
                ratchet() kicks in to sell on 1 hour low frame.
                if NOT waits 1 / 4 of 4 hours.
            elif 4 hour high frame and 1 hour mid-frame conditions are aligned (both flags True):
                ratchet() kicks in to sell on 15 min low frame.
                if NOT waits 1 / 4 of 1 hour.
            elif 1 hour high frame and 15min  mid-frame conditions are aligned (both flags True):
                ratchet() kicks in to sell on 5min low frame.
                if NOT waits 1 / 4 of 15 min.
            elif all high frames trend is negative:
                second pillow condition is activated.
                ratchet() kicks in to sell on 5minute low frame.
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
    i30m_frame = Api(crypto_currency, fiat_currency, 30, depth)
    i15m_frame = Api(crypto_currency, fiat_currency, 15, depth)

    i4h_feed = Api(crypto_currency, fiat_currency, 240, 1)
    i1h_feed = Api(crypto_currency, fiat_currency, 60, 1)
    i30m_feed = Api(crypto_currency, fiat_currency, 30, 1)
    i15m_feed = Api(crypto_currency, fiat_currency, 15, 1)
    i5m_feed = Api(crypto_currency, fiat_currency, 5, 1)

    log = '{} Elder bot start.'.format(time_stamp(time.time()))
    logging.info(log)
    while True:
        if exit_event.is_set():
            # thread "kill" by user
            log = '{} Break trading.'.format(time_stamp(time.time()))
            logging.info(log)
            break
        condition, crypto, fiat = get_condition(fiat_currency, crypto_currency)
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
                    order_manager(i4h_frame, i1h_feed, condition, fiat_currency, crypto_currency)
                elif buy_flag_4h is not True:
                    log = '{} 4hour momentum is weak.'.format(time_stamp(time.time()))
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
                            order_manager(i1h_frame, i15m_feed, condition, fiat_currency, crypto_currency)
                        elif buy_flag_1h is not True:
                            log = '{} 1hour momentum is weak.'.format(time_stamp(time.time()))
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
                                    order_manager(i15m_frame, i5m_feed, condition, fiat_currency, crypto_currency)
                                elif buy_flag_15m is not True:
                                    log = '{} 15 min momentum is weak. Wait 5 minutes.' \
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
                                order_manager(i15m_frame, i5m_feed, condition, fiat_currency, crypto_currency)
                            elif buy_flag_15m is not True:
                                log = '{} 15 min momentum is weak. Wait 5 minutes.'.format(time_stamp(time.time()))
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
                    order_manager(i1h_frame, i15m_feed, condition, fiat_currency, crypto_currency)
                elif buy_flag_1h is not True:
                    log = '{} 1hour momentum is weak.'.format(time_stamp(time.time()))
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
                            order_manager(i15m_frame, i5m_feed, condition, fiat_currency, crypto_currency)
                        elif buy_flag_15m is not True:
                            log = '{} 15min momentum is weak. Wait 5 minutes.'.format(time_stamp(time.time()))
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
                    order_manager(i15m_frame, i5m_feed, condition, fiat_currency, crypto_currency)
                elif buy_flag_15m is not True:
                    log = '{} 15min momentum is weak. Wait 5 minutes.'.format(time_stamp(time.time()))
                    logging.info(log)
                    time.sleep(i5m_feed.candle)
            else:
                log = '{} All high frames trends are negative. No buying opportunity. Wait 5 minutes.' \
                    .format(time_stamp(time.time()))
                logging.info(log)
                time.sleep(i5m_feed.candle)
        elif condition == 'sell':
            if trend_24h:
                log = '{} 24hour trend is {}.'.format(time_stamp(time.time()), trend_24h)
                logging.info(log)
                log = '{} mid 4hour frame buy flag is {}. mid 4hour frame sell flag is {}.' \
                    .format(time_stamp(time.time()), buy_flag_4h, sell_flag_4h)
                logging.info(log)
                if sell_flag_4h:
                    log = '{} 4hour momentum is weak.'.format(time_stamp(time.time()))
                    logging.info(log)
                    order_manager(i4h_frame, i1h_feed, condition, fiat_currency, crypto_currency)
                elif sell_flag_4h is not True:
                    log = '{} 4hour momentum is strong. Wait {} minutes.' \
                        .format(time_stamp(time.time()), i4h_frame.interval / 4)
                    logging.info(log)
                    time.sleep(i4h_frame.candle / 4)
            elif trend_4h:
                log = '{} 4hour trend is {}.'.format(time_stamp(time.time()), trend_4h)
                logging.info(log)
                log = '{} mid 1hour frame buy flag is {}. mid 1hour frame sell flag is {}.' \
                    .format(time_stamp(time.time()), buy_flag_1h, sell_flag_1h)
                logging.info(log)
                if sell_flag_1h:
                    log = '{} 1hour momentum is weak.'.format(time_stamp(time.time()))
                    logging.info(log)
                    order_manager(i1h_frame, i15m_feed, condition, fiat_currency, crypto_currency)
                elif sell_flag_1h is not True:
                    log = '1hour momentum is strong. Wait {} minutes.'.format(i1h_frame.interval / 4)
                    logging.info(log)
                    time.sleep(i1h_frame.candle / 4)
            elif trend_1h:
                log = '{} 1hour trend is {}.'.format(time_stamp(time.time()), trend_1h)
                logging.info(log)
                log = '{} mid15 min frame buy flag is {}. mid15 min frame sell flag is {}.' \
                    .format(time_stamp(time.time()), buy_flag_15m, sell_flag_15m)
                logging.info(log)
                if sell_flag_15m:
                    log = '{} 15min momentum is weak.'.format(time_stamp(time.time()))
                    logging.info(log)
                    order_manager(i15m_frame, i5m_feed, condition, fiat_currency, crypto_currency)
                elif sell_flag_15m is not True:
                    log = '{} 15min momentum strong. Wait {} minutes.' \
                        .format(time_stamp(time.time()), i15m_frame.interval / 4)
                    logging.info(log)
                    time.sleep(i15m_frame.candle / 4)
            else:
                log = '{} All high frames trends are negative. Safe sell activated.' \
                    .format(time_stamp(time.time()))
                logging.info(log)
                order_manager(i15m_frame, i5m_feed, condition, fiat_currency, crypto_currency)


def data_feed():
    return {'log': log,
            'condition': condition,
            'crypto_balance': crypto_balance,
            'fiat_balance': fiat_balance,
            'stop': stop,
            'limit': limit,
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
