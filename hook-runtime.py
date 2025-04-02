# hook-runtime.py - 将此文件放在项目根目录
import os
import sys

def pre_init_hook():
    """在应用初始化前设置搜索路径"""
    if hasattr(sys, '_MEIPASS'):
        # 将_internal目录添加到DLL搜索路径
        os.environ['PATH'] = os.path.join(sys._MEIPASS, '_internal') + os.pathsep + os.environ['PATH']
        # 也添加主目录
        os.environ['PATH'] = sys._MEIPASS + os.pathsep + os.environ['PATH']