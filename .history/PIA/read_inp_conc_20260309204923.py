import os
import matplotlib.pyplot as plt
from datetime import datetime
import numpy as np

def read_input_conc(OP_ID, MAIN_DIR, PINE_ID, CAMPAIGN):
    # 拼接文件路径
    SAVEPATH = os.path.join(MAIN_DIR, 'Plots')
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
    data_start_line_num = None  # 记录数据开始的行号

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
        
        # 跳过元数据行（带冒号的行），但仅在未找到表头时跳过，由于数据行含有时间字段也会带冒号
        if col_index_map is None and ':' in strip_line:
            continue
        
        # 自动适配任意空白符分割
        row_items = strip_line.split()
        if not row_items:
            continue

        # 匹配表头行
        if 'run_id' in row_items and 'datetime' in row_items:
            header = row_items
            data_start_line_num = line_num + 1  # 数据从下一行开始
            # 建立列名-索引映射
            col_index_map = {col: idx for idx, col in enumerate(header) if col in target_columns}
            # 校验目标列是否缺失
            missing_cols = [col for col in target_columns if col not in col_index_map]
            if missing_cols:
                raise ValueError(f"表头中缺失目标列: {missing_cols}")
            continue
        
        # 仅当表头已解析完成，才处理数据行
        if col_index_map is None:
            continue      

        # 修复带空格的时间被分割成两列的问题
        if 'datetime' in col_index_map and len(row_items) == len(header) + 1:
            dt_idx = col_index_map['datetime']
            # 将日期和时间重新拼接在一起
            row_items[dt_idx] = row_items[dt_idx] + ' ' + row_items[dt_idx + 1]
            del row_items[dt_idx + 1]
        
        # 先检查列数是否足够
        max_needed_idx = max(col_index_map.values())
        if len(row_items) <= max_needed_idx:
            print(f"  ❌ 跳过：列数不足！需要至少 {max_needed_idx + 1} 列，实际只有 {len(row_items)} 列\n")
            continue
        
        # 提取并转换数据
        try:
            row_data = []
            for col in target_columns:
                idx = col_index_map[col]
                val = row_items[idx]
                # 类型转换
                if col in ['run_id', 'chamber', 'INP_count']:
                    # 这些列需要是整数，但允许nan
                    if val.lower() == 'nan':
                        val = np.nan
                    else:
                        # 先转float再转int，避免 '4.0' 这种字符串直接转int报错
                        val = int(float(val))
                elif col == 'datetime':
                    val = val  # 时间保持字符串
                else:
                    # 其他列是浮点数，允许nan
                    val = float(val) if val.lower() != 'nan' else np.nan
                row_data.append(val)
            data.append(row_data)

        except Exception as e:
            print(f"  ❌ 跳过：类型转换失败！错误类型: {type(e).__name__}, 错误信息: {e}\n")
            continue

    # 校验有效数据
    print(f"\n================ 最终统计 ================")
    print(f"最终读取到有效数据行数: {len(data)}")

    # 拆分画图数据
    datetime_list = [row[1] for row in data]
    inp_cn_0_list = [row[6] for row in data]
    
    # 转换时间格式，优化x轴显示（兼容带毫秒和不带毫秒的时间）
    datetime_objs = []
    for dt in datetime_list:
        try:
            # 尝试带有微秒/毫秒的格式解析
            datetime_objs.append(datetime.strptime(dt, '%Y-%m-%d %H:%M:%S.%f'))
        except ValueError:
            # 去除微秒后重试
            datetime_objs.append(datetime.strptime(dt, '%Y-%m-%d %H:%M:%S'))

    # 画图
    plt.figure(figsize=(12, 6))
    plt.plot(datetime_objs, inp_cn_0_list, 'o-', color='steelblue', markersize=4)
    plt.xlabel('Datetime')
    plt.ylabel('INP_cn_0 (stdL-1)')
    plt.title(f'INP Concentration over Time (OP_ID: {OP_ID})')
    plt.xticks(rotation=45)
    plt.grid(alpha=0.3)
    plt.tight_layout()
    # plt.show()
    plt.savefig(f'{SAVEPATH}/{PINE_ID}_{CAMPAIGN}_op_id_{OP_ID}_INP_concentration.png')
    plt.close()

    # 返回结构化数据，方便后续分析
    
    return data
