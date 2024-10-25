let selected_files_details = 0;

$('#example-multiple-optgroups').multiselect({
    enableClickableOptGroups: false,
    enableCollapsibleOptGroups: true,
    disableIfEmpty: true,
    maxHeight: 200,
    inheritClass: true,
    numberDisplayed: 3,
    delimiterText: '; ',
    widthSynchronizationMode: 'ifPopupIsSmaller',
    onChange: function (option, checked) {
        let current_selected_file_name = $(option).val()
        if (checked) {
            selected_files_details=current_selected_file_name
        }
    },
    onDropdownHidden: function (event) {
        if (selected_files_details != 0) {
            let loadIndex = layer.load(0, {shade: false});
            let selectedFilesString = selected_files_details;
            let encodedSelectedFiles = encodeURIComponent(selectedFilesString);
            // window.location.href = '/temperature/details_data?fileId=' + encodedSelectedFiles;
            // 发送 AJAX 请求获取数据
            fetch('/temperature/details_data?fileId='+ encodedSelectedFiles)
                .then(response => response.json())
                .then(data => {
                    layer.close(loadIndex);
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
                    layer.close(loadIndex);
                    console.error('Error fetching data:', error);
                });
        }
    }
});


