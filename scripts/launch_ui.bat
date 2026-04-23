@echo off
REM ============================================================
REM  Windows 版 起動スクリプト
REM  このファイルをダブルクリックすると Shiny UI が立ち上がります
REM ============================================================
cd /d %~dp0\..

if not exist ".venv\Scripts\shiny.exe" (
    echo [エラー] .venv が見つかりません。
    echo まず PowerShell を開いて以下を 1 回だけ実行してください:
    echo   python -m venv .venv
    echo   .\.venv\Scripts\pip install numpy scipy pandas openpyxl sympy plotly matplotlib jinja2 shiny shinywidgets pytest pyyaml
    pause
    exit /b 1
)

echo Shiny UI を起動します。ブラウザで http://127.0.0.1:8000 を開いてください。
echo 終了するには Ctrl+C を押してください。
.\.venv\Scripts\shiny run --port 8000 src\oscillo_plasma_calc\ui\app.py
pause
