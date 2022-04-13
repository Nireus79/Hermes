import logging
import time
import threading
import winsound
from app.back.kraken import Api, high_frame_indicators, mid_frame_indicators, low_frame_indicators, time_stamp, \
    volume, add_order, cancel_order, get_condition

logging.basicConfig(level=logging.INFO)

condition = None
stop = 0
limit = None
closing_price = None
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


def signal_handler():
    """
    Setting exit event to allow process end
    within while loops before program stop.
    """
    exit_event.set()


def beeper(cond):
    """
    Triggers sound signal user notifications on important trading events.
    :param cond: sell / buy / start (events)
    """
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
    elif cond == 'break':
        winsound.Beep(240, 2000)


def order_manager(order_type, mid, low, cond, crypto_currency, fiat_currency):
    """
    When conditions to buy or sell are aligned in higher frames (buy or sell flag True)
    order_manager is setting limit and stop loss levels.
    Then starts monitoring periodically closing price in 1/10 time fragments of current running low time frame duration:

        When intending to sell asset
            if closing price lower than set stop-loss level:
                places market sell order for the asset.
                Conditions are reevaluated until order is closed.
            else:
                waits 1 / 6 of low frame duration to reevaluate:
                    if new closing price is higher than stop-loss:
                        if new lower low of low frame is higher than previous set:
                            sets new stop-loss equal to new lower-low.
                        else:
                            waits 1 / 6 of low frame period.
        When intending to buy asset
            if closing price exceeds set limit level:
                places a market buy asset for the asset
                and sets mid-frame last candle low as pillow.
                Conditions are reevaluated until order is closed.
            else:
                waits 1 / 6 of low frame duration to reevaluate.
                    if new closing price is lower than limit:
                        if new higher high of low frame is higher than previous set:
                            sets new limit equal to new higher high.
                        else:
                            waits 1 / 6 of low frame period.
    :param order_type: limit / market
    :param crypto_currency: asset a
    :param fiat_currency: asset b
    :param mid: mid-frame instance
    :param low: low-frame instance
    :param cond: buy / sell
    In stop-loss/limit levels an extra margin of current atr (average true range) is added,
    to include the volatility factor and limit false positioning.
    After setting a buy order, a safety "pillow" level is stored as a safety parameter.
    It is the 'low' of mid-frame candle minus mid-frame atr.
    """
    global pillow
    global condition
    global stop
    global limit
    global log
    global closing_price
    beeper('start')
    log = '{} Setting {}min low frame {} limits.'.format(time_stamp(time.time()), low.interval, cond)
    logging.info(log)
    middle_f = mid_frame_indicators(mid.get_frame()).iloc[-1]
    low_f = low_frame_indicators(low.get_frame()).iloc[-1]
    m_atr = middle_f['atr']
    atr = low_f['atr']
    limit = low_f['high'] + atr
    stop = low_f['low'] - atr
    pillow = middle_f['low'] - m_atr
    closing_price = low_f['close']
    log = 'Balance: {} crypto, {} money'.format(crypto_balance, fiat_balance)
    logging.info(log)
    log = '{} Current price {}. limit {}. Stop loss-Pillow {}.' \
        .format(time_stamp(time.time()), closing_price, limit, stop)
    logging.info(log)
    log = 'Wait {}min.'.format(low.interval / 6)
    logging.info(log)
    time.sleep(low.candle / 6)
    while True:
        middle_f = mid_frame_indicators(mid.get_frame()).iloc[-1]
        low_f = low_frame_indicators(low.get_frame()).iloc[-1]
        buy_flag = middle_f['buy flag']
        sell_flag = middle_f['sell flag']
        m_atr = middle_f['atr']
        atr = low_f['atr']
        new_limit = low_f['high'] + atr
        new_stop = low_f['low'] - atr
        closing_price = low_f['close']
        if exit_event.is_set():  # thread "kill" by user
            cancel_order()
            log = '{} Break ordering.'.format(time_stamp(time.time()))
            logging.info(log)
            break
        elif cond == 'buy':
            if buy_flag:
                if closing_price > limit:
                    add_order(order_type, cond, fiat_balance, closing_price, crypto_currency, fiat_currency)
                    pillow = middle_f['low'] - m_atr
                    beeper(cond)
                    time.sleep(10)
                    break
                else:
                    if new_limit <= limit:
                        limit = new_limit
                        log = '{} limit set to {}. Wait {}min' \
                            .format(time_stamp(time.time()), limit, low.interval / 6)
                        logging.info(log)
                        time.sleep(low.candle / 6)
                    else:
                        log = '{} Closing price under limit. Wait {}min.' \
                            .format(time_stamp(time.time()), low.interval / 6)
                        logging.info(log)
                        time.sleep(low.candle / 6)
            elif buy_flag is not True:
                log = '{} Conditions re-evaluation.'.format(time_stamp(time.time()))
                logging.info(log)
                beeper('break')
                time.sleep(10)
                break
        elif cond == 'sell':
            if sell_flag:
                if closing_price < stop:
                    add_order(order_type, cond, fiat_balance, closing_price, crypto_currency, fiat_currency)
                    beeper(cond)
                    break
                else:
                    if new_stop >= stop:
                        stop = new_stop
                        log = '{} Stop loss set to {}. Wait {}min' \
                            .format(time_stamp(time.time()), stop, low.interval / 6)
                        logging.info(log)
                        time.sleep(low.candle / 6)
                    else:
                        log = '{} Closing price over stop. Wait {}min.' \
                            .format(time_stamp(time.time()), low.interval / 6)
                        logging.info(log)
                        time.sleep(low.candle / 6)
            elif sell_flag is not True:
                log = '{} Conditions re-evaluation.'.format(time_stamp(time.time()))
                logging.info(log)
                beeper('break')
                time.sleep(10)
                break


