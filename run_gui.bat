@echo off
setlocal
cd /d "%~dp0"
python video_editor_gui.py
if errorlevel 1 pause
