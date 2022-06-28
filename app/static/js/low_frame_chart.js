var options = {
          series: [
          {
          name: 'Correction frame: ',
          type: 'candlestick',
          data: []
        },{
          name: 'Reward level: ',
          type: 'line',
          data: []
        },
        {
          name: 'Buy limit: ',
          type: 'line',
          data: []
        },{
          name: 'Stop loss: ',
          type: 'line',
          data: []
          },{
          name: 'Risk level: ',
          type: 'line',
          data: []
          }
        ],
        chart: {
          height: 230,
          type: 'line',
          stacked: false
        },
        title: {
          text: 'Trend frame',
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

var low_frame_chart = new ApexCharts(document.querySelector("#low_frame_chart"), options);

low_frame_chart.render();

var intervalID = setInterval(update_values, 1000);

function update_values() {
    $.getJSON($SCRIPT_ROOT + '/update',
        function(data_update) {
            low_frame_chart.updateSeries([{
              name: 'Correction frame: ' + data_update.runningLowFrame,
              data: data_update.low_chart_data
            }
//            ,{
//              name: 'Reward level: ' + data_update.low_reward[data_update.low_reward.length - 1]['y'],
//              data: data_update.low_reward
//            },
//            {
//              name: 'Buy limit: ' + data_update.low_buy_limit[data_update.low_buy_limit.length - 1]['y'],
//              data: data_update.low_buy_limit
//            },{
//              name: 'Stop loss: ' + data_update.low_stop_loss[data_update.low_stop_loss.length - 1]['y'],
//              data: data_update.low_stop_loss
//              },{
//              name: 'Risk level: ' + data_update.low_risk_level[data_update.low_risk_level.length - 1]['y'],
//              data: data_update.low_risk_level
//              }
            ]);
        }
    );
};