<#
.SYNOPSIS
  Einrichtung unter Windows: virtuelle Umgebung, Pakete, Datenbank, fiktive Beispieldaten.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
  (Bypass gilt nur für diesen einen Aufruf, keine Systemeinstellung wird geändert.)

.PARAMETER VenvPath
  Ort der virtuellen Umgebung (Standard: .venv im Projektordner).
.PARAMETER SkipSampleData
  Keine fiktiven Beispieldaten importieren.
#>
param(
    [string]$VenvPath = ".venv",
    [switch]$SkipSampleData
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Invoke-Checked([string]$exe, [string[]]$arguments) {
    & $exe @arguments
    if ($LASTEXITCODE -ne 0) { throw "Fehlgeschlagen: $exe $($arguments -join ' ')" }
}

$python = Join-Path $VenvPath "Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Host "Erstelle virtuelle Umgebung in $VenvPath ..."
    if (Get-Command py -ErrorAction SilentlyContinue) {
        Invoke-Checked "py" @("-3.12", "-m", "venv", $VenvPath)
    } else {
        Invoke-Checked "python" @("-m", "venv", $VenvPath)
    }
}
Invoke-Checked $python @("-m", "pip", "install", "--quiet", "--upgrade", "pip")
Invoke-Checked $python @("-m", "pip", "install", "--quiet", "-e", ".[dev]")
Invoke-Checked $python @("-m", "transparenz", "init-db")
if (-not $SkipSampleData) {
    Invoke-Checked $python @("-m", "transparenz", "update", "--force")
}
Write-Host ""
Write-Host "Fertig. App starten mit:"
Write-Host "  $python -m streamlit run app\main.py"
