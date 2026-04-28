import os
from PIL import Image

def create_ico(filename):
    # 自動獲取「目前這份程式碼」所在的資料夾路徑
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(base_dir, filename)
    output_path = os.path.join(base_dir, 'output_icon.ico')

    # 檢查檔案是否真的在那個路徑
    if not os.path.exists(input_path):
        print(f"❌ 錯誤：在以下位置找不到檔案：\n{input_path}")
        print(f"請確保圖片跟程式碼放在同一個資料夾。")
        return

    try:
        img = Image.open(input_path)
        sizes = [(16, 16), (32, 32), (64, 64), (128, 128), (256, 256)]
        img.save(output_path, format='ICO', sizes=sizes)
        print(f"✅ 成功！檔案已產生於：\n{output_path}")
    except Exception as e:
        print(f"❌ 轉換過程出錯：{e}")

# 執行
create_ico('ico.png')