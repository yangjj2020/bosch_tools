__coding__ = "utf-8"

import logging
import multiprocessing
from typing import Dict, List

import pandas as pd
from pandas import DataFrame

from app import chipNamesConfig, db_pool
from app.dao.DBOperator import query_table, query_table_by_sql
from app.utils.MathUtils import relative_difference_chip, difference_chip

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor


def process_file(file_name: str):
    # 初始化一个字典来存储每个温度区间的总分钟数
    cur_time_diffs = defaultdict(float)
    cur_total_minutes = 0
    try:
        logging.info(f"file_name:{file_name}")

        # 读取 CSV 文件的列名
        column_names = pd.read_csv(file_name, nrows=0).columns.tolist()
        # 需要检查的列名列表
        columns_to_check = ['TECU_t']
        # 检查每个列名是否存在
        exists = {column: column in column_names for column in columns_to_check}
        # 检查 'TECU_t' 列是否存在，如果不存在则退出程序
        if not exists.get('TECU_t', False):
            return cur_time_diffs, cur_total_minutes

        selected_columns_list = ['TECU_t', 'timestamps']
        df: DataFrame = pd.read_csv(file_name, usecols=selected_columns_list)

        # 定义温度区间
        temperature_intervals = list(range(-40, 120, 5))

        # 计算每个温度区间的时间差
        for start_temp, end_temp in zip(temperature_intervals, temperature_intervals[1:]):
            mask = (df['TECU_t'] >= start_temp) & (df['TECU_t'] < end_temp)
            filtered_df = df[mask]

            if not filtered_df.empty:
                time_diff = (filtered_df['timestamps'].max() - filtered_df['timestamps'].min()) / 60
                cur_time_diffs[f'{start_temp} ~ {end_temp}'] = round(time_diff, 2)
    except Exception as e:
        logging.error(f"An error occurred: {e}")

    # 计算总的分钟数
    logging.debug(cur_time_diffs.values())
    cur_total_minutes = round(sum(cur_time_diffs.values()), 2)
    logging.info(f"cur_total_minutes:{cur_total_minutes}")

    return cur_time_diffs, cur_total_minutes


def temperature_duration(selected_file_ids: list[int] = None, selected_file_names: list[str] = None, max_workers=None):
    # 将整数列表转换为字符串列表
    selected_file_ids_str = [str(id) for id in selected_file_ids]
    # 使用逗号连接字符串列表
    result = ','.join(selected_file_ids_str)
    # query_table_by_sql()

    # 使用 ThreadPoolExecutor 并行处理每个文件
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(process_file, selected_file_names))

    # 合并所有文件的结果
    combined_time_diffs = defaultdict(float)
    total_minutes = 0

    for time_diffs, total_minute in results:
        for interval, minutes in time_diffs.items():
            combined_time_diffs[interval] += minutes
        total_minutes += total_minute

    return dict(combined_time_diffs), total_minutes


def modify_records(df):
    # 处理数据：将除 timestamps 列外的值小于 100 或大于 200 的值置为 0
    for column in df.columns:
        if column != 'timestamps':
            df.loc[(df[column] < -100) | (df[column] > 200), column] = 0
    # 转换回记录列表
    modified_records = df.to_dict('records')
    return modified_records


# 计算要跳过的行号列表
def get_skiprows(n):
    return lambda x: x % n != 0


def temperature_chip(selected_columns: str, csv_path: str) -> Dict[str, List]:
    try:
        # 将字符串转换为列表
        selected_columns_list = selected_columns.split(',')
        # 读取 CSV 文件的列名
        column_names = pd.read_csv(csv_path, nrows=0).columns.tolist()
        # 过滤出 selected_columns_list 中存在的列
        existing_columns = [col for col in selected_columns_list if col in column_names]
        logging.debug(f"existing_columns:{existing_columns}")

        if not existing_columns:
            return {col: [] for col in selected_columns}

        # 读取 CSV 文件并应用过滤
        df = pd.read_csv(csv_path, usecols=existing_columns, skiprows=get_skiprows(1000))

        if df.empty:
            return {col: [] for col in selected_columns}

        # 转换 DataFrame 到记录列表
        result_dicts = modify_records(df)

        # 使用字典推导式来创建结果字典
        temperature_time: Dict[str, List] = {
            col: [row[col] for row in result_dicts] for col in result_dicts[0].keys()
        }

        # 日志记录
        logging.debug(f"Original temperature_time: {temperature_time}")

        # 预先构建映射表
        key_mapping = {key: chipNamesConfig.get('chip_names', key) for key in temperature_time.keys()}

        # 使用映射表替换 temperature_time 中的键
        new_temperature_time: Dict[str, List] = {
            key_mapping[key]: value for key, value in temperature_time.items()
        }

        # 日志记录
        logging.debug(f"Modified temperature_time: {new_temperature_time}")

        return new_temperature_time
    except Exception as e:
        logging.error(f"Error processing CSV file: {e}")
        return {col: [] for col in selected_columns}


