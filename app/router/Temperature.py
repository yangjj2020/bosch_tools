__coding__ = "utf-8"

import logging
import os
import time

from asammdf import MDF
from asammdf.blocks.utils import MdfException
from flask import request, render_template, jsonify

from app import db_pool, env_input_path, env_output_path
from app.dao.DBOperator import query_table, delete_from_tables, insert_data
from app.router import temperature_bp
from app.services.chips.temperature_work_time import str_to_list, temperature_duration, relative_difference
from app.services.chips.temperature_work_time import temperature_chip, create_data_structure
from app.utils.FileUtils import get_filename_without_extension, extract_prefix
from app.utils.HtmlGenerator import generate_select_options

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


def monitor_pool_status(interval=10):
    """
    定期监控连接池状态
    :param interval: 监控间隔时间（秒）
    """
    while True:
        status = db_pool.get_pool_status()
        logging.info("Database pool status: %s", status)
        time.sleep(interval)


'''
测量文件列表
'''


@temperature_bp.route('/list', methods=['GET'])
def temperature_list():
    try:
        measurement_file_list = get_measurement_file_list()
    except Exception as e:
        logging.error(f'查询异常:{e}')
        return render_template('error.html', failure_msg=f'{e}')
    return render_template('/page/chip/uploader.html', measurement_file_list=measurement_file_list)


@temperature_bp.route('/upload', methods=['POST'])
def upload():
    # client_ip = getClientIp()

    file = request.files['file']
    chunk_index = int(request.form.get('chunk', 0))
    total_chunks = int(request.form.get('chunks', 1))
    file_name = request.form.get('name')

    input_path = env_input_path
    test_team = request.form.get('test_team')
    input_path = os.path.join(input_path, test_team)
    # input_path = os.path.join(input_path, client_ip)
    if not os.path.exists(input_path):
        os.makedirs(input_path, exist_ok=True)

    save_file = ''
    msg = ''
    try:
        temp_file_path = os.path.join(input_path, f'{file_name}.part{chunk_index}')
        file.save(temp_file_path)  # 存储分片

        if chunk_index == total_chunks - 1:
            save_file = merge(file_name, total_chunks)  # 分片合并
    except Exception as e:
        msg = f'{e}'
        logging.error(f'file saved err:{msg}')

    return {'status': 'success', 'save_file': save_file, 'msg': msg}


def merge(file_name, total_chunks) -> str:
    # client_ip = getClientIp()

    save_path = env_input_path
    test_team = request.form.get('test_team')
    save_path = os.path.join(save_path, test_team)
    # save_path = os.path.join(save_path, client_ip)

    if not os.path.exists(save_path):
        os.makedirs(save_path, exist_ok=True)

    save_file = os.path.join(save_path, file_name)
    temp_files = [os.path.join(save_path, f'{file_name}.part{i}') for i in range(total_chunks)]
    with open(save_file, 'wb') as outfile:
        for temp_file in temp_files:
            with open(temp_file, 'rb') as infile:
                outfile.write(infile.read())
            os.remove(temp_file)
    return save_file


'''
测量文件数据入库
'''


