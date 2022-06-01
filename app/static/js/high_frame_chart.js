var options = {
          series: [
          {
          name: 'High candlestick',
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
          height: 250,
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
              data: [
                    {
              'x': 1538778600000,
              'y': [6629.81, 6650.5, 6623.04, 6633.33]
            },
            {
              'x': 1538780400000,
              'y': [6632.01, 6643.59, 6620, 6630.11]
            },
            {
              'x': 1538782200000,
              'y': [6630.71, 6648.95, 6623.34, 6635.65]
            },
            {
              'x': 1538784000000,
              'y': [6635.65, 6651, 6629.67, 6638.24]
            },
            {
              'x': 1538785800000,
              'y': [6638.24, 6640, 6620, 6624.47]
            },
            {
              'x': 1538787600000,
              'y': [6624.53, 6636.03, 6621.68, 6624.31]
            },
            {
              x: 1538789400000,
              y: [6624.61, 6632.2, 6617, 6626.02]
            },
            {
              x: 1538791200000,
              y: [6627, 6627.62, 6584.22, 6603.02]
            },
            {
              x: 1538793000000,
              y: [6605, 6608.03, 6598.95, 6604.01]
            }
              ]

        }])

        }
    );
};
