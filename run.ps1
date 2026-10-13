Write-Host "====================================================" -ForegroundColor Cyan
Write-Host " Starting Mafia42 Collection Journal (Full-Stack)" -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Application is opening at: http://127.0.0.1:8000" -ForegroundColor Green
Write-Host ""

Start-Process "http://127.0.0.1:8000"
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload

