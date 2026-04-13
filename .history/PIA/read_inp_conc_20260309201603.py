import os
def read_input_conc(OP_ID,MAIN_DIR, PINE_ID, CAMPAIGN):
    PINE_DIR = os.path.join(MAIN_DIR, 'L1_Data','exportdata', 'exportdata_ice')
    txt_filename = f'{PINE_ID}_{CAMPAIGN}_op_id_{OP_ID}_ice.txt'
    txt_path = os.path.join(PINE_DIR, txt_filename)
    if not os.path.exists(txt_path):
        raise FileNotFoundError(f'File {txt_path} does not exist.')
    
    # 读取并处理TXT文件内容
    with open(txt_path, 'r') as f:
        lines = f.readlines()
    # 提取所需数据，run_id、datatime、chamber、T_min、P_end、Fe_mean、INP_count、INP_cn_0、INP_cn_flush、spd_cn_0、spd_cn_flush
    data = []
    for line in lines:
        if ':' not in line:
            continue
        if line.startswith('run_id'):
            run_id = line.split(':', 1)[1].strip()
        elif line.startswith('datatime'):
            date = line.split(':', 1)[1].strip()
        elif line.startswith('chamber'):
            chamber = line.split(':', 1)[1].strip()
        elif line.startswith('T_min'):
            T_min = line.split(':', 1)[1].strip()
        elif line.startswith('P_end'):
            P_end = line.split(':', 1)[1].strip()
        elif line.startswith('Fe_mean'):
            Fe_mean = line.split(':', 1)[1].strip()
        elif line.startswith('INP_count'):
            INP_count = line.split(':', 1)[1].strip()
        elif line.startswith('INP_cn_0'):
            INP_cn_0 = line.split(':', 1)[1].strip()
        elif line.startswith('INP_cn_flush'):
            INP_cn_flush = line.split(':', 1)[1].strip()
        elif line.startswith('spd_cn_0'):
            spd_cn_0 = line.split(':', 1)[1].strip()
        elif line.startswith('spd_cn_flush'):
            spd_cn_flush = line.split(':', 1)[1].strip()
    # 将提取的数据添加到data列表中
    data.append([run_id, date, chamber, T_min, P_end, Fe_mean, INP_count, INP_cn_0, INP_cn_flush, spd_cn_0, spd_cn_flush])

    # 画图
    import matplotlib.pyplot as plt
   
    # data列表datatime、INP_cn_0画图
    datatime = [f"{date}"]
    INP_cn_0 = [float(INP_cn_0)]
    plt.plot(datatime, INP_cn_0, 'o')
    plt.xlabel('Date')
    plt.ylabel('INP_cn_0')
    plt.title('INP Concentration over Time')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

        
        
