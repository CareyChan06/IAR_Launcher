@echo off
setlocal enabledelayedexpansion

:: 检查是否传递了参数
if "%~1"=="" (
    echo IAR Launcher v1.0
    echo 用法: 将.eww文件拖拽到此程序上
    echo 示例: IAR_Launcher.bat ^<eww文件路径^>
    
    REM 显示编译说明
    echo.
    echo 编译说明:
    echo 如果需要重新编译exe文件，请确保已安装PyInstaller:
    echo   pip install pyinstaller
    echo 然后运行:
    echo   pyinstaller --onefile --windowed IAR_Launcher.py
    echo.
    
    pause
    goto :eof
)

:: 运行Python脚本
python "%~dp0IAR_Launcher.py" "%~1"

:: 如果直接双击bat文件，暂停等待用户按键
if "%~1"=="%CD%" pause