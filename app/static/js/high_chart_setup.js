//newData = []
highFrame = 'High frame'

var intervalID = setInterval(update_values, 1000);

function update_values() {
    $.getJSON($SCRIPT_ROOT + '/update',

        function(data_update) {
             newData = data_update.high_chart_data
             highFrame = data_update.runningHighFrame
             console.log(newData)
             return newData
        }
    );
};


// setup
const data = {
    datasets: [{
        label: highFrame,
        data: update_values()
    }]
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

//function destroy(){
//    myChart.destroy();
//};
//function render(){
//    myChart.render(
//    myChart = new Chart(
//    document.getElementById('HighFrame'),
//    config
//    );
//};
//});