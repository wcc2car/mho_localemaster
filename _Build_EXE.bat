@echo off
cd /d %~dp0
rem chcp 65001 > nul


C:\Python\Localemaster\.venv\Scripts\pyinstaller --onefile --console --icon=icon.ico Localemaster_v1.py

rem C:\Python\Localemaster\.venv\Scripts\pyinstaller --onefile --console --icon=ico.ico Localemaster_v1.py
pause