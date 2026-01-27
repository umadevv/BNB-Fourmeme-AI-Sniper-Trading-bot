@echo off
setlocal
cd /d "%~dp0"

REM Self-contained venv launcher (like your example)
if not exist ".venv\Scripts\python.exe" (
  echo Creating .venv ...
  py -3.11 -m venv .venv
  if errorlevel 1 python -m venv .venv
)

".venv\Scripts\python.exe" -m ensurepip --upgrade >nul 2>&1

REM This repo uses pyproject.toml; install deps by installing the package
".venv\Scripts\python.exe" -m pip install -q -e .

REM Launch GUI (pass-through args are ignored by Typer if none expected)
".venv\Scripts\python.exe" -m polymarket_copybot gui %*
