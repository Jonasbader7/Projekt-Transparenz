[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\pythonw.exe'
$runnerPath = Join-Path $PSScriptRoot 'autonomous_update.py'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Projekt-Python fehlt.' }
$taskName = 'ProjektTransparenz-DailyDataUpdate'
$existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existing -and $existing.Description -ne 'Projekt Transparenz: validierte lokale Datenupdates') {
    throw 'Gleichnamiger fremder Task vorhanden; keine Ueberschreibung.'
}
$account = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$action = New-ScheduledTaskAction -Execute $pythonPath -Argument ('"' + $runnerPath + '"') -WorkingDirectory $projectRoot
$daily = New-ScheduledTaskTrigger -Daily -At '09:00'
$logon = New-ScheduledTaskTrigger -AtLogOn -User $account
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 10) -RestartCount 2 -RestartInterval (New-TimeSpan -Minutes 30) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$principal = New-ScheduledTaskPrincipal -UserId $account -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger @($daily, $logon) -Settings $settings -Principal $principal -Description 'Projekt Transparenz: validierte lokale Datenupdates' -Force | Out-Null
Get-ScheduledTask -TaskName $taskName | Select-Object TaskName, State
