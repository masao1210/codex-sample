@echo off
chcp 65001 >nul
rem 販売管理アプリを起動する（ダブルクリックで実行）
rem 初回は、必要なソフトの導入・データベースの作成・ログイン用ユーザーの作成も行う
setlocal
cd /d "%~dp0"
title 販売管理

rem --- 仮想環境（.venv）を探す。なければ作る ---
if exist ".venv\Scripts\activate.bat" (
    set "VENV=.venv"
) else if exist "..\.venv\Scripts\activate.bat" (
    set "VENV=..\.venv"
) else (
    where python >nul 2>nul || goto :nopython
    echo 初回の準備をしています。数分かかります...
    python -m venv .venv || goto :error
    set "VENV=.venv"
)
call "%VENV%\Scripts\activate.bat" || goto :error

rem --- 必要なソフト（Django）が入っていなければ入れる ---
python -c "import django" >nul 2>nul
if errorlevel 1 (
    echo 必要なソフトを入れています...
    python -m pip install -r requirements.txt || goto :error
)

rem --- データベースを最新の形にする ---
python manage.py migrate -v 0 || goto :error

rem --- ログイン用ユーザーがいなければ作る ---
python manage.py shell -v 0 -c "from django.contrib.auth.models import User; import sys; sys.exit(0 if User.objects.exists() else 1)" >nul 2>nul
if errorlevel 1 (
    echo.
    echo ===== ログイン用のユーザーを作ります =====
    echo メールアドレスは空欄のまま Enter で大丈夫です。
    echo パスワードは入力しても画面に表示されません。
    echo.
    python manage.py createsuperuser || goto :error
    echo.
    choice /c YN /m "お試し用のダミーデータを入れますか？ Y=入れる N=入れない"
    if not errorlevel 2 python manage.py load_demo
)

rem --- 起動し、3秒後にブラウザを開く ---
echo.
echo ==========================================================
echo  販売管理を起動します。少しするとブラウザが開きます。
echo  開かないときは http://127.0.0.1:8000/ を開いてください。
echo.
echo  この画面は閉じないでください。最小化は大丈夫です。
echo  画面の中をクリックすると止まることがあります。
echo  止まったら Enter キーを押すと動き出します。
echo  終わるときは Ctrl+C を押してから、この画面を閉じます。
echo ==========================================================
echo.
start "" /b python -c "import time, webbrowser; time.sleep(3); webbrowser.open('http://127.0.0.1:8000/')"
python manage.py runserver
echo.
echo 販売管理を終了しました。
pause
exit /b 0

:nopython
echo.
echo Python が見つかりません。
echo https://www.python.org/downloads/ から Python を入れてください。
echo インストール画面で「Add python.exe to PATH」にチェックを入れてください。
pause
exit /b 1

:error
echo.
echo エラーが発生しました。上に出ているメッセージを確認してください。
pause
exit /b 1
