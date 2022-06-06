var options = {
  chart: {
    height: 300,
    type: "line",
    stacked: false
  },
  title: {
          text: 'Momentum frame',
          align: 'left'
        },
  dataLabels: {
    enabled: false
  },
  series: [
    {
      name: "Stochastic %D: ",
      data: []
    },
    {
      name: "Stochastic %DS: ",
      data: []
    },
    {
      name: "RSI: ",
      data: []
    },
    {
      name: "%ATR: ",
      data: []
    }
  ],
  stroke: {
    width: [4, 4]
  },
  plotOptions: {
    bar: {
      columnWidth: "20%"
    }
  },
  xaxis: {
     type: 'datetime'
  },
  yaxis: [
    {
      show: true,
      axisTicks: {
        show: true
      },
      axisBorder: {
        show: true
      },
      labels: {
      },
      title: {
        text: "Stoch %D-%DS, RSI",
      }
    },{
      show: false,
      axisTicks: {
        show: false
      },
      axisBorder: {
        show: false
      },
      labels: {

      },
      title: {
        text: "Stochastic %DS: ",

      }
    },{
      show: false,
      axisTicks: {
        show: false
      },
      axisBorder: {
        show: false
      },
      labels: {
      },
      title: {
        text: "RSI: ",

      }
    },
    {
      opposite: true,
      show: true,
      axisTicks: {
        show: true
      },
      axisBorder: {
        show: true
      },
      labels: {
      },
      title: {
        text: "%ATR",
      }
    }
  ],
  tooltip: {
    shared: false,
    intersect: true,
    x: {
      show: false
    }
  },
  legend: {
    horizontalAlign: "left",
    offsetX: 40
  }
};

var mid_line_chart = new ApexCharts(document.querySelector("#mid_frame_chart"), options);

mid_line_chart.render();

//var intervalID = setInterval(update_values, 1000);
//
//function update_values() {
//    $.getJSON($SCRIPT_ROOT + '/update',
//        function(data_update) {
//            mid_line_chart.updateSeries([{
//              name: 'Stochastic %D: ' + data_update.mid_d[data_update.mid_d.length - 1]['y'],
//              data: data_update.mid_d
//            },{
//              name: 'Stochastic %DS: ' + data_update.mid_ds[data_update.mid_ds.length - 1]['y'],
//              data: data_update.mid_ds
//            },{
//              name: 'RSI: ' + data_update.mid_ds[data_update.mid_rs.length - 1],
//              data: data_update.mid_rs
//            },{
//              name: '%ATR: ' + data_update.mid_ds[data_update.mid_p_atr.length - 1],
//              data: data_update.mid_p_atr
//            }
//            ]);
//        }
//    );
//};