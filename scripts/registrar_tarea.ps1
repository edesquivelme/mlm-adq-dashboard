# registrar_tarea.ps1
# Crea (o reemplaza) la tarea programada de Windows que corre scripts\auto_actualizar.ps1
# de lunes a viernes a la hora indicada (hora local del equipo = CDMX).
#
# 10:30 por defecto: Individuals Perf, que fija el corte del dashboard, se reconstruye ~09:56.
# Antes de esa carga el dashboard sale con datos hasta D-2; despues, hasta D-1 (History 96).
#
# Corre como el usuario actual y solo con sesion iniciada (aunque este bloqueada): el ADC de
# gcloud y las credenciales de git viven en su perfil, y asi Windows no guarda contrasena.
# Si a esa hora la laptop esta apagada o dormida, corre en cuanto vuelva a estar disponible.
#
# Uso (desde la raiz del proyecto):
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\registrar_tarea.ps1              # L-V 10:30
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\registrar_tarea.ps1 -Hora 11:00  # otra hora
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\registrar_tarea.ps1 -Quitar      # borrarla
# Solo ASCII en este archivo: PowerShell 5.1 lee los .ps1 sin BOM como ANSI.

param([string]$Hora = "10:30", [switch]$Quitar)

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