def process_sensor(sensor, temperature_time_dc1, tecu_temperatures):
    if sensor not in temperature_time_dc1:
        return None

    sensor_temperatures = temperature_time_dc1[sensor]
    min_length = min(len(tecu_temperatures), len(sensor_temperatures))

    series_data = [[sensor_temperatures[i], tecu_temperatures[i]] for i in range(min_length)]
    emphasis = {'focus': 'series'}
    markArea = {'silent': 'true', 'itemStyle': {'color': 'transparent', 'borderWidth': 1, 'borderType': 'dashed'},
                'data': [[{'name': '', 'xAxis': 'min', 'yAxis': 'min'}, {'xAxis': 'max', 'yAxis': 'max'}]]}
    # markPoint = {'data': [{'type': 'max', 'name': 'Max'},{'type': 'min', 'name': 'Min'}]}
    return {"name": sensor, "type": "scatter", "emphasis": emphasis, "data": series_data,
            "markArea": markArea}


def create_data_structure(temperature_time_dc1, sensors_list: list, num_processes=None):
    tecu_temperatures = temperature_time_dc1.get('TECU_t', [])
    with multiprocessing.Pool(processes=num_processes) as pool:
        results = pool.starmap(process_sensor,
                               [(sensor, temperature_time_dc1, tecu_temperatures) for sensor in sensors_list])

    # 过滤掉 None 结果
    results = [res for res in results if res is not None]

    return results


def str_to_list(sensors_str: str) -> List[str]:
    # 将字符串分割成列表
    selected_columns_dc1_list: List[str] = sensors_str.split(',')

    # 创建一个新的列表，存储替换后的列名
    sensors_list: List[str] = []

    for column in selected_columns_dc1_list:
        try:
            new_column = chipNamesConfig.get('chip_names', column.strip())
            sensors_list.append(new_column)
        except KeyError as e:
            logging.error(f"Key not found: {column}")
            sensors_list.append(column)  # 如果找不到键，保留原值

    return sensors_list


from concurrent.futures import ProcessPoolExecutor


def relative_difference(selected_file_names: list[str] = None, max_workers=None):
    # 使用 ProcessPoolExecutor 并行处理每个文件
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(relative_difference_process, selected_file_names))
        logging.debug(results)

    # 获取所有可能的列名
    all_columns = set(column for result in results for column in result.keys())
    # 计算所有文件中每列的最大值
    global_maxes = {column: max(result.get(column, 0) for result in results if column in result) for column in
                    all_columns}
    logging.debug(global_maxes)

    # 芯片字典(包含芯片名称、芯片温度阈值)
    chip_dict_list = chip_dict(db_pool)
    logging.debug(chip_dict_list)

    # 添加最大温度到 chip_dict_list
    for chip_info in chip_dict_list:
        measured_variable = chip_info['measured_variable']
        if measured_variable in global_maxes:
            chip_info['max_temperature'] = round(global_maxes[measured_variable], 1)
        else:
            chip_info['max_temperature'] = 0  # 或者设置为其他默认值

        chip_info['relative_difference_temperature'] = relative_difference_chip(chip_info['max_allowed_value'],
                                                                                chip_info['max_temperature'])
        chip_info['difference_temperature'] = difference_chip(chip_info['max_allowed_value'],
                                                              chip_info['max_temperature'])
    return chip_dict_list


def relative_difference_process(file_name: str):
    # 查看每个芯片的最大测量温度
    selected_columns_dc1_str: str = 'DC1_Th1,DC1_Th2,DC1_Th3,DC1_Th4,DC1_Th5,DC1_Th6,DC1_Th7,DC1_Th8'
    selected_columns_tc1_str: str = "TC1_Th1,TC1_Th2,TC1_Th3,TC1_Th4,TC1_Th5,TC1_Th6,TC1_Th7,TC1_Th8,TC1_Th9,TC1_Th10,TC1_Th11,TC1_Th12,TC1_Th13,TC1_Th14,TC1_Th15,TC1_Th16"
    selected_columns_tc2_str: str = "TC2_Th1,TC2_Th2,TC2_Th3,TC2_Th4,TC2_Th5,TC2_Th6,TC2_Th7,TC2_Th8,TC2_Th9,TC2_Th10,TC2_Th11,TC2_Th12,TC2_Th13"
    selected_columns: str = f"{selected_columns_dc1_str},{selected_columns_tc1_str},{selected_columns_tc2_str}"
    selected_columns_list: list = selected_columns.split(',')

    # 使用 pandas 读取 CSV 文件的列名
    column_names = pd.read_csv(file_name, nrows=0).columns.tolist()
    # 过滤出 selected_columns_list 中存在的列
    existing_columns = [col for col in selected_columns_list if col in column_names]

    if len(existing_columns) >= 1:
        # 使用 dask 读取数据
        df: DataFrame = pd.read_csv(file_name, usecols=existing_columns, engine='python')

        # 计算每列的最大值
        column_max_values = df.max().to_dict()
        del df
    else:
        # 如果没有匹配的列，返回空字典或抛出异常
        column_max_values = {}
        logging.debug("Warning: No matching columns found in the CSV file.")

    return column_max_values


