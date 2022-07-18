import logging
import time
import threading
import winsound
from app.back.kraken import Api, high_frame_indicators, mid_frame_indicators, low_frame_indicators, time_stamp, \
    add_order, cancel_order, get_condition, high_data, mid_data, low_data
from app.back.spring import check

logging.basicConfig(level=logging.INFO)

condition = None
trend_24h = None
trend_4h = None
trend_1h = None
sell_flag_4h = None
sell_flag_1h = None
sell_flag_15m = None
crypto_balance = None
fiat_balance = 0
limit = None
stop = None
closing_price = None

buy_flag_4h = False
buy_flag_1h = False
buy_flag_15m = False
runningHighFrame = None
runningMidFrame = None
runningLowFrame = None
high_chart_data = None
mid_chart_data = None
high_ema13 = None
high_macd = None
mid_d = None
mid_ds = None
mid_rs = None
mid_p_atr = None
low_chart_data = None
low_reward = None
low_limit = None
low_stop = None
low_risk = None
log = 'Please set control parameters to start.'
logs = []
trades = []

break_event = threading.Event()


def signal_handler():
    """
    Setting exit event to allow process end
    within while loops before program stop.
    """
    break_event.set()


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


def chart_data(high_frame, mid_frame, low_frame):
    global high_chart_data, high_ema13, high_macd, mid_chart_data, mid_d, mid_ds, mid_rs, mid_p_atr, \
        low_chart_data, low_limit, low_stop
    limit_data = []
    stop_data = []
    high_candles, e13, mac = high_data(high_frame)
    mid_candles, d, ds, rs, at = mid_data(mid_frame)
    low_candles = low_data(low_frame)
    for i in low_candles:
        limit_data.append({
            'x': i['x'],
            'y': limit
        })
        stop_data.append({
            'x': i['x'],
            'y': stop
        })
    high_chart_data = high_candles
    high_ema13 = e13
    high_macd = mac
    mid_chart_data = mid_candles
    mid_d = d
    mid_ds = ds
    mid_rs = rs
    mid_p_atr = at
    low_chart_data = low_candles
    low_limit = limit_data
    low_stop = stop_data


def simple_order(order_type, price, cond, crypto_currency, fiat_currency):
    global condition, log, crypto_balance, fiat_balance
    if cond == 'buy':
        asset_vol = (fiat_balance - fiat_balance * 0.0026) / price
        # kraken max trading fee: 0.0026 * asset_vol
        log = '{} order to {} {} {} using {} {}.' \
            .format(order_type, cond, asset_vol, crypto_currency, fiat_balance, fiat_currency)
        logging.info(log)
        tx = add_order(order_type, cond, asset_vol, closing_price, crypto_currency, fiat_currency)
        log = tx
        logging.info(log)
        beeper(cond)
        log = '{} Bought {} at: {}.'.format(time_stamp(time.time()), crypto_currency, closing_price)
        trades.append(log + '<br>')
    elif cond == 'sell':
        log = '{} order to {} {} {} at {}.' \
            .format(order_type, cond, crypto_balance, crypto_currency, closing_price)
        logging.info(log)
        tx = add_order(order_type, cond, crypto_balance, closing_price, crypto_currency, fiat_currency)
        log = tx
        logging.info(log)
        beeper(cond)
        log = '{} Sold {} at: {}.'.format(time_stamp(time.time()), crypto_currency, closing_price)
        trades.append(log + '<br>')


