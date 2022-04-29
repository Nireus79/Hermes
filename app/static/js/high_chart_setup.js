        // setup
//        const startingDate = luxon.DateTime.fromRFC2822('01 Aug 2021 00:00 GMT'); startingDate.valueOf()
//        const date2 = luxon.DateTime.fromRFC2822('02 Aug 2021 00:00 GMT'); date2.valueOf
        const data = {
//                          labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                          datasets: [{
                                        label: 'High frame',
                                        data: [
                                            {
                                                x: 0,
                                                o: 1,
                                                h: 1.5,
                                                l: 0.75,
                                                c: 1.25
                                            },
                                            {
                                                x: 1,
                                                o: 1.25,
                                                h: 1.5,
                                                l: 0.5,
                                                c: 0.9
                                            }
                                            ]
                                      }]
                        };

        // config
        const config = {
          type: 'candlestick',
          data,
          options: {}
        };

        // render init block
        const myChart = new Chart(
                                    document.getElementById('HighFrame'),
                                    config
                                   );