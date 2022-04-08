import time
import threading
from app.back.bot import elderbot, data_feed, signal_handler
from app.back.kraken import cancel_order
from app import app
from flask import render_template, request, jsonify
from app.back.kraken import time_stamp

asset_a = None
asset_b = None


@app.route('/')
@app.route('/home')
def main():
    return render_template('overview.html')


@app.route('/control', methods=['POST', 'GET'])
def control():
    global asset_a, asset_b
    if request.method == 'POST':
        asset_a = request.form['assetA']
        asset_b = request.form['assetB']
    return render_template('control.html')


@app.route('/manual')
def doc():
    return render_template('doc.html')


@app.route('/update', methods=['GET'])
def update():
    dt = data_feed()
    dt['current_time'] = time_stamp(time.time())
    dt['crypto_currency'] = asset_a
    dt['fiat_currency'] = asset_b
    return jsonify(dt)


@app.route('/zero_start')
def zero_starter():
    consulting = threading.Thread(target=elderbot, args=('zero', asset_a, asset_b, 50))
    consulting.daemon = True
    consulting.start()
    return render_template('overview.html')


@app.route('/consulting_start')
def consulting_starter():
    consulting = threading.Thread(target=elderbot, args=('consulting', asset_a, asset_b, 50))
    consulting.daemon = True
    consulting.start()
    return render_template('overview.html')


@app.route('/trading_start')
def trading_starter():
    trading = threading.Thread(target=elderbot, args=('trading', asset_a, asset_b, 50))
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
