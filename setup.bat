@echo off
title NEBL Fetch Server - Setup
echo ========================================
echo   NEBL Fetch Server - Installing
echo ========================================
echo.
echo Installing Python dependencies...
echo.
pip install flask requests beautifulsoup4 lxml gunicorn
echo.
echo ========================================
echo   Installation Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Run: python fetch_server.py
echo 2. Open browser: http://localhost:5000
echo.
pause
