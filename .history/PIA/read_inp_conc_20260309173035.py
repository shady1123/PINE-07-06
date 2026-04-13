import os
def read_input_conc(OP_ID,MAIN_DIR, PINE_ID, CAMPAIGN):
    PINE_DIR = os.path.join(MAIN_DIR, 'L2_Data', 'Temp_Spec')
    txt_filename = f'{PINE_ID}_{CAMPAIGN}_op_id_{OP_ID}_temp_mean.txt'
    txt_path = os.path.join(PINE_DIR, txt_filename)
    if not os.path.exists(txt_path):
        raise FileNotFoundError(f'File {txt_path} does not exist.')
    
    with open(txt_path, 'r') as f:
        lines = f.readlines()
        print(f"Contents of {txt_filename}:")