def order_manager(order_type, high, mid, low, cond, crypto_currency, fiat_currency, time_divisor, max_rsi):
    """
    When conditions to buy or sell are aligned in higher frames (buy or sell flag True)
    order_manager is setting limit and stop loss levels.
    Then starts monitoring periodically closing price at current running low time frame duration:
        When intending to buy asset
            if closing price exceeds set limit level:
                places a market buy asset for the asset
                Conditions are reevaluated until order is closed.
                Risk level is set on the low of previous low frame candle - low frame atr as global variable.
                Buy price is stored as global variable.
                Reward level is set by choice as the single, double, triple or 100 (ignored)
                of (buy price - risk level) + buy price
            else: (closing price under limit)
                waits part or full time by choice, of low frame duration to reevaluate.
                    if new closing price is lower than limit:
                        if new higher high of low frame is higher than previous set:
                            sets new limit equal to new higher high.
                        else:
                            waits one low candle / divisor
        When intending to sell asset
            if closing price is under buy price AND over risk:
                waits one low candle / divisor
                as this zone is considered possible pullback zone of the price.
            elif closing price is over buy price AND lower than set stop-loss level:
                places market sell order for the asset.
                Conditions are reevaluated until order is closed.
            else: (closing price over stop-loss)
                waits part or full time by choice, of low frame duration to reevaluate:
                    if new closing price is higher than stop-loss:
                        if new lower low of low frame is higher than previous set:
                            sets new stop-loss equal to new lower-low.
                        else:
                            waits one low candle / divisor
    :param max_rsi: maximum rsi in mid-frame
    :param time_divisor: reevaluation of low frame
    :param order_type: limit / market
    :param crypto_currency: asset a
    :param fiat_currency: asset b
    :param high: high-frame instance
    :param mid: mid-frame instance
    :param low: low-frame instance
    :param cond: buy / sell
    In stop-loss/limit levels an extra margin of current atr (average true range) is added,
    to include the volatility factor and limit false positioning.
    After setting a buy order, safety "risk" and "reward" levels are stored as safety parameters.
    Risk level = 'low' of mid-frame candle minus low-frame atr.
    Risk = Buy price - Risk level
    Reward = Buy price + (Risk * 2) As 1/2 Risk/Reward ratio.

    WARNING!!!
    When setting market order, volume must be set on the amount of the first asset.
    When setting buy order, vol = (money - money * max kraken fee) / crypto price
    When setting sell order, vol = crypto_balance (fee is calculated by kraken)
    """
    global condition, stop, limit, log, closing_price, runningLowFrame, crypto_balance, fiat_balance
    beeper('start')
    log = '{} Order management. Setting {}min low frame {} limits.'.format(time_stamp(time.time()), low.interval, cond)
    logging.info(log)
    logs.append(log + '<br>')
    high_f = high_frame_indicators(high.get_frame())
    mid_f = mid_frame_indicators(mid.get_frame(), max_rsi)
    low_f = low_frame_indicators(low.get_frame())
    l_atr = low_f.iloc[-1]['atr']
    limit = low_f.iloc[-1]['high'] + l_atr
    stop = low_f.iloc[-1]['low'] - l_atr
    closing_price = low_f.iloc[-1]['close']
    log = 'Balance: {} {}. {} {}'.format(crypto_balance, crypto_currency, fiat_balance, fiat_currency)
    logging.info(log)
    logs.append(log + '<br>')
    log = '{} Current price: {}. limit: {}. Stop loss: {}'.format(time_stamp(time.time()), closing_price, limit, stop)
    logging.info(log)
    logs.append(log + '<br>')
    log = '{} Wait {}min.'.format(time_stamp(time.time()), low.interval)
    logging.info(log)
    logs.append(log + '<br>')
    chart_data(high_f, mid_f, low_f)
    time.sleep(low.candle)
    while True:
        high_f = high_frame_indicators(high.get_frame())
        mid_f = mid_frame_indicators(mid.get_frame(), max_rsi)
        low_f = low_frame_indicators(low.get_frame())
        buy_flag = mid_f.iloc[-1]['buy flag']
        sell_flag = mid_f.iloc[-1]['sell flag']
        l_atr = low_f.iloc[-1]['atr']
        new_limit = low_f.iloc[-1]['high'] + l_atr
        new_stop = low_f.iloc[-1]['low'] - l_atr
        closing_price = low_f.iloc[-1]['close']
        chart_data(high_f, mid_f, low_f)
        if break_event.is_set():  # thread "kill" by user
            cancel_order()
            log = '{} Break ordering.'.format(time_stamp(time.time()))
            logging.info(log)
            logs.append(log + '<br>')
            break
        elif cond == 'buy':
            if buy_flag:
                if closing_price > limit:
                    asset_vol = (fiat_balance - fiat_balance * 0.0026) / closing_price
                    # kraken max trading fee: 0.0026 * asset_vol
                    log = '{} order to {} {} {} using {} {}.' \
                        .format(order_type, cond, asset_vol, crypto_currency, fiat_balance, fiat_currency)
                    logging.info(log)
                    tx = add_order(order_type, cond, asset_vol, closing_price, crypto_currency, fiat_currency)
                    log = tx
                    logging.info(log)
                    beeper(cond)
                    log = '{} Bought {} at: {}.'.format(time_stamp(time.time()), crypto_currency, closing_price)
                    trades.append(log + '<br>')
                    stop = None
                    limit = None
                    break
                else:
                    if new_limit <= limit:
                        limit = new_limit
                        log = '{} limit set to {}. Wait {}min' \
                            .format(time_stamp(time.time()), limit, low.interval / time_divisor)
                        logging.info(log)
                        logs.append(log + '<br>')
                        time.sleep(low.candle / time_divisor)
                    else:
                        log = '{} Closing price under limit. Wait {}min.' \
                            .format(time_stamp(time.time()), low.interval / time_divisor)
                        logging.info(log)
                        logs.append(log + '<br>')
                        time.sleep(low.candle / time_divisor)
            elif buy_flag is not True:
                log = '{} Conditions re-evaluation.'.format(time_stamp(time.time()))
                logging.info(log)
                logs.append(log + '<br>')
                beeper('break')
                time.sleep(10)
                limit = None
                stop = None
                break
        elif cond == 'sell':
            if sell_flag:
                if closing_price < stop:
                    log = '{} order to {} {} {} at {}.' \
                        .format(order_type, cond, crypto_balance, crypto_currency, closing_price)
                    logging.info(log)
                    tx = add_order(order_type, cond, crypto_balance, closing_price, crypto_currency, fiat_currency)
                    log = tx
                    logging.info(log)
                    beeper(cond)
                    log = '{} Sold {} at: {}.'.format(time_stamp(time.time()), crypto_currency, closing_price)
                    trades.append(log + '<br>')
                    limit = None
                    stop = None
                    break
                else:
                    if new_stop >= stop:
                        stop = new_stop
                        log = '{} Stop loss set to {}. Wait {}min' \
                            .format(time_stamp(time.time()), stop, low.interval / time_divisor)
                        logging.info(log)
                        logs.append(log + '<br>')
                        time.sleep(low.candle / time_divisor)
                    else:
                        log = '{} Closing price over stop. Wait {}min.' \
                            .format(time_stamp(time.time()), low.interval / time_divisor)
                        logging.info(log)
                        logs.append(log + '<br>')
                        time.sleep(low.candle / time_divisor)
            elif sell_flag is not True:
                log = '{} Conditions re-evaluation.'.format(time_stamp(time.time()))
                logging.info(log)
                logs.append(log + '<br>')
                beeper('break')
                limit = None
                stop = None
                break


