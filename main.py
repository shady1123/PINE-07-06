from PIA.process_pine_data import process_pine_data
from PIA.read_inp_conc import read_input_conc
from PIA.read_temp_bin_inp_conc import read_temp_bin_inp_conc
if __name__ == "__main__":
    
    ############################################ 配置参数 ######### ###################################
    OP_ID = 1       # 操作ID
    FILE_COUNT = 1  # 需要处理的文件数量 == OP_ID 的最大值
    MAIN_DIR = r'D:\Download\PINE-07-06\20260410_test'  # 主目录路径
    EXCEL_TEMPLATE_PATH = r"D:\File\python\Scientific work\PINE-07-06\Logbook_pine_id_campaign.xlsx"  # Excel模板路径
    PINE_ID = "PINE-07-06"      # PINE编号
    CAMPAIGN = "20260410_test"  # 测试活动名称
    SAVEPATH = MAIN_DIR  # 保存目录
    ############################################ 配置参数结束 ######### ###################################


    # 处理数据并获取结果
    result_file, _ = process_pine_data(FILE_COUNT, MAIN_DIR, EXCEL_TEMPLATE_PATH, PINE_ID, CAMPAIGN, SAVEPATH)
    # data = read_input_conc(OP_ID, MAIN_DIR, PINE_ID, CAMPAIGN)
    # temp_data = read_temp_bin_inp_conc(OP_ID, MAIN_DIR, PINE_ID, CAMPAIGN)
   