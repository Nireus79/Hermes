var options = {
          series: [
          {
          name: 'candlestick',
          type: 'candlestick',
          data: []
        },{
          name: 'EMA13',
          type: 'line',
          data: []
        },{
          name: 'EMA30',
          type: 'line',
          data: []
        },{
          name: 'MACD',
          type: 'line',
          data: []
        }
        ],
          chart: {
          height: 300,
          type: 'line',
        },
        title: {
          text: 'High frame',
          align: 'left'
        },
        stroke: {
          width: [3, 1]
        },
        tooltip: {
          shared: true,
          custom: [function({seriesIndex, dataPointIndex, w}) {
            return w.globals.series[seriesIndex][dataPointIndex]
          }, function({ seriesIndex, dataPointIndex, w }) {
            var o = w.globals.seriesCandleO[seriesIndex][dataPointIndex]
            var h = w.globals.seriesCandleH[seriesIndex][dataPointIndex]
            var l = w.globals.seriesCandleL[seriesIndex][dataPointIndex]
            var c = w.globals.seriesCandleC[seriesIndex][dataPointIndex]
            return (
              ''
            )
          }]
        },
        xaxis: {
          type: 'datetime'
        }
        };

var high_frame_chart = new ApexCharts(document.querySelector("#high_frame_chart"), options);

high_frame_chart.render();

var intervalID = setInterval(update_values, 1000);

function update_values() {
    $.getJSON($SCRIPT_ROOT + '/update',
        function(data_update) {

//           console.log(data_update.high_chart_data)
//           console.log(data_update.high_ema13)
//           console.log(data_update.high_ema30)
//           console.log(data_update.high_macd)
            high_frame_chart.updateSeries([{
              name: 'candlestick',
              data: data_update.high_chart_data
            },{
              name: 'EMA13:',
              data: data_update.high_ema13
            },{
              name: 'EMA30:',
              data: data_update.high_ema30
            }]);
        }
    );
};
