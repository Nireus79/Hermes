// setup
const data = {
    datasets: [{
        label: 'High Frame',
        data: []
    }],
};
// config
const config = {
    type: 'candlestick',
    data,
    options: {}
};
// init block
const myChart = new Chart(
    document.getElementById('HighFrame'),
    config
);

var intervalID = setInterval(update_values, 1000);

function update_values() {
    $.getJSON($SCRIPT_ROOT + '/update',

        function(data_update) {
             newData = JSON.parse(data_update.high_chart_data);
             highFrame = data_update.runningHighFrame;
             console.log(newData)
             console.log(highFrame)
             myChart.data.datasets[0].label = 'High frame: '+highFrame;
             myChart.data.datasets[0].data = newData;
             myChart.update();
        }
    );
};
