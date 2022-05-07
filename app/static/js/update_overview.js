var intervalID = setInterval(update_values, 1000);
function update_values() {
    $.getJSON($SCRIPT_ROOT + '/update',
        function(data) {
                $('#current_time').text('Current time: '+data.current_time);
                $('#mode').text('Mode: '+data.mode);
                $('#volatility').text('Min %ATR: '+data.volatility);
                $('#rsi').text('Max RSI: '+data.rsi);
                $('#evaluations').text('Evaluations per low period: '+data.divider);
                $('#condition').text('Evaluating to '+data.condition+':');
                $('#crypto_currency').text('for '+data.fiat_currency+'.');
                $('#fiat_currency').text(''+data.crypto_currency);
                $('#crypto_balance').text('asset A: '+data.crypto_balance);
                $('#fiat_balance').text('asset B: '+data.fiat_balance);
                $('#trend_24h').text(data.trend_24h);
                $('#buy_flag_4h').text(data.buy_flag_4h);
                $('#sell_flag_4h').text(data.sell_flag_4h);
                $('#trend_4h').text(data.trend_4h);
                $('#buy_flag_1h').text(data.buy_flag_1h);
                $('#sell_flag_1h').text(data.sell_flag_1h);
                $('#trend_1h').text(data.trend_1h);
                $('#buy_flag_15m').text(data.buy_flag_15m);
                $('#sell_flag_15m').text(data.sell_flag_15m);
                $('#price').text('Closing price: '+data.price);
                $('#pillow').text('Pillow: '+data.pillow);
                $('#limit').text('Buy limit: '+data.limit);
                $('#stop').text('Stop loss: '+data.stop);
                $('#log').text('Log: '+data.log);
                ema13 = JSON.parse(data.high_ema13)
                $('#high_ema13').html('EMA13: '+ema13[ema13.length - 1]);
                ema30 = JSON.parse(data.high_ema30)
                $('#high_ema30').html('EMA30: '+ema30[ema30.length - 1]);
                macd = JSON.parse(data.high_macd)
                $('#high_macd').html('MACD: '+macd[macd.length - 1]);
                d = JSON.parse(data.mid_d)
                $('#mid_d').html('Stochastic %D: '+d[d.length - 1]);
                ds = JSON.parse(data.mid_ds)
                $('#mid_ds').html('Stochastic %DS: '+ds[ds.length - 1]);
                rsi = JSON.parse(data.mid_rs)
                $('#mid_rs').html('RSI: '+rsi[rsi.length - 1]);
                tr = JSON.parse(data.mid_p_atr)
                $('#mid_tr').html('%ATR: '+tr[tr.length - 1]);
        });
};