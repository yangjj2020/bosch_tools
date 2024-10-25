let chipChart11 = echarts.init(document.getElementById('chip_temperature11'), null, {
    renderer: 'canvas',
    useDirtyRect: false
});

// 初始化图表
let initialData = {
    legend: [],
    series: []
};

let c_tooltip = {
    showDelay: 0,
    formatter: function (params) {
        if (params.value.length > 1) {
            return (
                params.seriesName +
                ' :<br/>' +
                params.value[0] +
                '°C ' +
                params.value[1] +
                '°C '
            );
        } else {
            return (
                params.seriesName +
                ' :<br/>' +
                params.name +
                ' : ' +
                params.value +
                '°C '
            );
        }
    },
    axisPointer: {
        show: true,
        type: 'cross',
        lineStyle: {
            type: 'dashed',
            width: 1
        }
    }
}
let c_toolbox = {
    feature: {
        dataZoom: {}
        ,
        brush: {
            type: ['rect', 'polygon', 'clear']
        }
        ,
        restore: {}
    }
}
let c_grid = {
    left: '10%',
    right: '32%',
    bottom: '3%',
    top: 80,
    containLabel: true
}
let c_xAxis = {
    type: 'value',
    scale: true,
    name: 'TECU_T',
    axisLabel: {
        formatter: '{value}°C'
    },
    splitLine: {
        show: false
    }
}
let c_yAxis = {
    type: 'value',
    scale: true,
    splitNumber: 5,
    name: 'Temperature',
    axisLabel: {
        formatter: '{value}°C'
    }
}
let chipOption11 = {
    title: {
        text: 'Correlation between chips and TECU_T',
        left: '30%',
        right: '50%'
    },
    tooltip: c_tooltip,
    toolbox: c_toolbox,
    brush: {},
    legend: {
        type: 'scroll',
        orient: 'vertical',
        right: 40,
        top: 30,
        bottom: 5,
        show: true,
        width: 100,
        formatter: function (name) {
            return echarts.format.truncateText(name, 200, '14px Microsoft Yahei', '…');
        },
        tooltip: {
            show: true
        },
        data: [] //初始化图例为空
    },
    grid: c_grid,
    xAxis: c_xAxis,
    yAxis: c_yAxis,
    series: [] // 初始化图表数据为空
};

chipChart11.setOption(chipOption11);

// 发送 AJAX 请求获取数据
fetch('/temperature/details_data')
    .then(response => response.json())
    .then(data => {
        // 更新初始数据
        initialData = {
            legend: data.temperature_time_legend,
            series: data.temperature_time
        };

        chipChart11.setOption({
            legend: {
                data: data.temperature_time_legend
            },
            series: data.temperature_time
        });
    })
    .catch(error => {
        console.error('Error fetching data:', error);
    });
// 自定义恢复功能
chipChart11.on('restore', function () {
    chipChart11.setOption({
        legend: {
            data: initialData.legend
        },
        series: initialData.series
    });
});