def limit_manager(mode, high, mid, low, cond, time_divisor, max_rsi):
    """
    Same as order_manager.
    No actual order is set.
    User is just informed for the action he has to take.
    :param max_rsi: maximum rsi in mid-frame
    :param time_divisor: reevaluation of low frame
    :param mode: zero or consulting
    :param high: The high frame instance, used for chart data.
    :param mid: The middle frame instance, used to check if buy/sell flag is still True.
    :param low: The low frame instance, used to set limit/stop-loss borders.
    :param cond: Condition sell/buy
    """
    global condition, stop, limit, log, closing_price, runningLowFrame
    beeper('start')
    log = '{} Limit management. Setting {}min low frame {} limits.'.format(time_stamp(time.time()), low.interval, cond)
    logging.info(log)
    logs.append(log + '<br>')
    high_f = high_frame_indicators(high.get_frame())
    mid_f = mid_frame_indicators(mid.get_frame(), max_rsi)
    low_f = low_frame_indicators(low.get_frame())
    l_atr = low_f.iloc[-1]['atr']
    limit = low_f.iloc[-1]['high'] + l_atr
    stop = low_f.iloc[-1]['low'] - l_atr
    closing_price = low_f.iloc[-1]['close']
    log = '{} Current price {}. limit: {}. Stop loss: {}'.format(time_stamp(time.time()), closing_price, limit, stop)
    logging.info(log)
    logs.append(log + '<br>')
    if cond == 'buy':
        log = '{} Please give buy order when price exceeds {}. Wait {}min.' \
            .format(time_stamp(time.time()), limit, low.interval)
    elif cond == 'sell':
        log = '{} Please give sell order when price under {}. Wait {}min.' \
            .format(time_stamp(time.time()), stop, low.interval)
    logging.info(log)
    logs.append(log + '<br>')
    chart_data(high_f, mid_f, low_f)
    time.sleep(low.candle)
    while True:
        high_f = high_frame_indicators(high.get_frame())
        mid_f = mid_frame_indicators(mid.get_frame(), max_rsi)
        low_f = low_frame_indicators(low.get_frame())
        buy_flag = mid_f.iloc[-1]['buy flag']
        sell_flag = mid_f.iloc[-1]['sell flag']
        l_atr = low_f.iloc[-1]['atr']
        new_limit = low_f.iloc[-1]['high'] + l_atr
        new_stop = low_f.iloc[-1]['low'] - l_atr
        closing_price = low_f.iloc[-1]['close']
        chart_data(high_f, mid_f, low_f)
        if break_event.is_set():  # thread "kill" by user
            log = '{} Operation interrupted by user.'.format(time_stamp(time.time()))
            logging.info(log)
            logs.append(log + '<br>')
            break
        if cond == 'buy':
            if buy_flag:
                if closing_price > limit:
                    log = '{} Closing price exceeded limit. Please add buy order'.format(time_stamp(time.time()))
                    logging.info(log)
                    logs.append(log + '<br>')
                    beeper(cond)
                    if mode == 'simulator':
                        logging.info('')
                        logs.append('<br>')
                        log = '{} Bought at: {}'.format(time_stamp(time.time()), closing_price)
                        logging.info(log)
                        logs.append(log + '<br>')
                        trades.append(log + '<br>')
                        condition = 'sell'
                    runningLowFrame = None
                    break
                else:
                    if new_limit < limit:
                        limit = new_limit
                        stop = new_stop
                        log = '{} New limit set to {}. Please wait {}min.' \
                            .format(time_stamp(time.time()), limit, low.interval / time_divisor)
                        logging.info(log)
                        logs.append(log + '<br>')
                        time.sleep(low.candle / time_divisor)
                    else:
                        log = '{} Closing price not exceeded limit. Please wait {}min.'.format(
                            time_stamp(time.time()), low.interval / time_divisor)
                        logging.info(log)
                        logs.append(log + '<br>')
                        time.sleep(low.candle / time_divisor)
            elif buy_flag is not True:
                log = '{} Conditions re-evaluation.'.format(time_stamp(time.time()))
                logging.info(log)
                logs.append(log + '<br>')
                beeper('break')
                limit = None
                stop = None
                break
        elif cond == 'sell':
            if sell_flag:
                if closing_price < stop:
                    log = '{} Closing price under stop loss. Please add sell order' \
                        .format(time_stamp(time.time()))
                    logging.info(log)
                    logs.append(log + '<br>')
                    beeper(cond)
                    if mode == 'simulator':
                        logging.info('')
                        logs.append('<br>')
                        log = '{} Sold at: {}'.format(time_stamp(time.time()), closing_price)
                        logging.info(log)
                        logs.append(log + '<br>')
                        trades.append(log + '<br>')
                        condition = 'buy'
                    limit = None
                    stop = None
                    break
                else:
                    if new_stop > stop:
                        limit = new_limit
                        stop = new_stop
                        log = '{} New stop-loss set to {}. Please wait {}min.' \
                            .format(time_stamp(time.time()), stop, low.interval / time_divisor)
                        logging.info(log)
                        logs.append(log + '<br>')
                        time.sleep(low.candle / time_divisor)
                    else:
                        log = '{} Closing price over stop-loss level. Please wait {}min.'.format(
                            time_stamp(time.time()), low.interval / time_divisor)
                        logging.info(log)
                        logs.append(log + '<br>')
                        time.sleep(low.candle / time_divisor)
            elif sell_flag is not True:
                log = '{} Conditions re-evaluation.'.format(time_stamp(time.time()))
                logging.info(log)
                logs.append(log + '<br>')
                beeper('break')
                limit = None
                stop = None
                break


