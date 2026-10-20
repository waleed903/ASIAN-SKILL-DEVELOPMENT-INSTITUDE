@echo off
title ASDI Student Mobile Portal
color 0B
cls
echo ==============================================================
echo           ASDI STUDENT PORTAL (PWA MOBILE APP)
echo ==============================================================
echo.
echo Starting Portal Server...
echo.
python -c "import socket; s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(('8.8.8.8', 80)); print('>> Apne mobile phone par ye link kholein: http://' + s.getsockname()[0] + ':5000'); s.close()"
echo >> Ya apne computer par kholein:              http://localhost:5000
echo.
echo Note: Mobile aur computer aik hi Wi-Fi network par hone chahiye.
echo Server band karne ke liye Ctrl + C dabayein.
echo ==============================================================
echo.
python app.py
pause
