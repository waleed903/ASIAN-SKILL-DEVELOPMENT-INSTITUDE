@echo off
title ASDI Portal - Push to GitHub
cd /d "%~dp0"
echo ===================================================
echo      ASDI Portal - Pushing Updates to GitHub
echo ===================================================
echo.
git status
echo.
echo Pushing committed updates to GitHub (main)...
git push origin main
echo.
if %ERRORLEVEL% EQU 0 (
    echo ===================================================
    echo    SUCCESS! Sabhi files GitHub par push ho gayin!
    echo ===================================================
) else (
    echo [ERROR] Push fail hua. Agar GitHub browser window khuli hai to "Authorize" ya "Sign In" par click karein.
)
echo.
pause
