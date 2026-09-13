@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
cd /d "%~dp0"
if not exist logs mkdir logs
python run.py %1 >> logs\bat_%DATE:~0,4%-%DATE:~5,2%-%DATE:~8,2%.log 2>&1