def elderbot(mode, crypto_currency, fiat_currency, depth, time_divisor, max_rsi):
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
    In our case a preset combination of 13p, 200p EMA and macd indicators (Closing > EMA13 and macd > 0)
    is used to determine the high frame trend.
    Mid-frame.
    Trend momentum and position is detected with the use of stochastic slow indicator. Stochastic fast can be used for
    quicker response but in this case more force signals are generated. Stochastic slow is used as it is a 'smothered'
    version of stoch fast. (d > ds > 20 buy Flag / d < ds < 80 sell Flag)
    An additional indicator of strength is added (RSI) as choice for safety reasons,
    as when current price strength is above safety, price is actually 'overbought' and probability of descent is high.
    ATR detects the volatility of the price. ATR% is ATR related with the closing price.
    An extra condition of %ATR is given as choice, to avoid false buy flags in price consolidation instances.
    ATR of middle frame is also subtracted by lowest low of low-candle before buy candle,
    to be used as risk level and avoid false flag.
    Low frame.
    When conditions are aligned in the higher frames action limits are set, according to the last low frame
    closed candle range. Next time fragment of candle price gives action flag or sets new limits.
    Low frame current candle ATR is added to the limit and subtracted to stop-loss, so current volatility
    of the price is taken into consideration to avoid false transactions.

    https://en.wikipedia.org/wiki/Alexander_Elder
    elder.com
    tradingstrategyguides.com
    www.elearnmarkets.com

    Original strategy dictates to wait the whole time of each candle to set condition flag,
        but as api provides data in real time, duration is divided optionally to make bot faster.
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
            After every purchase of an asset risk and reward levels are set.
            if closing < risk or closing > reward::
                order_manager() kicks in to sell on 5min low frame.
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
                second risk condition is activated.
                order_manager() kicks in to sell on 5minute low frame.
    :param max_rsi: maximum rsi in mid-frame
    :param time_divisor: reevaluation of low frame
    :param mode: trading / consulting
    :param crypto_currency: the crypto asset to be traded
    :param fiat_currency: the fiat asset to be traded
    :param depth: the time periods back to be analysed
    risk: A safety level is set at the beginning of the process to 4% under current price.
            That is for the case of bot starts evaluating sell condition and no other
            safety level is stored.
            After every buy of asset A, a safety level is set on the lowest low of previous (from buy)
            low-frame candle minus atr.
            That is considered as minimum stop loss level price can reach on a pullback.
    """
    global condition, log, trend_24h, trend_4h, trend_1h, buy_flag_4h, buy_flag_1h, buy_flag_15m,\
        sell_flag_4h, sell_flag_1h, sell_flag_15m, \
        crypto_balance, fiat_balance, closing_price, runningHighFrame, runningMidFrame, runningLowFrame
    # TODO activate licence check
    licence = True  # check()['license_active']
    if licence:
        log = 'Your product licence is active. Thank you for using Hermes.'
        logging.info(log)
        logs.append(log + '<br>')
        if mode == 'simulator':
            condition = 'buy'
        i24h_frame = Api(crypto_currency, fiat_currency, 1440, depth)
        i4h_frame = Api(crypto_currency, fiat_currency, 240, depth)
        i1h_frame = Api(crypto_currency, fiat_currency, 60, depth)
        i15m_frame = Api(crypto_currency, fiat_currency, 15, depth)
        i5m_frame = Api(crypto_currency, fiat_currency, 5, depth)
        log = '{} Operation start. Mode is {}. Max RSI set to: {}. Low frame evaluations: {}.'\
            .format(time_stamp(time.time()), mode, max_rsi, time_divisor)
        logging.info(log)
        logs.append(log + '<br>')
        while True:
            if break_event.is_set():  # thread "kill" by user
                cancel_order()
                log = '{} Breaking operation.'.format(time_stamp(time.time()))
                logging.info(log)
                logs.append(log + '<br>')
                break
            high_frame_24h = high_frame_indicators(i24h_frame.get_frame())
            high_frame_4h = high_frame_indicators(i4h_frame.get_frame())
            high_frame_1h = high_frame_indicators(i1h_frame.get_frame())
            mid_frame_4h = mid_frame_indicators(i4h_frame.get_frame(), max_rsi)
            mid_frame_1h = mid_frame_indicators(i1h_frame.get_frame(), max_rsi)
            mid_frame_15m = mid_frame_indicators(i15m_frame.get_frame(), max_rsi)
            closing_price = high_frame_24h.iloc[-1]['close']
            trend_24h = high_frame_24h.iloc[-1]['trend']
            trend_4h = high_frame_4h.iloc[-1]['trend']
            trend_1h = high_frame_1h.iloc[-1]['trend']
            buy_flag_4h = mid_frame_4h.iloc[-1]['buy flag']
            sell_flag_4h = mid_frame_4h.iloc[-1]['sell flag']
            buy_flag_1h = mid_frame_1h.iloc[-1]['buy flag']
            sell_flag_1h = mid_frame_1h.iloc[-1]['sell flag']
            buy_flag_15m = mid_frame_15m.iloc[-1]['buy flag']
            sell_flag_15m = mid_frame_15m.iloc[-1]['sell flag']
            if mode == 'consulting' or mode == 'trading':
                condition, crypto_balance, fiat_balance = get_condition(crypto_currency, fiat_currency, closing_price)
            log = '{} Condition is {}.'.format(time_stamp(time.time()), condition)
            logging.info(log)
            logs.append(log + '<br>')
            if condition == 'buy':
                if trend_24h:
                    log = '{} 24hour trend is {}'.format(time_stamp(time.time()), trend_24h)
                    logging.info(log)
                    logs.append(log + '<br>')
                    runningHighFrame = '24Hour'
                    runningMidFrame = '4Hour'
                    runningLowFrame = '1Hour'
                    chart_data(high_frame_24h, mid_frame_4h, low_frame_indicators(i1h_frame.get_frame()))
                    if buy_flag_4h:
                        log = '{} 4hour momentum is {}.'.format(time_stamp(time.time()), buy_flag_4h)
                        logging.info(log)
                        logs.append(log + '<br>')
                        if mode == 'trading':
                            order_manager('market', i24h_frame, i4h_frame, i1h_frame, condition,
                                          crypto_currency, fiat_currency, time_divisor, max_rsi)
                        elif mode == 'consulting' or mode == 'simulator':
                            limit_manager(mode, i24h_frame, i4h_frame, i1h_frame, condition, time_divisor, max_rsi)
                    elif buy_flag_4h is not True:
                        log = '{} 4hour momentum is {}.'.format(time_stamp(time.time()), buy_flag_4h)
                        logging.info(log)
                        logs.append(log + '<br>')
                        if trend_4h:
                            logging.info('{} 4hour trend is {}.'.format(time_stamp(time.time()), trend_4h))
                            logging.info(log)
                            runningHighFrame = '4Hour'
                            runningMidFrame = '1Hour'
                            runningLowFrame = '15minutes'
                            chart_data(high_frame_4h, mid_frame_1h, low_frame_indicators(i15m_frame.get_frame()))
                            if buy_flag_1h and sell_flag_4h is not True:
                                log = '{} 1hour momentum is {}.'.format(time_stamp(time.time()), buy_flag_1h)
                                logging.info(log)
                                logs.append(log + '<br>')
                                if mode == 'trading':
                                    order_manager('market', i4h_frame, i1h_frame, i15m_frame, condition,
                                                  crypto_currency, fiat_currency, time_divisor, max_rsi)
                                elif mode == 'consulting' or mode == 'zero':
                                    limit_manager(mode, i4h_frame, i1h_frame, i15m_frame,
                                                  condition, time_divisor, max_rsi)
                            elif buy_flag_1h is not True:
                                log = '{} 1hour momentum is not {}. Wait 5 min.'\
                                    .format(time_stamp(time.time()), buy_flag_1h)
                                logging.info(log)
                                logs.append(log + '<br>')
                                time.sleep(300)
                        elif trend_4h is not True:
                            log = '{} 4hour trend is {}.'.format(time_stamp(time.time()), trend_4h)
                            logging.info(log)
                            logs.append(log + '<br>')
                            chart_data(high_frame_1h, mid_frame_15m, low_frame_indicators(i5m_frame.get_frame()))
                            if buy_flag_1h and sell_flag_4h is not True:
                                log = '{} 1hour momentum is {}.'.format(time_stamp(time.time()), buy_flag_1h)
                                logging.info(log)
                                logs.append(log + '<br>')
                                if mode == 'trading':
                                    simple_order('market', closing_price, condition, crypto_currency, fiat_currency)
                                elif mode == 'consulting' or mode == 'simulator':
                                    log = '{} Buy asset'.format(time_stamp(time.time()))
                                    logging.info(log)
                                    logs.append(log + '<br>')
                            else:
                                log = '{} No buying opportunity. Wait 5 min.'.format(time_stamp(time.time()))
                                logging.info(log)
                                logs.append(log + '<br>')
                                time.sleep(300)
                elif trend_4h:
                    log = '{} 4hour trend is {}.'.format(time_stamp(time.time()), trend_4h)
                    logging.info(log)
                    logs.append(log + '<br>')
                    log = '{} mid 1hour frame buy flag is {}. mid 1hour frame sell flag is {}.' \
                        .format(time_stamp(time.time()), buy_flag_1h, sell_flag_1h)
                    logging.info(log)
                    logs.append(log + '<br>')
                    runningHighFrame = '4Hour'
                    runningMidFrame = '1Hour'
                    runningLowFrame = '15minutes'
                    chart_data(high_frame_4h, mid_frame_1h, low_frame_indicators(i15m_frame.get_frame()))
                    if buy_flag_1h and sell_flag_4h is not True:
                        log = '{} 1hour momentum is {}.'.format(time_stamp(time.time()), buy_flag_1h)
                        logging.info(log)
                        logs.append(log + '<br>')
                        if mode == 'trading':
                            order_manager('market', i4h_frame, i1h_frame, i15m_frame, condition,
                                          crypto_currency, fiat_currency, time_divisor, max_rsi)
                        elif mode == 'consulting' or mode == 'simulator':
                            limit_manager(mode, i4h_frame, i1h_frame, i15m_frame, condition, time_divisor, max_rsi)
                    elif buy_flag_1h is not True:
                        log = '{} 1hour momentum is {}. Wait 5 min'.format(time_stamp(time.time()), buy_flag_1h)
                        logging.info(log)
                        logs.append(log + '<br>')
                        chart_data(high_frame_1h, mid_frame_15m, low_frame_indicators(i5m_frame.get_frame()))
                        logging.info(log)
                        logs.append(log + '<br>')
                        time.sleep(300)
                else:
                    if buy_flag_1h and sell_flag_4h is not True:
                        log = '{} 1hour momentum is {}.'.format(time_stamp(time.time()), buy_flag_1h)
                        logging.info(log)
                        logs.append(log + '<br>')
                        if mode == 'trading':
                            simple_order('market', closing_price, condition, crypto_currency, fiat_currency)
                        elif mode == 'consulting' or mode == 'zero':
                            limit_manager(mode, i4h_frame, i1h_frame, i15m_frame,
                                          condition, time_divisor, max_rsi)
                    elif buy_flag_1h is not True:
                        log = '{} 1hour momentum is {}. Wait 5 min.'.format(time_stamp(time.time()), buy_flag_1h)
                        logging.info(log)
                        logs.append(log + '<br>')
                        time.sleep(300)
            elif condition == 'sell':
                if trend_24h:
                    log = '{} 24hour trend is {}.'.format(time_stamp(time.time()), trend_24h)
                    logging.info(log)
                    logs.append(log + '<br>')
                    runningHighFrame = '24Hour'
                    runningMidFrame = '4Hour'
                    runningLowFrame = '1Hour'
                    chart_data(high_frame_24h, mid_frame_4h, low_frame_indicators(i5m_frame.get_frame()))
                    if sell_flag_4h:
                        log = '{} 4hour momentum is {}.'.format(time_stamp(time.time()), sell_flag_4h)
                        logging.info(log)
                        logs.append(log + '<br>')
                        if mode == 'trading':
                            order_manager('market', i24h_frame, i4h_frame, i1h_frame, condition,
                                          crypto_currency, fiat_currency, time_divisor, max_rsi)
                        elif mode == 'consulting' or mode == 'simulator':
                            limit_manager(mode, i24h_frame, i4h_frame, i1h_frame, condition, time_divisor, max_rsi)
                    elif sell_flag_4h is not True:
                        log = '{} 4hour momentum is {}. Wait {} minutes.' \
                            .format(time_stamp(time.time()), sell_flag_4h, i4h_frame.interval / 12)
                        logging.info(log)
                        logs.append(log + '<br>')
                        time.sleep(i4h_frame.candle / 12)
                elif trend_4h:
                    log = '{} 4hour trend is {}.'.format(time_stamp(time.time()), trend_4h)
                    logging.info(log)
                    logs.append(log + '<br>')
                    runningHighFrame = '4Hour'
                    runningMidFrame = '1Hour'
                    runningLowFrame = '15minutes'
                    chart_data(high_frame_4h, mid_frame_1h, low_frame_indicators(i5m_frame.get_frame()))
                    if sell_flag_1h:
                        log = '{} 1hour momentum is {}.'.format(time_stamp(time.time()), sell_flag_1h)
                        logging.info(log)
                        logs.append(log + '<br>')
                        if mode == 'trading':
                            order_manager('market', i4h_frame, i1h_frame, i15m_frame, condition,
                                          crypto_currency, fiat_currency, time_divisor, max_rsi)
                        elif mode == 'consulting' or mode == 'simulator':
                            limit_manager(mode, i4h_frame, i1h_frame, i15m_frame, condition, time_divisor, max_rsi)
                    elif sell_flag_1h is not True:
                        log = '1hour momentum is {}. Wait {} minutes.'.format(sell_flag_1h, i1h_frame.interval / 12)
                        logging.info(log)
                        logs.append(log + '<br>')
                        time.sleep(i1h_frame.candle / 12)
                else:
                    if sell_flag_1h:
                        log = '1hour momentum is {}.'.format(sell_flag_1h)
                        logging.info(log)
                        logs.append(log + '<br>')
                        if mode == 'trading':
                            simple_order('market', closing_price, condition, crypto_currency, fiat_currency)
                        elif mode == 'consulting' or mode == 'simulator':
                            log = '{} Sell asset'.format(time_stamp(time.time()))
                            logging.info(log)
                            logs.append(log + '<br>')
                    else:
                        log = '{} 1hour momentum is not {}. Wait 5 min.'.format(time_stamp(time.time()), sell_flag_1h)
                        logging.info(log)
                        logs.append(log + '<br>')
                        time.sleep(300)
    else:
        log = 'Your product licence is not active. Please activate or contact technical support.'
        logging.info(log)
        logs.append(log + '<br>')
        exit()


def data_feed():
    if len(logs) > 300:
        del logs[:len(logs) - 299]
    return {
        'log': log,
        'logs': logs,
        'trades': trades,
        'condition': condition,
        'crypto_balance': crypto_balance,
        'fiat_balance': fiat_balance,
        'runningHighFrame': runningHighFrame,
        'runningMidFrame': runningMidFrame,
        'runningLowFrame': runningLowFrame,
        'trend_24h': str(trend_24h),
        'trend_4h': str(trend_4h),
        'trend_1h': str(trend_1h),
        'buy_flag_4h': str(buy_flag_4h),
        'sell_flag_4h': str(sell_flag_4h),
        'buy_flag_1h': str(buy_flag_1h),
        'sell_flag_1h': str(sell_flag_1h),
        'buy_flag_15m': str(buy_flag_15m),
        'sell_flag_15m': str(sell_flag_15m),
        'high_chart_data': high_chart_data,
        'mid_chart_data': mid_chart_data,
        'high_ema13': high_ema13,
        'high_macd': high_macd,
        'mid_d': mid_d,
        'mid_ds': mid_ds,
        'mid_rs': mid_rs,
        'mid_p_atr': mid_p_atr,
        'low_chart_data': low_chart_data,
        'price': closing_price,
        'low_limit': low_limit,
        'low_stop': low_stop
    }
