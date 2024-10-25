let initialData = {
    chip_names: [],
    max_allowed_values: [],
    max_temperature: [],
    relative_difference_temperature: []

};
let chipChart09 = echarts.init(document.getElementById('chip_temperature09'), null, {
    renderer: 'canvas',
    useDirtyRect: false
});

let chipOption09 = {
    title: {
        text: 'Temperature threshold and relative temperature difference',
        subtext: 'Relative temperature difference = (chips temperature threshold, minus the maximum measurement temperature of the chips) divided by the chips temperature threshold'
    },
    tooltip: {
        trigger: 'axis'
    },
    toolbox: {
        show: true,
        feature: {
            restore: {},
            saveAsImage: {}
        }
    },
    grid: {
        top: 90,
        bottom: 70
    },
    dataZoom: [
        {
            type: 'inside'
        },
        {
            type: 'slider'
        }
    ],
    xAxis: {
        type: 'category',
        name: 'Chip Name',
        axisPointer: {
            type: 'shadow'
        },
        data: []
    },
    yAxis: {
        name: 'Temperature',
        type: 'value'
    },
    series: [
        // 温度阈值 - 折线图
        {
            name: 'max allowed temperature',
            type: 'line',
            data: [],
            tooltip: {
                valueFormatter: function (value) {
                    return value + ' °C';
                }
            },
            label: {
                show: true,
                position: 'top',
                formatter: '{c}'
            },
            emphasis: {
                focus: 'series'
            }
        },
        // 最大温度 - 柱形图
        {
            name: 'max measurement temperature',
            type: 'bar',
            showBackground: true,
            data: [],
            label: {
                show: true,
                position: 'top',
                formatter: '{c}'
            },
            tooltip: {
                valueFormatter: function (value) {
                    return value + ' °C';
                }
            },
            emphasis: {
                focus: 'series'
            },
            stack: 'st'
        },
        // 相对温差 = (温度阈值 - 最大温度) / 温度阈值
        {
            name: 'relative difference temperature',
            type: 'bar',
            showBackground: true,
            data: [],
            label: {
                show: false,
                position: 'bottom',
                formatter: '{c}'
            },
            tooltip: {
                show: true,
                valueFormatter: function (value) {
                    return -value + ' %';
                }
            },
            emphasis: {
                focus: 'series'
            },
            stack: 'st'
        }
    ]
};

// 使用初始配置项和数据显示图表。
chipChart09.setOption(chipOption09);

let init_selected_files_str= document.getElementById("init_selected_files").value;
let encodedSelectedFiles = encodeURIComponent(init_selected_files_str);
// 发送 AJAX 请求获取数据
fetch('/temperature/overview_relative?fileId=' + encodedSelectedFiles)
    .then(response => response.json())
    .then(data => {
        initialData = {
            chip_names: data.temperature_time_legend,
            max_allowed_values: data.max_allowed_values,
            max_temperature: data.max_temperature,
            relative_difference_temperature: data.relative_difference_temperature,
        };
        const updatedOption = {
            xAxis: {
                data: initialData.chip_names // 假设服务器返回的数据中包含芯片名称列表
            },
            series: [
                {
                    name: 'max allowed temperature',
                    data: initialData.max_allowed_values
                },
                {
                    name: 'max measurement temperature',
                    data: initialData.max_temperature
                },
                {
                    name: 'relative difference temperature',
                    data: initialData.relative_difference_temperature
                }
            ]
        };
        // 更新图表
        chipChart09.setOption(updatedOption);
    })
    .catch(error => {
        console.error('Error fetching data:', error);
    });
// 自定义恢复功能
chipChart09.on('restore', function () {
    chipChart09.setOption({
        xAxis: {
            data: initialData.chip_names // 假设服务器返回的数据中包含芯片名称列表
        },
        series: [
            {
                name: 'max allowed temperature',
                data: initialData.max_allowed_values
            },
            {
                name: 'max measurement temperature',
                data: initialData.max_temperature
            },
            {
                name: 'relative difference temperature',
                data: initialData.relative_difference_temperature
            }
        ]
    });
});