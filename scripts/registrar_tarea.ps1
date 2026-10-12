# registrar_tarea.ps1
# Crea (o reemplaza) la tarea programada de Windows que corre scripts\auto_actualizar.ps1
# de lunes a viernes a la hora indicada (hora local del equipo = CDMX).
#
# 09:00 por defecto (decision Edgar 12-Oct-2026: el equipo necesita el dato antes de las 10).
# Costo: Individuals Perf, que fija el corte de los conteos, se reconstruye ~09:55-10:20, asi
# que a las 9:00 los conteos salen hasta D-2 (a las 10:30 salian hasta D-1). Los ratios no
# cambian: ya iban a D-2 por el corte comun. Para volver a D-1: -Hora 10:30 (History 100).
#
# Corre como el usuario actual y solo con sesion iniciada (aunque este bloqueada): el ADC de
# gcloud y las credenciales de git viven en su perfil, y asi Windows no guarda contrasena.
# Si a esa hora la laptop esta apagada o dormida, corre en cuanto vuelva a estar disponible.
#
# Uso (desde la raiz del proyecto):
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\registrar_tarea.ps1              # L-V 09:00
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\registrar_tarea.ps1 -Hora 11:00  # otra hora
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\registrar_tarea.ps1 -Quitar      # borrarla
# Solo ASCII en este archivo: PowerShell 5.1 lee los .ps1 sin BOM como ANSI.

param([string]$Hora = "09:00", [switch]$Quitar)

$DIAS   = @("Monday", "Tuesday", "Wednesday", "Thursday", "Friday")

$NOMBRE = "MLM ADQ Dashboard - actualizacion diaria"
$ROOT   = Split-Path $PSScriptRoot -Parent

if ($Quitar) {
    Unregister-ScheduledTask -TaskName $NOMBRE -Confirm:$false
    Write-Host "Tarea '$NOMBRE' eliminada."
    exit 0
}

$actionArgs = @{
    Execute          = "powershell.exe"
    Argument         = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$ROOT\scripts\auto_actualizar.ps1`""
    WorkingDirectory = $ROOT
}
$settingsArgs = @{
    StartWhenAvailable         = $true
    WakeToRun                  = $true
    AllowStartIfOnBatteries    = $true
    DontStopIfGoingOnBatteries = $true
    ExecutionTimeLimit         = (New-TimeSpan -Hours 2)
    MultipleInstances          = "IgnoreNew"
}
$taskArgs = @{
    TaskName    = $NOMBRE
    Action      = New-ScheduledTaskAction @actionArgs
    Trigger     = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $DIAS -At $Hora
    Settings    = New-ScheduledTaskSettingsSet @settingsArgs
    Principal   = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited
    Description = "Genera dashboard_v1.html (BigQuery), lo publica en Apps Script y sincroniza GitHub. Logs en $ROOT\logs. Ver scripts\auto_actualizar.ps1."
    Force       = $true
}
Register-ScheduledTask @taskArgs | Out-Null

$info = Get-ScheduledTaskInfo -TaskName $NOMBRE
Write-Host "Tarea registrada: $NOMBRE (lunes a viernes $Hora)"
Write-Host "  Proxima corrida: $($info.NextRunTime.ToString('yyyy-MM-dd HH:mm'))"
Write-Host "  Logs: $ROOT\logs"