@temperature_bp.route('/trans_csv', methods=['POST'])
def trans_csv():
    data = request.get_json()
    measure_file_path = data['save_file']
    test_team = data['test_team']
    logging.info(f"measure_file_path:{measure_file_path},test_team:{test_team}")

    mdf = MDF(measure_file_path)
    selected_columns = ['DC1_Th1', 'DC1_Th2', 'DC1_Th3', 'DC1_Th4', 'DC1_Th5', 'DC1_Th6', 'DC1_Th7',
                        'DC1_Th8', 'TC1_Th1', 'TC1_Th2', 'TC1_Th3', 'TC1_Th4', 'TC1_Th5', 'TC1_Th6',
                        'TC1_Th7', 'TC1_Th8', 'TC1_Th9', 'TC1_Th10', 'TC1_Th11', 'TC1_Th12', 'TC1_Th13',
                        'TC1_Th14', 'TC1_Th15', 'TC1_Th16', 'TC2_Th1', 'TC2_Th2', 'TC2_Th3', 'TC2_Th4',
                        'TC2_Th5', 'TC2_Th6', 'TC2_Th7', 'TC2_Th8', 'TC2_Th9', 'TC2_Th10', 'TC2_Th11',
                        'TC2_Th12', 'TC2_Th13', 'EnvT_t']
    # 检查并添加 TECU_tRaw 或 TECU_t 列
    if 'TECU_tRaw' in mdf:
        selected_columns.append('TECU_tRaw')
        alias_column = 'TECU_tRaw'
    elif 'TECU_t' in mdf:
        selected_columns.append('TECU_t')
        alias_column = 'TECU_t'
    else:
        alias_column = None

    # 过滤掉不存在的列
    existing_columns = [col for col in selected_columns if col in mdf.channels_db]
    try:
        df = mdf.to_dataframe(channels=existing_columns)
    except MdfException as e:
        logging.error(f"Error converting to DataFrame: {e}")
        return jsonify({'generate_report_failed': {e}})

    # TECU_tRaw\ETKC:1
    column_names = df.columns.tolist()
    alias_column_names = {item: item.split('\\')[0] for item in column_names}
    df.rename(columns=alias_column_names, inplace=True)

    # 如果存在 TECU_tRaw 或 TECU_t 列，为其起别名
    if alias_column is not None:
        df.rename(columns={alias_column: 'TECU_t'}, inplace=True)

    # 去除连续的重复行
    # 首先对 DataFrame 进行排序，确保按时间顺序排列
    df.sort_values(by='timestamps', inplace=True)
    logging.info(f"排序:{len(df)}")

    # 使用 keep='first' 选项保留第一次出现的非重复行
    df.drop_duplicates(keep='first', inplace=True)
    logging.info(f"删除重复项:{len(df)}")

    df.reset_index(inplace=True)
    logging.info(f"重置索引:{len(df)}")

    output_path = env_output_path
    output_path = os.path.join(output_path, test_team)
    # output_path = os.path.join(output_path, getClientIp())
    output_file = os.path.join(output_path, get_filename_without_extension(measure_file_path) + ".csv")
    os.makedirs(output_path, exist_ok=True)

    with open(output_file, 'w', newline='') as f:
        df.to_csv(f, index=True)

    logging.info(f"saved file:{output_file}")

    # 保存测量文件元信息
    ret_msg, last_id = insert_data(db_pool, table_name='measurement_file',
                                   params={"file_name": extract_prefix(measure_file_path)})
    if ret_msg != 'success':
        return jsonify({'generate_report_failed': ret_msg})
    logging.info(f"文件元信息索引:{last_id}")

    return jsonify({'generate_report_failed': ''})


'''
数据详情
'''


@temperature_bp.route('/details_page', methods=['GET'])
def temperature_details_page():
    measurement_file_list = get_measurement_file_list()
    # 下拉复选框
    multi_select_html = generate_select_options(measurement_files=measurement_file_list, multiple="")

    # 渲染页面
    return render_template('page/chip/details.html',
                           multi_select_html=multi_select_html)


@temperature_bp.route('/details_data', methods=['GET'])
def temperature_details_data():
    selected_file_names, measurement_file_list, selected_file_ids = get_selected_file_names()
    logging.info(f"file_names:{selected_file_names}")

    selected_columns_dc1_str: str = 'DC1_Th1,DC1_Th2,DC1_Th3,DC1_Th4,DC1_Th5,DC1_Th6,DC1_Th7,DC1_Th8'
    selected_columns_tc1_str: str = "TC1_Th1,TC1_Th2,TC1_Th3,TC1_Th4,TC1_Th5,TC1_Th6,TC1_Th7,TC1_Th8,TC1_Th9,TC1_Th10,TC1_Th11,TC1_Th12,TC1_Th13,TC1_Th14,TC1_Th15,TC1_Th16"
    selected_columns_tc2_str: str = "TC2_Th1,TC2_Th2,TC2_Th3,TC2_Th4,TC2_Th5,TC2_Th6,TC2_Th7,TC2_Th8,TC2_Th9,TC2_Th10,TC2_Th11,TC2_Th12,TC2_Th13"
    selected_columns_ett_str: str = "EnvT_t,TECU_t"
    selected_columns: str = f"{selected_columns_dc1_str},{selected_columns_tc1_str},{selected_columns_tc2_str},{selected_columns_ett_str}"
    temperature_time_dc1 = temperature_chip(selected_columns=selected_columns, csv_path=selected_file_names[0])

    temperature_time_legend: list = str_to_list(selected_columns)
    data_structure_dc1 = create_data_structure(temperature_time_dc1, temperature_time_legend, num_processes=2)

    # 渲染页面
    return {"temperature_time_legend": temperature_time_legend, "temperature_time": data_structure_dc1}


