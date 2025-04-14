@echo off
title ابتسامة المشاهير لتجميل الاسنان
echo جاري تشغيل نظام إدارة عيادة ابتسامة المشاهير لتجميل الاسنان...
echo.
cd /d "%~dp0"

:: انتظار 3 ثوانٍ ثم فتح المتصفح
start "" cmd /c "timeout /t 3 /nobreak && start http://127.0.0.1:5000"

:: تشغيل التطبيق
python app.py
pause
