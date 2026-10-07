:; exec python3 "$(dirname "$0")/speaker.py" "$@" # Runs speaker.py on macOS and Linux (sh) and on Windows (cmd).
@echo off
rem On Windows, python3 is often the Microsoft Store placeholder, so use the py launcher.
where py >nul 2>nul
if %errorlevel%==0 (py -3 "%~dp0speaker.py" %*) else (python "%~dp0speaker.py" %*)
