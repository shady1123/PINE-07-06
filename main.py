from PIA.process_pine_data import process_pine_data
from PIA.read_inp_conc import read_input_conc
from PIA.read_temp_mean_bin_inp_conc import read_temp_mean_bin_inp_conc
from PIA.read_temp_bin_inp_conc import read_temp_bin_inp_conc
if __name__ == "__main__":
    
    ############################################ 配置参数 ######### ###################################
    EXCEL_TEMPLATE_PATH = r"D:\File\python\Scientific work\PINE-07-06\Logbook_pine_id_campaign.xlsx"  # Excel模板路径
    OP_ID = 1       # 操作ID
    FILE_COUNT = 1  # 需要处理的文件数量 == OP_ID 的最大值
    
    # 实验1、
    # MAIN_DIR = r'D:\Download\PINE-07-06\20260410_test'  # 主目录路径
    # PINE_ID = "PINE-07-06"      # PINE编号
    # CAMPAIGN = "20260410_test"  # 测试活动名称

    # 实验2、
    # MAIN_DIR = r'D:\Download\Baidu Wangpan\2025.12.PINEs-Test\202512_06_Test'
    # PINE_ID = "PINE-07-06"      # PINE编号
    # CAMPAIGN = "test"  # 测试活动名称

    # 实验3、
    MAIN_DIR = r'D:\Download\Baidu Wangpan\2025.12.PINEs-Test\202512_Test'
    PINE_ID = "PINE-07-04"      # PINE编号
    CAMPAIGN = "202512_Test"  # 测试活动名称

    ############################################ 配置参数结束 ######### ###################################
    # 保存结果的目录
    SAVEPATH = MAIN_DIR  # 保存目录
    ############################################ 配置参数结束 ######### ###################################


    # 处理数据并获取结果
    # result_file, _ = process_pine_data(FILE_COUNT, MAIN_DIR, EXCEL_TEMPLATE_PATH, PINE_ID, CAMPAIGN, SAVEPATH)
    # 1) run级（推荐做最终INPs时间序列）
    # read_input_conc(
    #     OP_ID=1, 
    #     MAIN_DIR=MAIN_DIR, 
    #     PINE_ID=PINE_ID, 
    #     CAMPAIGN=CAMPAIGN, 
    #     series_source="ice_run",
    #     downsample_n=1,
    #     min_cn_ice=10,       # 过滤底部密集低值带
    #     resample_minutes=60  # 10分钟中位数 
    #                 )
    
    # 1秒数据太密，按10倍降采样
    # read_input_conc(
    #     OP_ID=1,
    #     MAIN_DIR=MAIN_DIR,
    #     PINE_ID= PINE_ID,
    #     CAMPAIGN= CAMPAIGN,
    #     series_source="cn_bin",
    #     cn_dt=1,
    #     downsample_n=10
    # )

    # 3秒数据，按5倍降采样
    # read_input_conc(
    #     OP_ID=1,
    #     MAIN_DIR=MAIN_DIR,
    #     PINE_ID= PINE_ID,
    #     CAMPAIGN= CAMPAIGN,
    #     series_source="cn_bin",
    #     cn_dt=3,
    #     downsample_n=1,
    #     min_cn_ice=10,       # 过滤底部密集低值带
    #     resample_minutes=60  # 10分钟中位数
    # )

    # read_temp_mean_bin_inp_conc(
    #     OP_ID, 
    #     MAIN_DIR, 
    #     PINE_ID, 
    #     CAMPAIGN, 
    #     smooth_window=5,   # 平滑窗口，单位为数据点数量，默认为3。会被校正为>=1且不大于数据长度。优先使用奇数窗口以便居中。
    #     show_std_band=True, # 是否显示标准差带，默认为True
    #     show_smooth_curve=False # 是否显示平滑曲线，默认为True
    #     )
    
    # 读取温度分箱的INP浓度数据，进行分组并导出CSV文件
    # read_temp_bin_inp_conc(
    #     OP_ID=22,
    #     MAIN_DIR=MAIN_DIR,
    #     PINE_ID= PINE_ID,
    #     CAMPAIGN= CAMPAIGN,
    #     runs_per_big_run=12,    # 每个大run包含的runs数量，默认为10
    #     unify_temp_range=True,  # 是否统一温度范围，默认为True
    #     start_run_id=None,          # 起始run_id，默认为None表示不设限制
    #     end_run_id=None,            # 结束run_id，默认为None表示不设限制
    #     export_group_csv=True,  # 是否导出分组CSV文件，默认为True
    # )

    # 计算每月平均INP浓度
    from PIA.cal_month_ave_inp_conc import cal_month_ave_inp_conc

    # 全部op_id汇总（建议年数据用这个）
    # 仅画有数据月份（跳过缺失月）
    cal_month_ave_inp_conc(
        MAIN_DIR=MAIN_DIR,
        PINE_ID= PINE_ID,
        CAMPAIGN= CAMPAIGN,
        OP_ID=None, # None表示读取该campaign下所有 *_temp.txt
        target_temps=(-15, -20, -25, -30), # 代表性温度列表
        plot_only_existing_months=False, # 是否仅画有数据月份，默认为False
        figsize=(7,6), # 图像大小，默认为(8.2, 6.2)
        bar_width=0.20, # 条形宽度，默认为0.28
        dpi=600,
        show_title=False, # 是否显示标题，默认为True
        month_spacing=0.35 # 月份间隔
    )

    # 计算日间夜间平均INP浓度
    from PIA.cal_day_night_ave_inp_conc import cal_day_night_ave_inp_conc

    # 全部 OP 汇总
    cal_day_night_ave_inp_conc(
        MAIN_DIR=MAIN_DIR,
        PINE_ID= PINE_ID,
        CAMPAIGN= CAMPAIGN,
        OP_ID = None, # None 表示读取该campaign下所有 *_temp.txt
        target_temps=(-15, -20, -25, -30), # 温度范围
        temp_tolerance=3.0, # 放宽温度匹配以增加样本量，尤其是夜间
        show_title=False # 是否显示标题，默认为True
    )
