@echo off
cd /d "%~dp0"
py -3.13 parser.py -t 30 -r 3 %*
