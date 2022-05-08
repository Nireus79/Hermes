// high candle chart setup
const high_candle_data = {
    datasets: [{
        label: 'High Frame',
        data: []
                }
    ],
};
// config
const config_high_candle_chart = {
    type: 'candlestick',
    data: high_candle_data,
    options: {}
};
// init block
const HighCandleChart = new Chart(
    document.getElementById('HighFrameCandles'),
    config_high_candle_chart
);
// mid candle chart setup
const mid_candle_data = {
    datasets: [{
        label: 'Middle Frame',
        data: []
                }
    ],
};
// config
const config_mid_candle_chart = {
    type: 'candlestick',
    data: mid_candle_data,
    options: {}
};
// init block
const MidCandleChart = new Chart(
    document.getElementById('MidFrameCandles'),
    config_mid_candle_chart
);

var intervalID = setInterval(update_values, 1000);

function update_values() {
    $.getJSON($SCRIPT_ROOT + '/update',
        function(data_update) {
             HighCandleChart.data.datasets[0].label = 'High frame: '+data_update.runningHighFrame;
             HighCandleChart.data.datasets[0].data = JSON.parse(data_update.high_chart_data);
             MidCandleChart.data.datasets[0].label = 'Middle frame: '+data_update.runningMidFrame;
             MidCandleChart.data.datasets[0].data = JSON.parse(data_update.mid_chart_data);
             HighCandleChart.update();
             MidCandleChart.update();
        }
    );
};
