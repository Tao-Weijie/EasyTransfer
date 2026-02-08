import sys
# 确保脚本路径在 sys.path 中
sys.path.append("/Users/taomou/user/3_Script/EasyTransfer/build_WIP/maya")
import test_maya_functions
import importlib

importlib.reload(test_maya_functions) # <--- 强制清除缓存，重新读取文件

test_maya_functions.EasyCopy()