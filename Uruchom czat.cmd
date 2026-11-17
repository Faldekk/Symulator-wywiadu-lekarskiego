@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    py -m venv .venv
    if errorlevel 1 goto error
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 goto error
)
where ollama >nul 2>&1
if errorlevel 1 goto error
ollama list >nul 2>&1
if errorlevel 1 start "" /b ollama serve
echo Otworz w przegladarce: http://127.0.0.1:8000/
echo Zostaw to okno otwarte podczas rozmowy.
".venv\Scripts\python.exe" -B -m uvicorn backend.main.app:app --host 127.0.0.1 --port 8000
if not errorlevel 1 exit /b 0
:error
echo Sprawdz komunikat powyzej. Jesli czat juz dziala, otworz http://127.0.0.1:8000/
pause
exit /b 1
