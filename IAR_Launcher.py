import sys
import os
import json
import xml.etree.ElementTree as ET
import subprocess
import ctypes
import time

def is_admin():
    """检查是否以管理员权限运行程序"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def load_config():
    """加载配置文件，如果不存在则创建默认配置"""
    # 获取exe文件所在目录
    if getattr(sys, 'frozen', False):
        # 如果是打包后的exe运行
        app_dir = os.path.dirname(sys.executable)
    else:
        # 如果是开发环境运行
        app_dir = os.path.dirname(__file__)
    
    config_path = os.path.join(app_dir, 'config.json')
    
    # 如果配置文件不存在，创建默认配置
    if not os.path.exists(config_path):
        default_config = {
            "iar_paths": {
                "ARM": r"C:\iar\ewarm-9.60.3\common\bin\IarIdePm.exe",
                "RX": r"C:\Program Files (x86)\IAR Systems\Embedded Workbench 8.4\common\bin\IarIdePm.exe",
                "RH850": r"C:\Program Files (x86)\IAR Systems\Embedded Workbench for RH850 3.10\common\bin\IarIdePm.exe",
                "RL78": r"C:\Program Files (x86)\IAR Systems\Embedded Workbench for RL78 3.10\common\bin\IarIdePm.exe",
                "RISC-V": r"C:\Program Files\IAR Systems\IAR Embedded Workbench for RISC-V\common\bin\IarIdePm.exe",
                "MSP430": r"C:\Program Files (x86)\IAR Systems\Embedded Workbench 8.0\common\bin\IarIdePm.exe"
            },
            "default_config": {
                "check_for_updates": True,
                "show_console_output": False
            }
        }
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            print(f"已创建默认配置文件: {config_path}")
            ctypes.windll.user32.MessageBoxW(0, f"已创建默认配置文件，请根据您的IAR安装路径修改: {config_path}", "IAR Launcher", 0x40)
        except Exception as e:
            print(f"创建配置文件失败: {e}")
            return default_config
            
    # 读取配置文件
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"读取配置文件失败: {e}, 使用默认配置")
        ctypes.windll.user32.MessageBoxW(0, f"读取配置文件失败: {e}\n将使用默认配置运行。", "IAR Launcher", 0x30)
        return {
            "iar_paths": {
                "ARM": r"C:\iar\ewarm-9.60.3\common\bin\IarIdePm.exe",
                "RX": r"C:\Program Files (x86)\IAR Systems\Embedded Workbench 8.4\common\bin\IarIdePm.exe",
                "RH850": r"C:\Program Files (x86)\IAR Systems\Embedded Workbench for RH850 3.10\common\bin\IarIdePm.exe",
                "RL78": r"C:\Program Files (x86)\IAR Systems\Embedded Workbench for RL78 3.10\common\bin\IarIdePm.exe",
                "RISC-V": r"C:\Program Files\IAR Systems\IAR Embedded Workbench for RISC-V\common\bin\IarIdePm.exe",
                "MSP430": r"C:\Program Files (x86)\IAR Systems\Embedded Workbench 8.0\common\bin\IarIdePm.exe"
            },
            "default_config": {
                "check_for_updates": True,
                "show_console_output": False
            }
        }

def get_toolchain(ewp_path):
    """从ewp文件获取toolchain"""
    try:
        tree = ET.parse(ewp_path)
        root = tree.getroot()
        
        # 遍历所有配置中的toolchain
        for config in root.findall('.//configuration'):
            toolchain_elem = config.find('toolchain')
            if toolchain_elem is not None:
                name_elem = toolchain_elem.find('name')
                if name_elem is not None and name_elem.text:
                    return name_elem.text.strip().upper()
    except Exception as e:
        print(f"解析ewp文件失败: {e}")
    
    return None

def select_eww_file():
    """使用文件对话框让用户选择eww文件"""
    import tkinter as tk
    from tkinter import filedialog
    
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口
    
    file_path = filedialog.askopenfilename(
        title="选择IAR工作区文件(.eww)",
        filetypes=[
            ("IAR Workspace", "*.eww"),
            ("IAR Project", "*.ewp"),
            ("All files", "*.*")
        ]
    )
    
    root.destroy()
    return file_path

def main():
    # 参数检查
    if len(sys.argv) < 2:
        # 没有参数时显示使用说明
        print("IAR Launcher v1.0")
        print("用法: 将.eww文件拖拽到此程序上")
        print("或者双击程序后通过对话框选择.eww文件")
        print("示例: IAR_Launcher.exe <eww文件路径>")
        
        # 手动选择eww文件
        eww_path = select_eww_file()
        
        if not eww_path:
            # 用户取消选择，直接退出程序
            return
    else:
        eww_path = sys.argv[1]
    
    # 验证文件
    if not os.path.exists(eww_path):
        error_msg = f"错误: 文件不存在\n{eww_path}"
        ctypes.windll.user32.MessageBoxW(0, error_msg, "IAR Launcher", 0x10)
        return
    
    # 解析eww文件获取ewp路径
    try:
        tree = ET.parse(eww_path)
        root = tree.getroot()
        
        ewp_relative = None
        for project in root.findall('.//project'):
            path_elem = project.find('path')
            if path_elem is not None and path_elem.text:
                ewp_relative = path_elem.text
                break
        
        if not ewp_relative:
            ctypes.windll.user32.MessageBoxW(0, "无法从eww文件中找到ewp路径", "IAR Launcher", 0x10)
            return
        
        # 构建路径
        ewp_relative = ewp_relative.replace('$WS_DIR$\\', '').replace('$WS_DIR$/', '')
        ewp_path = os.path.join(os.path.dirname(eww_path), ewp_relative)
        
    except Exception as e:
        error_msg = f"解析eww文件失败:\n{str(e)}"
        ctypes.windll.user32.MessageBoxW(0, error_msg, "IAR Launcher", 0x10)
        return
    
    # 检查ewp文件
    if not os.path.exists(ewp_path):
        error_msg = f"找不到ewp文件:\n{ewp_path}"
        ctypes.windll.user32.MessageBoxW(0, error_msg, "IAR Launcher", 0x10)
        return
    
    # 获取toolchain
    toolchain = get_toolchain(ewp_path)
    if not toolchain:
        ctypes.windll.user32.MessageBoxW(0, "无法从ewp文件中识别toolchain", "IAR Launcher", 0x10)
        return
    
    # 加载配置文件
    config = load_config()
    iar_paths = config.get("iar_paths", {})
    
    if toolchain not in iar_paths:
        error_msg = f"未在配置文件中找到 {toolchain} 的路径，请编辑 config.json 文件添加对应路径。"
        ctypes.windll.user32.MessageBoxW(0, error_msg, "IAR Launcher", 0x10)
        return
    
    iar_exe = iar_paths[toolchain]
    
    # 检查IAR是否存在
    if not os.path.exists(iar_exe):
        error_msg = f"IAR可执行文件不存在:\n{iar_exe}\n请检查 config.json 文件中的路径配置。"
        ctypes.windll.user32.MessageBoxW(0, error_msg, "IAR Launcher", 0x10)
        
        # 提供手动选择功能
        if ctypes.windll.user32.MessageBoxW(0, "是否手动选择IAR的可执行文件？", "IAR Launcher", 0x34) == 6:  # IDYES=6
            import tkinter as tk
            from tkinter import filedialog
            
            root = tk.Tk()
            root.withdraw()
            iar_exe = filedialog.askopenfilename(
                title=f"选择 {toolchain} 版本的 IarIdePm.exe",
                filetypes=[("Executable files", "*.exe"), ("All files", "*.*")]
            )
            root.destroy()
            
            if not iar_exe:
                return

    # 启动IAR
    try:
        print(f"启动 {toolchain} IAR: {iar_exe}")
        subprocess.Popen([iar_exe, eww_path], shell=True)
    except Exception as e:
        error_msg = f"启动IAR失败:\n{str(e)}"
        ctypes.windll.user32.MessageBoxW(0, error_msg, "IAR Launcher", 0x10)

if __name__ == "__main__":
    main()