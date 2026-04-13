import os
import matplotlib.pyplot as plt
from datetime import datetime
import numpy as np

def read_input_conc(OP_ID, MAIN_DIR, PINE_ID, CAMPAIGN):
    # 拼接文件路径
    PINE_DIR = os.path.join(MAIN_DIR, 'L1_Data', 'exportdata', 'exportdata_ice')
    txt_filename = f'{PINE_ID}_{CAMPAIGN}_op_id_{OP_ID}_ice.txt'
    txt_path = os.path.join(PINE_DIR, txt_filename)
    
    # 校验文件是否存在
    if not os.path.exists(txt_path):
        raise FileNotFoundError(f'File {txt_path} does not exist.')
    
    # 定义目标列名（和txt表头严格对应）
    target_columns = [
        'run_id', 'datetime', 'chamber', 'T_min', 'P_end', 
        'Fe_mean', 'INP_count', 'INP_cn_0', 'INP_cn_flush', 
        'spd_cn_0', 'spd_cn_flush'
    ]
    data = []
    header = None
    col_index_map = None

    # 读取并处理TXT文件内容
    with open(txt_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        for line in lines:
            # 去除首尾空白符，跳过空行
            strip_line = line.strip()
            if not strip_line:
                continue
            
            # 跳过元数据行（带冒号的行），处理表头和数据行
            if ':' in strip_line:
                continue
            
            # 分割行数据（txt用制表符\t分隔）
            row_items = strip_line.split('\t')
            
            # 处理表头行，建立列名-索引映射
            if strip_line.startswith('run_id'):
                header = row_items
                col_index_map = {col: idx for idx, col in enumerate(header) if col in target_columns}
                # 校验目标列是否都存在
                missing_cols = [col for col in target_columns if col not in col_index_map]
                if missing_cols:
                    raise ValueError(f"表头中缺失目标列: {missing_cols}")
                continue
            
            # 处理数据行：仅当表头已解析完成时
            if col_index_map is None:
                continue
            
            # 按目标列提取数据
            try:
                row_data = []
                for col in target_columns:
                    idx = col_index_map[col]
                    val = row_items[idx]
                    # 类型转换：run_id、chamber、INP_count为int，其余数值为float，时间为字符串
                    if col in ['run_id', 'chamber', 'INP_count']:
                        val = int(val) if val.lower() != 'nan' else np.nan
                    elif col == 'datetime':
                        val = val
                    else:
                        val = float(val) if val.lower() != 'nan' else np.nan
                    row_data.append(val)
                data.append(row_data)
            except (ValueError, IndexError) as e:
                print(f"跳过无效数据行: {strip_line}, 错误: {e}")
                continue

    # 无有效数据时抛出异常
    if not data:
        raise ValueError("文件中未读取到有效数据")

    # 拆分画图所需数据
    datetime_list = [row[1] for row in data]
    inp_cn_0_list = [row[7] for row in data]
    # 转换时间格式，解决x轴显示问题
    datetime_objs = [datetime.strptime(dt, '%Y-%m-%d %H:%M:%S.%f') for dt in datetime_list]

    # 画图
    plt.figure(figsize=(12, 6))
    plt.plot(datetime_objs, inp_cn_0_list, 'o-', color='steelblue', markersize=4)
    plt.xlabel('Datetime')
    plt.ylabel('INP_cn_0 (stdL-1)')
    plt.title(f'INP Concentration over Time (OP_ID: {OP_ID})')
    plt.xticks(rotation=45)
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.show()

    # 返回处理好的结构化数据，方便后续分析
    return {
        'columns': target_columns,
        'data': data,
        'datetime': datetime_objs,
        'INP_cn_0': inp_cn_0_list
    }
