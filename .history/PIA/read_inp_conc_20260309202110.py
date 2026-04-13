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
        raise FileNotFoundError(f'文件不存在: {txt_path}')
    print(f"成功找到文件，正在读取: {txt_path}")

    # 定义目标列名（和txt表头严格对应）
    target_columns = [
        'run_id', 'datetime', 'chamber', 'T_min', 'P_end', 
        'Fe_mean', 'INP_count', 'INP_cn_0', 'INP_cn_flush', 
        'spd_cn_0', 'spd_cn_flush'
    ]
    data = []
    header = None
    col_index_map = None

    # 读取文件：优先适配Windows常用编码，避免乱码
    try:
        with open(txt_path, 'r', encoding='utf-8-sig') as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        print("utf-8编码读取失败，切换为GBK编码读取")
        with open(txt_path, 'r', encoding='gbk') as f:
            lines = f.readlines()
    
    print(f"文件总行数: {len(lines)}")

    # 逐行处理
    for line_num, line in enumerate(lines, 1):
        # 去除首尾所有空白符（空格、制表符、换行符）
        strip_line = line.strip()
        # 跳过空行
        if not strip_line:
            continue
        
        # 跳过元数据行（带冒号的行）
        if ':' in strip_line:
            continue
        
        # ========== 核心修复1：自动适配任意空白符分割 ==========
        # 不带参数的split()自动按任意空白符（多个空格/制表符）分割，完美适配你的txt格式
        row_items = strip_line.split()
        if not row_items:
            continue

        # ========== 核心修复2：宽松匹配表头行，避免匹配失效 ==========
        if 'run_id' in row_items and 'datetime' in row_items:
            header = row_items
            print(f"成功识别表头行(行号{line_num})，表头列: {header}")
            # 建立列名-索引映射
            col_index_map = {col: idx for idx, col in enumerate(header) if col in target_columns}
            # 校验目标列是否缺失
            missing_cols = [col for col in target_columns if col not in col_index_map]
            if missing_cols:
                raise ValueError(f"表头中缺失目标列: {missing_cols}")
            print(f"成功建立列映射: {col_index_map}")
            continue
        
        # 仅当表头已解析完成，才处理数据行
        if col_index_map is None:
            continue
        
        # 提取并转换数据
        try:
            row_data = []
            for col in target_columns:
                idx = col_index_map[col]
                val = row_items[idx]
                # 类型转换
                if col in ['run_id', 'chamber', 'INP_count']:
                    val = int(val) if val.lower() != 'nan' else np.nan
                elif col == 'datetime':
                    val = val
                else:
                    val = float(val) if val.lower() != 'nan' else np.nan
                row_data.append(val)
            data.append(row_data)
        except (ValueError, IndexError) as e:
            print(f"跳过行号{line_num}的无效数据行，内容: {strip_line[:50]}...，错误: {e}")
            continue

    # 校验有效数据
    print(f"最终读取到有效数据行数: {len(data)}")
    if not data:
        raise ValueError("文件中未读取到有效数据，请检查文件格式、分隔符、编码是否正确")

    # 拆分画图数据
    datetime_list = [row[1] for row in data]
    inp_cn_0_list = [row[7] for row in data]
    # 转换时间格式，优化x轴显示
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

    # 返回结构化数据，方便后续分析
    return {
        'columns': target_columns,
        'data': data,
        'datetime': datetime_objs,
        'INP_cn_0': inp_cn_0_list
    }
