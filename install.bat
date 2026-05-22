@echo off
REM Ставит зависимости в тот же Python, которым запускается парсер
py -3.13 -m pip install -r requirements.txt
if errorlevel 1 exit /b 1
echo.
echo OK. Запуск: run.bat  или  py -3.13 parser.py
