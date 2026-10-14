@echo off
setlocal
rem ------------------------------------------------------------------
rem  Builds DeSSaveEditor.exe (single file, no console window) from gui.py
rem  Output: dist\DeSSaveEditor.exe
rem ------------------------------------------------------------------
cd /d "%~dp0"

rem --- find Python ---------------------------------------------------
set "PY="
where python >nul 2>nul && set "PY=python"
if not defined PY (
    where py >nul 2>nul && set "PY=py -3"
)
if not defined PY (
    echo [ERROR] Python was not found. Install Python 3 and tick "Add python.exe to PATH".
    pause
    exit /b 1
)
echo Using: %PY%
%PY% --version

rem --- check the project files ---------------------------------------
if not exist "gui.py"  ( echo [ERROR] gui.py not found next to build.bat & pause & exit /b 1 )
if not exist "main.py" ( echo [ERROR] main.py not found next to build.bat & pause & exit /b 1 )
if not exist "json\"   ( echo [ERROR] json folder not found next to build.bat & pause & exit /b 1 )

rem --- install / update PyInstaller -----------------------------------
echo.
echo Installing PyInstaller...
%PY% -m pip install --upgrade pyinstaller
if errorlevel 1 (
    echo [ERROR] Could not install PyInstaller.
    pause
    exit /b 1
)

rem --- clean old build -----------------------------------------------
if exist "build" rmdir /s /q "build"
if exist "dist\DeSSaveEditor.exe" del /q "dist\DeSSaveEditor.exe"
if exist "DeSSaveEditor.spec" del /q "DeSSaveEditor.spec"

rem --- build ---------------------------------------------------------
echo.
echo Building...
%PY% -m PyInstaller --noconfirm --clean --onefile --windowed ^
    --name DeSSaveEditor ^
    --add-data "json;json" ^
    gui.py
if errorlevel 1 (
    echo.
    echo [ERROR] Build failed - see the messages above.
    pause
    exit /b 1
)

rem --- tidy up -------------------------------------------------------
if exist "build" rmdir /s /q "build"
if exist "DeSSaveEditor.spec" del /q "DeSSaveEditor.spec"

echo.
echo Done: %CD%\dist\DeSSaveEditor.exe
pause
endlocal
