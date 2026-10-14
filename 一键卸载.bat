@echo off
cd /d "%~dp0"
chcp 65001 >nul
if not exist "%~dp0Antigravity中文.exe" (
  echo 请从 Releases 下载完整 Windows 压缩包。源码用户可用 Python 运行 tool.py。
  pause
  exit /b 1
)
start /wait "" "%~dp0Antigravity中文.exe" --uninstall
