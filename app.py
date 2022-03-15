import time
from flask import Flask, render_template, jsonify, request
import threading
import webbrowser
from back.bot import elder_cons, elder_trading, data_feed, signal_handler, time_stamp
from back.kraken import cancel_order

app = Flask(__name__)

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
        #

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


@app.route('/consulting_start')
def consulting_starter():
    consulting = threading.Thread(target=elder_cons, args=(asset_a, asset_b, 50))
    consulting.daemon = True
    consulting.start()
    return render_template('overview.html')


@app.route('/trading_start')
def trading_starter():
    trading = threading.Thread(target=elder_trading, args=(asset_a, asset_b, 50))
    trading.daemon = True
    # trading.start()
    return render_template('overview.html')


@app.route('/stop')
def stopper():
    signal_handler()
    return render_template('overview.html')


@app.route('/cancel')
def canceler():
    cancel_order()
    return render_template('overview.html')


if __name__ == '__main__':
    webbrowser.open_new('http://127.0.0.1:5000')
    app.run(debug=True)
