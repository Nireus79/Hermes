var options = {
          series: [{
          name: 'line',
          type: 'line',
          data: []
        }, {
          name: 'candle',
          type: 'candlestick',
          data: []
        }],
          chart: {
          height: 300,
          type: 'line',
        },
        title: {
          text: 'Middle frame',
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

var mid_frame_chart = new ApexCharts(document.querySelector("#mid_frame_chart"), options);
mid_frame_chart.render();