def limit_manager(mode, mid, low, cond):
    """
    Same as order_manager.
    No actual order is set.
    User is just informed for the action he has to take.
    :param mode: zero or consulting
    :param mid: The middle time frame instance, used to check if buy/sell flag is still True.
    :param low: The low time frame instance, used to set limit/stop-loss borders.
    :param cond: Condition sell/buy
    """
    global pillow
    global condition
    global stop
    global limit
    global log
    global closing_price
    beeper('start')
    log = '{} Setting {}min low frame {} limits.'.format(time_stamp(time.time()), low.interval, cond)
    logging.info(log)
    middle_f = mid_frame_indicators(mid.get_frame()).iloc[-1]
    low_f = low_frame_indicators(low.get_frame()).iloc[-1]
    m_atr = middle_f['atr']
    pillow = middle_f['low'] - m_atr
    atr = low_f['atr']
    limit = low_f['high'] + atr
    stop = low_f['low'] - atr
    closing_price = low_f['close']
    log = '{} Current price {}. limit: {}. Stop loss: {}. Pillow: {}. ' \
        .format(time_stamp(time.time()), closing_price, limit, stop, pillow)
    logging.info(log)
    if cond == 'buy':
        log = '{} Please give buy order when price exceeds {}. Wait {}min.' \
            .format(time_stamp(time.time()), limit, low.interval / 6)
    elif cond == 'sell':
        log = '{} Please give sell order when price under {}. Wait {}min.' \
            .format(time_stamp(time.time()), stop, low.interval / 6)
    logging.info(log)
    time.sleep(low.candle / 6)
    while True:
        middle_f = mid_frame_indicators(mid.get_frame()).iloc[-1]
        low_f = low_frame_indicators(low.get_frame()).iloc[-1]
        buy_flag = middle_f['buy flag']
        sell_flag = middle_f['sell flag']
        m_atr = middle_f['atr']
        atr = low_f['atr']
        new_limit = low_f['high'] + atr
        new_stop = low_f['low'] - atr
        pillow = middle_f['low'] - m_atr
        closing_price = low_f['close']
        if exit_event.is_set():  # thread "kill" by user
            log = '{} Operation interrupted by user.'.format(time_stamp(time.time()))
            logging.info(log)
            break
        if cond == 'buy':
            if buy_flag:
                if closing_price > limit:
                    log = '{} Closing price exceeded limit. Please add buy order'.format(time_stamp(time.time()))
                    logging.info(log)
                    beeper(cond)
                    time.sleep(10)
                    if mode == 'zero':
                        condition = 'sell'
                        logging.info('BUY')
                        logging.info(condition)
                    break
                elif closing_price <= limit:
                    if new_limit < limit:
                        limit = new_limit
                        stop = new_stop
                        log = '{} New limit set to {}. Please wait {}min.' \
                            .format(time_stamp(time.time()), limit, low.interval / 6)
                        logging.info(log)
                        time.sleep(low.candle / 6)
                    else:
                        log = '{} Closing price not exceeded limit. Please wait {}min.'.format(
                            time_stamp(time.time()), low.interval / 6)
                        logging.info(log)
                        time.sleep(low.candle / 6)
            elif buy_flag is not True:
                log = '{} Conditions re-evaluation.'.format(time_stamp(time.time()))
                logging.info(log)
                beeper('break')
                time.sleep(10)
                break
        elif cond == 'sell':
            if sell_flag:
                if closing_price < stop:
                    log = '{} Closing price under stop loss level. Please add sell order' \
                        .format(time_stamp(time.time()))
                    logging.info(log)
                    beeper(cond)
                    time.sleep(10)
                    if mode == 'zero':
                        condition = 'buy'
                        logging.info('SELL')
                        logging.info(condition)
                    break
                elif closing_price >= stop:
                    if new_stop > stop:
                        limit = new_limit
                        stop = new_stop
                        log = '{} New stop-loss set to {}. Please wait {}min.' \
                            .format(time_stamp(time.time()), stop, low.interval / 6)
                        logging.info(log)
                        time.sleep(low.candle / 6)
                    else:
                        log = '{} Closing price over stop-loss level. Please wait {}min.'.format(
                            time_stamp(time.time()), low.interval / 6)
                        logging.info(log)
                        time.sleep(low.candle / 6)
            elif sell_flag is not True:
                log = '{} Conditions re-evaluation.'.format(time_stamp(time.time()))
                logging.info(log)
                beeper('break')
                time.sleep(10)
                break


