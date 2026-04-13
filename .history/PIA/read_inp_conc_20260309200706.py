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
        print(f"Contents of {txt_filename}:")
        for line in lines:
            print(line.strip())
        
        
