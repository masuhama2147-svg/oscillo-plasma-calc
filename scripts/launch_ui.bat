@echo off
REM ============================================================
REM  Windows 版 起動スクリプト
REM  このファイルをダブルクリックすると Shiny UI が立ち上がります
REM  失敗してもメッセージが出てから止まるよう pause を必ず入れる
REM ============================================================

chcp 65001 > nul
cd /d "%~dp0\.."

echo ============================================
echo  野村研究室 液中プラズマ 解析ソフト 起動中
echo ============================================
echo.

if not exist ".venv\Scripts\shiny.exe" (
    echo [エラー] 仮想環境 .venv が見つかりません。
    echo.
    echo セットアップが完了していない可能性があります。
    echo README.md の「Windows 5 ステップセットアップ」を実行してから再試行してください。
    echo.
    pause
    exit /b 1
)

echo [情報] 起動準備が整いました。
echo [情報] ブラウザで http://127.0.0.1:8000 を開いてください。
echo.
echo [Defender 警告が出たら] 「詳細情報」→「実行」をクリック。
echo [止めるとき] Ctrl+C を押すか、このウィンドウを閉じてください。
echo.

.venv\Scripts\shiny run --port 8000 src\oscillo_plasma_calc\ui\app.py

echo.
echo [情報] サーバが停止しました。
pause
