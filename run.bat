@echo off
echo ====================================================
echo Starting Mafia42 Collection Journal (Full-Stack)
echo ====================================================
echo.
echo Application will be available at: http://127.0.0.1:8000
echo.
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
pause

