import matplotlib.pyplot as plt
import scipy.io
import pandas as pd
import os

# # 設定來源與輸出資料夾
# input_folder = r"G:\豪力輝數據\0度空氣20250410\logVib_Data"
output_folder = r"G:\豪力輝數據\空氣零度"
df = pd.read_csv(os.path.join(output_folder, "VibCur213_VirData.csv"))
# print(df.iloc[0].tolist())

plt.plot(df.iloc[0].tolist())
plt.show()

# # 建立輸出資料夾
# os.makedirs(output_folder, exist_ok=True)

# # 逐一處理所有 .mat 檔
# for file_name in os.listdir(input_folder):
#     if file_name.endswith(".mat"):
#         file_path = os.path.join(input_folder, file_name)
#         data = scipy.io.loadmat(file_path)
        
#         # 移除 MATLAB 內建變數
#         clean_data = {k: v for k, v in data.items() if not k.startswith("__")}
        
#         for key, value in clean_data.items():
#             try:
#                 # 嘗試轉成 DataFrame
#                 df = pd.DataFrame(value)
#                 output_file = os.path.join(
#                     output_folder, f"{os.path.splitext(file_name)[0]}_{key}.csv"
#                 )
#                 df.to_csv(output_file, index=False)
#                 print(f"✔ 轉換完成: {output_file}")
#             except Exception as e:
#                 print(f"⚠ 無法轉換 {file_name} 內的 {key}: {e}")