'''
数据概述
'''


def get_selected_file_names():
    selected_file_ids = []
    selected_file_names = []

    measurement_file_list = get_measurement_file_list()
    logging.debug(f"query result:{measurement_file_list}")

    # 请求报文中获取参数fileId
    fileId = request.args.get('fileId')
    if fileId:
        selected_file_ids = [int(id) for id in fileId.split(',')]
        selected_files = [file for file in measurement_file_list if file['id'] in selected_file_ids]
        selected_file_names = [os.path.join(env_output_path, 'HTM', file['file_name'] + ".csv") for file in
                               selected_files]
    else:
        selected_file_ids.append(measurement_file_list[0].get('id'))
        file_path = os.path.join(env_output_path, 'HTM', measurement_file_list[0].get('file_name') + ".csv")
        selected_file_names.append(file_path)
    return selected_file_names, measurement_file_list, selected_file_ids


@temperature_bp.route('/overview_relative', methods=['GET'])
def temperature_relative():
    selected_file_names, measurement_file_list, selected_file_ids = get_selected_file_names()
    # 温度阈值 和 相对温差
    chip_dict_list = relative_difference(selected_file_names=selected_file_names, max_workers=len(selected_file_names))
    chip_names = [chip['chip_name'] for chip in chip_dict_list]
    max_allowed_values = [chip['max_allowed_value'] for chip in chip_dict_list]
    max_temperature = [chip['max_temperature'] for chip in chip_dict_list]
    relative_difference_temperature = [-chip['relative_difference_temperature'] for chip in chip_dict_list]

    temperature_relative = {"chip_names": chip_names,
                            "max_allowed_values": max_allowed_values,
                            "max_temperature": max_temperature,
                            "relative_difference_temperature": relative_difference_temperature}
    return temperature_relative


@temperature_bp.route('/overview', methods=['GET'])
def temperature_overview():
    selected_file_names, measurement_file_list, selected_file_ids = get_selected_file_names()
    logging.info(f"file_names:{selected_file_names}")
    logging.info(f"file_names:{selected_file_names}")

    ## TECU_t温度时长的柱形图和饼状图
    time_diffs, total_minutes = temperature_duration(selected_file_names=selected_file_names,
                                                     max_workers=len(selected_file_names))
    # 使用排序函数
    sorted_data = dict(sorted(time_diffs.items(), key=lambda item: float(item[0].split(' ~ ')[0])))
    # 创建转换后的数据结构，并添加索引
    time_diffs = [
        {**{key: value}, 'idx': idx}
        for idx, (key, value) in enumerate(sorted_data.items())
    ]

    # 下拉多选框
    multi_select_html = generate_select_options(measurement_files=measurement_file_list, multiple="multiple")

    # 将列表中的整数转换为字符串，并用逗号连接
    selected_file_ids_str = ','.join(map(str, selected_file_ids))
    # 渲染页面
    return render_template('page/chip/overview.html',
                           total_minutes=total_minutes,
                           time_diffs=time_diffs,
                           init_selected_files=selected_file_ids_str,
                           multi_select_html=multi_select_html)


@temperature_bp.route('/delete_file', methods=['POST'])
def delete_file():
    data = request.get_json()
    file_id = data.get('id')

    try:
        # 调用数据库模块删除文件
        primary_table_name = 'measurement_file'
        primary_param: map = {'id': file_id}

        result, message = delete_from_tables(db_pool, table=primary_table_name,
                                             param=primary_param)
        if result:
            second_table_name = 'chip_temperature'
            second_param: map = {'file_id': file_id}
            result, message = delete_from_tables(db_pool, table=second_table_name,
                                                 param=second_param)
            if result:
                return jsonify({'success': True, 'message': '文件删除成功'})
            else:
                return jsonify({'success': False, 'message': '文件删除失败'})
        else:
            return jsonify({'success': False, 'message': '文件删除失败'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


'''
获取已上传全部文件元数据
'''


def get_measurement_file_list():
    query_sql = 'SELECT file_name, id FROM measurement_file WHERE status = %s ORDER BY id DESC'
    params = (0,)
    measurement_file_list = query_table(db_pool, query=query_sql, params=params)
    return measurement_file_list


# 定义排序依据
def get_key(item):
    start_time: str = item.split('~')[0]  # 分割时间区间，获取起始时间
    start_time: str = start_time.strip()
    return int(start_time)  # 转换为整数以便排序
