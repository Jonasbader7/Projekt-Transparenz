<#
.SYNOPSIS
  Startet die Streamlit-App (http://localhost:8501).

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\start.ps1
#>
param([string]$VenvPath = ".venv", [int]$Port = 8501)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
$python = Join-Path $VenvPath "Scripts\python.exe"
if (-not (Test-Path $python)) { throw "Keine Umgebung gefunden. Zuerst scripts\setup.ps1 ausführen." }
& $python -m streamlit run app\main.py --server.port $Port