def chip_dict(db_pool):
    query_sql = " select measured_variable, chip_name,max_allowed_value from chip_dict  where status = '1' "
    result_dicts = query_table(db_pool, query=query_sql)
    return result_dicts


def max_query(db_pool, selected_ids: list) -> DataFrame:
    max_query_sql = """
            SELECT
            ROUND(MAX(DC1_Th1)) AS DC1_Th1,
            ROUND(MAX(DC1_Th2)) AS DC1_Th2,
            ROUND(MAX(DC1_Th3)) AS DC1_Th3,
            ROUND(MAX(DC1_Th4)) AS DC1_Th4,
            ROUND(MAX(DC1_Th5)) AS DC1_Th5,
            ROUND(MAX(DC1_Th6)) AS DC1_Th6,
            ROUND(MAX(DC1_Th7)) AS DC1_Th7,
            ROUND(MAX(DC1_Th8)) AS DC1_Th8,
            ROUND(MAX(TC1_Th1)) AS TC1_Th1,
            ROUND(MAX(TC1_Th2)) AS TC1_Th2,
            ROUND(MAX(TC1_Th3)) AS TC1_Th3,
            ROUND(MAX(TC1_Th4)) AS TC1_Th4,
            ROUND(MAX(TC1_Th5)) AS TC1_Th5,
            ROUND(MAX(TC1_Th6)) AS TC1_Th6,
            ROUND(MAX(TC1_Th7)) AS TC1_Th7,
            ROUND(MAX(TC1_Th8)) AS TC1_Th8,
            ROUND(MAX(TC1_Th9)) AS TC1_Th9,
            ROUND(MAX(TC1_Th10)) AS TC1_Th10,
            ROUND(MAX(TC1_Th11)) AS TC1_Th11,
            ROUND(MAX(TC1_Th12)) AS TC1_Th12,
            ROUND(MAX(TC1_Th13)) AS TC1_Th13,
            ROUND(MAX(TC1_Th14)) AS TC1_Th14,
            ROUND(MAX(TC1_Th15)) AS TC1_Th15,
            ROUND(MAX(TC1_Th16)) AS TC1_Th16,
            ROUND(MAX(TC2_Th1)) AS TC2_Th1,
            ROUND(MAX(TC2_Th2)) AS TC2_Th2,
            ROUND(MAX(TC2_Th3)) AS TC2_Th3,
            ROUND(MAX(TC2_Th4)) AS TC2_Th4,
            ROUND(MAX(TC2_Th5)) AS TC2_Th5,
            ROUND(MAX(TC2_Th6)) AS TC2_Th6,
            ROUND(MAX(TC2_Th7)) AS TC2_Th7,
            ROUND(MAX(TC2_Th8)) AS TC2_Th8,
            ROUND(MAX(TC2_Th9)) AS TC2_Th9,
            ROUND(MAX(TC2_Th10)) AS TC2_Th10,
            ROUND(MAX(TC2_Th11)) AS TC2_Th11,
            ROUND(MAX(TC2_Th12)) AS TC2_Th12,
            ROUND(MAX(TC2_Th13)) AS TC2_Th13
        FROM chip_temperature
    """
    if len(selected_ids) > 0:
        # 将列表转换为逗号分隔的字符串
        selected_ids_str = ','.join(map(str, selected_ids))
        where_clause = f' WHERE file_id IN ({selected_ids_str})'
        max_sql = max_query_sql + where_clause

    logging.info(f"max_query_sql:{max_sql}")
    max_query_rslt_df = query_table_by_sql(db_pool, query_sql=max_sql)

    # 重置索引
    results_df = max_query_rslt_df.reset_index()

    # 为列起别名
    results_df = results_df.rename(columns={'index': 'Measurement_Point', 0: 'Measurement'})
    return results_df
