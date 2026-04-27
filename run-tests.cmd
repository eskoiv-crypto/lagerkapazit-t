@echo off
REM ============================================================
REM NH5 Dashboard — Test-Runner für CMD
REM Sorgt dafür dass Node aus winget-User-Scope auch in CMD findbar ist.
REM Aufruf:  run-tests.cmd                (alle Tests)
REM          run-tests.cmd headed         (mit sichtbarem Browser)
REM          run-tests.cmd ui             (interaktiver Mode)
REM          run-tests.cmd report         (HTML-Report öffnen)
REM ============================================================

REM Node aus winget-User-Install zu PATH hinzufuegen
set "NODE_DIR=%LOCALAPPDATA%\Microsoft\WinGet\Packages\OpenJS.NodeJS.LTS_Microsoft.Winget.Source_8wekyb3d8bbwe\node-v24.15.0-win-x64"
if exist "%NODE_DIR%\node.exe" (
    set "PATH=%NODE_DIR%;%PATH%"
) else (
    echo [WARN] Node nicht im erwarteten Pfad gefunden: %NODE_DIR%
    echo        Falls Node anders installiert ist, einfach normal "npm test" nutzen.
)

REM Ins Projekt-Verzeichnis wechseln (Skript-Ort)
cd /d "%~dp0"

REM Default: alle Tests
if "%1"=="" (
    npm test
    goto :end
)
if /I "%1"=="headed" (
    npm run test:headed
    goto :end
)
if /I "%1"=="ui" (
    npm run test:ui
    goto :end
)
if /I "%1"=="report" (
    npm run test:report
    goto :end
)

echo Unbekanntes Argument: %1
echo Verfuegbare Modi: headed, ui, report  (oder kein Argument fuer Default)

:end
