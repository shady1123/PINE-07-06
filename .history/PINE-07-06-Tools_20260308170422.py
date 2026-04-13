import os
import pandas as pd

def process_pine_data(file_count, txt_dir, excel_template_path, pine_id, campaign, savepath):
    """
    处理PINE测试数据，从指定目录的TXT文件提取信息并更新到Excel文件中
    动态生成Excel文件名：Logbook_{pine_id}_{campaign}.xlsx，保存到指定目录
    
    参数说明：
    ----------
    file_count : int
        需要处理的TXT文件数量（文件命名格式：pfr_PINE-07-06_test_opid-{数字}.txt）
    txt_dir : str
        TXT文件所在的目录路径（绝对路径）
    excel_template_path : str
        Excel模板文件的完整路径（包含文件名和扩展名）
    pine_id : str
        PINE编号（如：PINE-07-06），用于生成输出文件名
    campaign : str
        测试活动名称（如：test），用于生成输出文件名
    savepath : str
        最终Excel文件的保存目录（绝对路径）
    
    返回值：
    ----------
    pd.DataFrame
        更新后的DataFrame数据；若出错返回None
    str
        最终保存的Excel文件完整路径；若出错返回None
    """
    # -------------------------- 初始化数据 --------------------------
    try:
        # 读取Excel模板文件（只读取一次）
        df = pd.read_excel(excel_template_path)
    except FileNotFoundError:
        print(f"错误：Excel模板文件 {excel_template_path} 不存在！")
        return None, None
    except Exception as e:
        print(f"读取Excel模板文件时出错：{str(e)}")
        return None, None

    # 确保必要的列存在（如果不存在则创建）
    required_columns = [
        '# operation', 'total number of runs', 'Date', 
        'Start time operation', 'operation type (#)', 'Aerosol'
    ]
    for col in required_columns:
        if col not in df.columns:
            df[col] = None

    # -------------------------- 处理每个TXT文件 --------------------------
    # 记录成功处理的文件数
    success_count = 0
    for op_id in range(1, file_count + 1):
        # 构建TXT文件名（兼容pine_id动态生成，适配不同PINE编号）
        txt_filename = f'pfr_{pine_id}_{campaign}_opid-{op_id}.txt'
        txt_path = os.path.join(txt_dir, txt_filename)
        
        # 检查文件是否存在，避免文件缺失报错
        if not os.path.exists(txt_path):
            print(f"警告：文件 {txt_filename} 不存在，跳过处理")
            continue
        
        # 读取并处理TXT文件内容
        try:
            with open(txt_path, 'r', encoding='utf-8') as f:
                data = f.read().strip()
            
            # 按行分割数据
            lines = data.split('\n')
            if len(lines) < 2:  # 至少需要表头+1行数据
                print(f"警告：文件 {txt_filename} 数据不足，跳过处理")
                continue
            
            # 提取数据（跳过表头，处理实际数据行）
            data_rows = lines[1:]
            num_runs = len(data_rows)
            
            # 提取开始时间信息（第一行数据的第二列）
            first_row = data_rows[0].split('\t')
            if len(first_row) < 2:
                print(f"警告：文件 {txt_filename} 格式错误，跳过处理")
                continue
            
            time_start = first_row[1]
            date_part, time_part = time_start.split(' ')
            
            # 格式化日期（YY.MM.DD）
            date_formatted = f"{date_part[0:4]}.{date_part[5:7]}.{date_part[8:10]}"
            
            # -------------------------- 更新DataFrame --------------------------
            # 如果行索引超出当前DataFrame长度，扩展DataFrame
            if op_id >= len(df):
                # 创建空行并保持列结构一致
                new_row = pd.DataFrame([{}], columns=df.columns)
                df = pd.concat([df, new_row], ignore_index=True)
            
            # 更新核心数据列
            df.loc[op_id, '# operation'] = op_id
            df.loc[op_id, 'total number of runs'] = num_runs
            df.loc[op_id, 'Date'] = date_formatted
            df.loc[op_id, 'Start time operation'] = time_part
            
            # 填充operation type (#)和Aerosol列
            df.loc[op_id, 'operation type (#)'] = 'Test (5)'
            df.loc[op_id, 'Aerosol'] = 'Ambient'
            
            print(f"成功处理文件：{txt_filename} | 运行次数：{num_runs} | 操作ID：{op_id}")
            success_count += 1
        
        except UnicodeDecodeError:
            print(f"错误：文件 {txt_filename} 编码格式不支持（utf-8），请检查文件编码")
            continue
        except Exception as e:
            print(f"处理文件 {txt_filename} 时出错：{str(e)}")
            continue

    # -------------------------- 保存结果 --------------------------
    # 确保保存目录存在，不存在则创建
    if not os.path.exists(savepath):
        os.makedirs(savepath)
        print(f"提示：保存目录 {savepath} 不存在，已自动创建")
    
    # 动态生成输出Excel文件名
    output_excel_name = f"Logbook_{pine_id}_{campaign}.xlsx"
    output_excel_path = os.path.join(savepath, output_excel_name)
    
    try:
        # 保存更新后的DataFrame到指定目录
        df.to_excel(output_excel_path, index=False)
        print(f"\n处理完成！成功处理 {success_count} 个文件")
        print(f"结果已保存到：{output_excel_path}")
    except Exception as e:
        print(f"保存Excel文件时出错：{str(e)}")
        return None, None
    
    return df, output_excel_path