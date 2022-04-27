import time
import threading
from app.back.bot import elderbot, data_feed, signal_handler
from app.back.kraken import cancel_order
from app import app
from flask import render_template, request, jsonify
from app.back.kraken import time_stamp
import logging

# Default values given as preset
asset_a = None
asset_b = None
mode = None
divider = 4
rsi = 70
volatility = 0.5

# Flask logs
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)


@app.route('/')
@app.route('/home')
def main():
    return render_template('overview.html')


@app.route('/control', methods=['POST', 'GET'])
def control():
    global asset_a, asset_b, mode, divider, rsi, volatility
    if request.method == 'POST':
        asset_a = request.form['assetA']
        asset_b = request.form['assetB']
        mode = request.form['mode']
        divider = float(request.form['divider'])
        rsi = float(request.form['rsi'])
        volatility = float(request.form['volatility'])
    return render_template('control.html')


@app.route('/manual')
def doc():
    return render_template('doc.html')


@app.route('/history')
def history():
    return render_template('history.html')


@app.route('/update', methods=['GET'])
def update():
    dt = data_feed()
    dt['current_time'] = time_stamp(time.time())
    dt['crypto_currency'] = asset_a
    dt['fiat_currency'] = asset_b
    dt['mode'] = mode
    dt['divider'] = divider
    dt['rsi'] = rsi
    dt['volatility'] = volatility
    return jsonify(dt)


@app.route('/start')
def starter():
    if mode is None:
        logging.info('Mode not set.')
        return render_template('control.html')
    elif asset_a is None or asset_b is None:
        logging.info('Set assets.')
        return render_template('control.html')
    elif divider is None:
        logging.info('Set low frame evaluations.')
        return render_template('control.html')
    elif rsi is None:
        logging.info('Set rsi.')
        return render_template('control.html')
    elif volatility is None:
        logging.info('Set %atr.')
        return render_template('control.html')
    else:
        trading = threading.Thread(target=elderbot, args=(mode, asset_a, asset_b, 50, divider, rsi, volatility))
        trading.daemon = True
        trading.start()
        return render_template('overview.html')


@app.route('/stop')
def stopper():
    signal_handler()
    return render_template('overview.html')


@app.route('/cancel')
def canceler():
    cancel_order()
    return render_template('overview.html')
