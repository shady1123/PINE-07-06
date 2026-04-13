import os
import matplotlib.pyplot as plt
import numpy as np
def read_temp_mean_bin_inp_conc(OP_ID, MAIN_DIR, PINE_ID, CAMPAIGN):
    # 拼接文件路径
    SAVEPATH = os.path.join(MAIN_DIR, 'Plots')
    PINE_DIR = os.path.join(MAIN_DIR, 'L2_Data', 'Temp_Spec')
    txt_filename = f'{PINE_ID}_{CAMPAIGN}_op_id_{OP_ID}_temp_mean.txt'
    txt_path = os.path.join(PINE_DIR, txt_filename)
    
    # 校验文件是否存在
    if not os.path.exists(txt_path):
        raise FileNotFoundError(f'文件不存在: {txt_path}')

    # 配置项
    target_columns = ['Temp_start', 'Temp_end', 'cn_ice', 'cn_ice_std']
    HEADER_LINE_NUM = 15  # 表头在第15行
    
    # 自动创建保存目录
    os.makedirs(SAVEPATH, exist_ok=True)

    data = []
    header = None
    col_index_map = None

    # 读取文件（兼容编码）
    try:
        with open(txt_path, 'r', encoding='utf-8-sig') as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        with open(txt_path, 'r', encoding='gbk') as f:
            lines = f.readlines()

    # 校验文件行数
    if len(lines) < HEADER_LINE_NUM:
        raise ValueError(f"文件行数不足！仅{len(lines)}行，表头需要在第{HEADER_LINE_NUM}行")
    
    print(f"成功读取文件: {txt_path}，总行数: {len(lines)},表头行数: {HEADER_LINE_NUM}")

    # 解析数据
    for line_num, line in enumerate(lines, 1):
        line_stripped = line.strip()
        if not line_stripped:
            continue
        
        # 解析表头
        if line_num == HEADER_LINE_NUM:
            header = line_stripped.split()
            missing_cols = [col for col in target_columns if col not in header]
            if missing_cols:
                raise ValueError(f"表头缺少目标列：{missing_cols}")
            col_index_map = {col: idx for idx, col in enumerate(header)}
            continue
        
        # 解析表头后的数据行
        if line_num > HEADER_LINE_NUM and col_index_map:
            values = line_stripped.split()
            try:
                row = [float(values[col_index_map[col]]) for col in target_columns]
                data.append(row)
            except (ValueError, IndexError, KeyError):
                continue

    # 校验有效数据
    if not data:
        raise ValueError('未读取到有效数据')

    # 绘图并保存
    temp_start = [row[0] for row in data]
    cn_ice = [row[2] for row in data]
    cn_ice_std = [row[3] for row in data]

    # 数据平滑（可选，根据需要启用）
    from scipy.ndimage import uniform_filter1d
    cn_ice_smooth = uniform_filter1d(cn_ice, size=3)

    # 温度
    # 定义因子factor
    factor = 3
    plt.figure(figsize=(10, 6))
    plt.plot(temp_start[factor:-factor], cn_ice[factor:-factor], marker='o', linestyle='-',  color='#1f77b4', linewidth=2)
    plt.plot(temp_start[factor:-factor], cn_ice_smooth[factor:-factor], marker='', linestyle='-',  color='#ff7f0e', linewidth=2)
    plt.xlabel('Temperature (°C)', fontsize=12)
    plt.ylabel('INP Concentration (std L$^{-1}$)', fontsize=12)
    plt.title(f'{PINE_ID} {CAMPAIGN} | OP {OP_ID}\nINP Concentration vs Temperature', fontsize=13)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    # 横轴不留白，直接从数据范围开始
    # plt.xlim(temp_start[-factor], temp_start[factor])
    # 对数坐标
    plt.yscale('log')
    fig_path = os.path.join(SAVEPATH, f'{PINE_ID}_{CAMPAIGN}_op_id_{OP_ID}_inp_conc_vs_temp.png')
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f'绘图已保存至: {fig_path}')

    return data
