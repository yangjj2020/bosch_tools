import glob
import os

from asammdf import MDF


measure_file_path = r'C:\Users\Administrator\Downloads\input\HTM\127001\HTM01_highway.mf4'
mdf = MDF(measure_file_path)
output_file = r'C:\Users\Administrator\Downloads\output\HTM\127001\HTM01_highway.csv'
df = mdf.to_dataframe()
# with open(output_file, 'w', newline='') as f:
#     df.to_csv(f, index=True)

output_path = r'C:\Users\Administrator\Downloads\output\HTM\127001'
# 列出output_path目录下所有的csv文件
csv_files = glob.glob(os.path.join(output_path, '*.csv'))
for file in csv_files:
    file_name, _ = os.path.splitext(os.path.basename(file))
    print( file_name)