def elderbot(mode, crypto_currency, fiat_currency, depth):
    """
    Custom, real time, multiple time frame, consulting-trading bot application,
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
            elif 1 hour high frame trend is positive ... same as above for frames (H1 M15 L5) only...
            elif conditions at all time frame combinations are not aligned:
                bot sleeps for 5 minutes to review conditions.
        elif condition is 'sell':
            if new closing price < stop:
                pillow
            elif 24 hour high frame and 4 hour mid-frame conditions are aligned (both flags True):
                order_manager() kicks in to sell on 1 hour low frame.
                if NOT waits 1 / 12 of 4 hours.
            elif 4 hour high frame and 1 hour mid-frame conditions are aligned (both flags True):
                order_manager() kicks in to sell on 15 min low frame.
                if NOT waits 1 / 12 of 1 hour.
            elif 1 hour high frame and 15min  mid-frame conditions are aligned (both flags True):
                order_manager() kicks in to sell on 5min low frame.
                if NOT waits 1 / 12 of 15 min.
            elif all high frames trend is negative:
                second pillow condition is activated.
                order_manager() kicks in to sell on 5minute low frame.

    :param mode: trading / consulting
    :param crypto_currency: the crypto asset to be traded
    :param fiat_currency: the fiat asset to be traded
    :param depth: the time periods back to be analysed
    pillow: A safety level is set at the beginning of the process to 4% under current price
            and is added after every circle. That is for the case of bot starts evaluating sell condition and no other
            safety level is stored.
            After every buy of asset A, a safety level is set on the lowest low of mid-frame candle minus atr,
            so volatility is calculated in this case.
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
    global pillow
    global closing_price
    if mode == 'zero':
        condition = 'buy'
    elif mode == 'consulting' or mode == 'trading':
        vol = volume(crypto_currency, fiat_currency)
        crypto_balance = float(vol[crypto_currency])
        fiat_balance = float(vol[fiat_currency])
    i24h_frame = Api(crypto_currency, fiat_currency, 1440, depth)
    i4h_frame = Api(crypto_currency, fiat_currency, 240, depth)
    i1h_frame = Api(crypto_currency, fiat_currency, 60, depth)
    i15m_frame = Api(crypto_currency, fiat_currency, 15, depth)
    i5m_frame = Api(crypto_currency, fiat_currency, 5, depth)
    # Pillow set to 4% loss, in case of connection when condition is already 'sell'
    closing_price = i5m_frame.get_frame().iloc[-1]['close']
    pillow = closing_price * 0.96
    log = '{} Elder bot start.'.format(time_stamp(time.time()))
    logging.info(log)
    while True:
        if exit_event.is_set():  # thread "kill" by user
            cancel_order()
            log = '{} Break trading.'.format(time_stamp(time.time()))
            logging.info(log)
            break
        if mode == 'consulting' or mode == 'trading':
            condition = get_condition(crypto_currency, fiat_currency)
        log = '{} Condition is {}. Mode is {}.'.format(time_stamp(time.time()), condition, mode)
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
        # Pillow set to 4% loss, in case of connection when condition is already 'sell'
        closing_price = i5m_frame.get_frame().iloc[-1]['close']
        pillow = closing_price * 0.96
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
                        order_manager('market', i4h_frame, i1h_frame, condition, fiat_currency, crypto_currency)
                    elif mode == 'consulting' or mode == 'zero':
                        limit_manager(mode, i4h_frame, i1h_frame, condition)
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
                                order_manager('market', i1h_frame, i15m_frame, condition,
                                              fiat_currency, crypto_currency)
                            elif mode == 'consulting' or mode == 'zero':
                                limit_manager(mode, i1h_frame, i15m_frame, condition)
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
                                        order_manager('market', i15m_frame, i5m_frame, condition,
                                                      fiat_currency, crypto_currency)
                                    elif mode == 'consulting' or mode == 'zero':
                                        limit_manager(mode, i15m_frame, i5m_frame, condition)
                                elif buy_flag_15m is not True:
                                    log = '{} 15 min momentum is not strong. Wait 5 minutes.' \
                                        .format(time_stamp(time.time()))
                                    logging.info(log)
                                    time.sleep(i5m_frame.candle)
                            elif trend_1h is not True:
                                log = '{} 1hour trend is {}. No buying opportunity. Wait 5 minutes.' \
                                    .format(time_stamp(time.time()), trend_1h)
                                logging.info(log)
                                time.sleep(i5m_frame.candle)
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
                                    order_manager('market', i15m_frame, i5m_frame, condition,
                                                  fiat_currency, crypto_currency)
                                elif mode == 'consulting' or mode == 'zero':
                                    limit_manager(mode, i15m_frame, i5m_frame, condition)
                            elif buy_flag_15m is not True:
                                log = '{} 15 min momentum is not strong. Wait 5 minutes.' \
                                    .format(time_stamp(time.time()))
                                logging.info(log)
                                time.sleep(i5m_frame.candle)
                        elif trend_1h is not True:
                            log = '{} 1hour trend is {}. No buying opportunity. Wait 5 minutes.' \
                                .format(time_stamp(time.time()), trend_1h)
                            logging.info(log)
                            time.sleep(i5m_frame.candle)
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
                        order_manager('limit', i1h_frame, i15m_frame, condition, fiat_currency, crypto_currency)
                    elif mode == 'consulting' or mode == 'zero':
                        limit_manager(mode, i1h_frame, i15m_frame, condition)
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
                                order_manager('market', i15m_frame, i5m_frame, condition,
                                              fiat_currency, crypto_currency)
                            elif mode == 'consulting' or mode == 'zero':
                                limit_manager(mode, i15m_frame, i5m_frame, condition)
                        elif buy_flag_15m is not True:
                            log = '{} 15min momentum is not strong. Wait 5 minutes.'.format(time_stamp(time.time()))
                            logging.info(log)
                            time.sleep(i5m_frame.candle)
                    elif trend_1h is not True:
                        log = '1hour trend is {}. {} No buying opportunity. Wait 5 minutes.' \
                            .format(time_stamp(time.time()), trend_1h)
                        logging.info(log)
                        time.sleep(i5m_frame.candle)
            elif trend_1h:
                log = '{} 1hour trend is {}.'.format(time_stamp(time.time()), trend_1h)
                logging.info(log)
                log = '{} mid15 min frame buy flag is {}. mid15 min frame sell flag is {}.' \
                    .format(time_stamp(time.time()), buy_flag_15m, sell_flag_15m)
                logging.info(log)
                if buy_flag_15m:
                    log = '{} 15min momentum is strong.'.format(time_stamp(time.time()))
                    logging.info(log)
                    if mode == 'trading':
                        order_manager('market', i15m_frame, i5m_frame, condition, fiat_currency, crypto_currency)
                    elif mode == 'consulting' or mode == 'zero':
                        limit_manager(mode, i15m_frame, i5m_frame, condition)
                elif buy_flag_15m is not True:
                    log = '{} 15min momentum is not strong. Wait 5 minutes.'.format(time_stamp(time.time()))
                    logging.info(log)
                    time.sleep(i5m_frame.candle)
            else:
                log = '{} All high frames trends are negative. No buying opportunity. Wait 5 minutes.' \
                    .format(time_stamp(time.time()))
                logging.info(log)
                time.sleep(i5m_frame.candle)
        elif condition == 'sell':
            if i5m_frame.get_frame().iloc[-1]['close'] < pillow:  # pillow
                log = '{} Warning. Pillow activated. Sell your asset.'.format(time_stamp(time.time()))
                logging.info(log)
                if mode == 'trading':
                    order_manager('market', i15m_frame, i5m_frame, condition, fiat_currency, crypto_currency)
                elif mode == 'consulting' or mode == 'zero':
                    limit_manager(mode, i15m_frame, i5m_frame, condition)
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
                        order_manager('market', i4h_frame, i1h_frame, condition, fiat_currency, crypto_currency)
                    elif mode == 'consulting' or mode == 'zero':
                        limit_manager(mode, i4h_frame, i1h_frame, condition)
                elif sell_flag_4h is not True:
                    log = '{} 4hour momentum is not weak. Wait {} minutes.' \
                        .format(time_stamp(time.time()), i4h_frame.interval / 12)
                    logging.info(log)
                    time.sleep(i4h_frame.candle / 12)
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
                        order_manager('market', i1h_frame, i15m_frame, condition, fiat_currency, crypto_currency)
                    elif mode == 'consulting' or mode == 'zero':
                        limit_manager(mode, i1h_frame, i15m_frame, condition)
                elif sell_flag_1h is not True:
                    log = '1hour momentum is not weak. Wait {} minutes.'.format(i1h_frame.interval / 12)
                    logging.info(log)
                    time.sleep(i1h_frame.candle / 12)
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
                        order_manager('market', i15m_frame, i5m_frame, condition, fiat_currency, crypto_currency)
                    elif mode == 'consulting' or mode == 'zero':
                        limit_manager(mode, i15m_frame, i5m_frame, condition)
                elif sell_flag_15m is not True:
                    log = '{} 15min momentum not weak. Wait {} minutes.' \
                        .format(time_stamp(time.time()), i15m_frame.interval / 12)
                    logging.info(log)
                    time.sleep(i15m_frame.candle / 12)
            else:
                log = '{} All high frames trends are negative.' \
                    .format(time_stamp(time.time()))
                logging.info(log)
                if mode == 'trading':
                    order_manager('market', i15m_frame, i5m_frame, condition, fiat_currency, crypto_currency)
                elif mode == 'consulting' or mode == 'zero':
                    log = 'Please sell your asset.'
                    logging.info(log)
                    limit_manager(mode, i15m_frame, i5m_frame, condition)
                    time.sleep(10)


def data_feed():
    return {'log': log,
            'condition': condition,
            'crypto_balance': crypto_balance,
            'fiat_balance': fiat_balance,
            'price': closing_price,
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
