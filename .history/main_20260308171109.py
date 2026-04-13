from PIA.process_pine_data import process_pine_data

if __name__ == "__main__":

    FILE_COUNT = 25  # 需要处理的文件数量
    TXT_DIR = r'D:\Download\Baidu Wangpan\2025.12.PINEs-Test\202512_06_Test\raw_Data'  # TXT文件目录
    EXCEL_TEMPLATE_PATH = r"D:\File\python\demo\PINE-07-06\Logbook_pine_id_campaign.xlsx"  # Excel模板路径
    PINE_ID = "PINE-07-06"  # PINE编号
    CAMPAIGN = "test"  # 测试活动名称
    SAVEPATH = r"D:\Download\Baidu Wangpan\2025.12.PINEs-Test\202512_06_Test"  # 保存目录

    # 调用函数处理数据
    result_file, _ = process_pine_data(FILE_COUNT, TXT_DIR, EXCEL_TEMPLATE_PATH, PINE_ID, CAMPAIGN, SAVEPATH)
