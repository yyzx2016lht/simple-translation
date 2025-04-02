# convert_icon.py
from PIL import Image
import os

# 确保文件存在
jpg_path = "translate.jpg"
if not os.path.exists(jpg_path):
    print(f"错误: 找不到文件 {jpg_path}")
    exit(1)

# 转换图像
img = Image.open(jpg_path)
icon_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
img.save("translate.ico", format="ICO", sizes=icon_sizes)
print("图标已转换完成: translate.ico")