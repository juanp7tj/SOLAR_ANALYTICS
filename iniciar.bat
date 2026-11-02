@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo  SOLAR ANALYTICS - Inicializacao local
echo  Inteligencia que transforma energia em economia.
echo ============================================================

if not exist .venv\Scripts\python.exe (
  echo [1/4] Criando ambiente virtual Python...
  py -3 -m venv .venv
  if errorlevel 1 goto :error
)

echo [2/4] Instalando/atualizando dependencias Python...
.venv\Scripts\python.exe -m pip install --upgrade pip==26.2.2
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto :error

where npm >nul 2>nul
if errorlevel 1 (
  echo Node.js 20.19+ ou 22.12+ e npm sao necessarios. Atualize o Node.js e tente novamente.
  goto :error
)

echo [3/4] Instalando dependencias da interface...
call npm install
if errorlevel 1 goto :error

echo [4/4] Compilando a interface...
call npm run build
if errorlevel 1 goto :error

if not exist .env copy .env.example .env >nul
if not exist data mkdir data
if not exist backups mkdir backups
icacls "data" /inheritance:r /grant:r "%USERDOMAIN%\%USERNAME%:(OI)(CI)F" /T /C >nul 2>nul
if errorlevel 1 echo [AVISO] ACL de data nao foi alterada; confira permissões do diretório.
icacls "backups" /inheritance:r /grant:r "%USERDOMAIN%\%USERNAME%:(OI)(CI)F" /T /C >nul 2>nul
if errorlevel 1 echo [AVISO] ACL de backups nao foi alterada; confira permissões do diretório.

echo.
echo Aplicacao disponivel em http://127.0.0.1:8000
start "SOLAR ANALYTICS" http://127.0.0.1:8000
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
if errorlevel 1 goto :error
exit /b 0

:error
echo.
echo A inicializacao encontrou um erro. Confira a mensagem acima e o README.md.
pause
exit /b 1
