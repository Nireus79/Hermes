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
                $('#high_ema13').text('EMA13: '+data.high_ema13);
                $('#high_ema30').text('EMA30: '+data.high_ema30);
                $('#high_macd').text('MACD: '+data.high_macd);
                $('#mid_d').text('Stochastic %D: '+data.mid_d);
                $('#mid_ds').text('Stochastic %DS: '+data.mid_ds);
                $('#mid_rs').text('RSI: '+data.mid_rs);
                $('#mid_tr').text('%ATR: '+data.mid_p_atr);
//                console.log(data)
        });
};