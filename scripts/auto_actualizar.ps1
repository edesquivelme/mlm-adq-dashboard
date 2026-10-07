# auto_actualizar.ps1
# Corrida desatendida del ciclo diario. La lanza el Programador de tareas de Windows
# (ver scripts\registrar_tarea.ps1). Envuelve a actualizar_dashboard.ps1 con las
# guardias que en una corrida manual se hacen a ojo:
#   0. Sabado o domingo -> no corre (decision Edgar: solo dias habiles). Cubre el caso
#      de una corrida del viernes perdida que Windows dispara al prender la laptop el sabado.
#   1. Ya hubo deploy exitoso hoy -> no repetir. Cada deploy gasta 1 de las 200
#      versiones de Apps Script y la API no permite borrarlas.
#   2. Hay cambios sin commitear  -> no correr. El "git add ." del paso 3 los subiria
#      a medio hacer y se publicaria codigo sin validar.
#   3. Probe ADC (check_appscript.py --probe) -> si da 403 aborta antes de gastar
#      minutos de BigQuery. Reintenta si falla por red (laptop recien despierta).
#   4. actualizar_dashboard.ps1   -> genera, deploya, commit + push.
#   5. Verifica que el push subio y que el web app sigue en DOMAIN / USER_DEPLOYING.
# Cada corrida deja un log en logs\ (ignorado por git) y una notificacion de Windows.
#
# Uso:
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\auto_actualizar.ps1
#   ... -Force    corre aunque sea fin de semana o ya haya habido deploy exitoso hoy
#   ... -DryRun   solo guardias + probe + verify; no genera ni deploya
# Solo ASCII en este archivo: PowerShell 5.1 lee los .ps1 sin BOM como ANSI.

param([switch]$Force, [switch]$DryRun)

$ROOT  = Split-Path $PSScriptRoot -Parent
$PY    = "$ROOT\vEnv_Meli_Code1\Scripts\python.exe"
$CHECK = "$ROOT\scripts\check_appscript.py"
$LOGS  = "$ROOT\logs"
$STAMP = "$LOGS\.ultimo_deploy_ok"
$HOY   = Get-Date -Format "yyyy-MM-dd"
$T0    = Get-Date

New-Item -ItemType Directory -Force $LOGS | Out-Null
$LOG = "$LOGS\auto_$(Get-Date -Format 'yyyy-MM-dd_HHmm').log"

# Python escribe UTF-8; sin esto PowerShell decodifica su salida como OEM y el log sale roto.
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONUNBUFFERED = "1"
$env:PYTHONIOENCODING = "utf-8"

function Log([string]$msg) {
    $line = "[$(Get-Date -Format 'HH:mm:ss')] $msg"
    Add-Content -Path $LOG -Value $line -Encoding UTF8
    Write-Host $line
}

# Corre un ejecutable mandando stdout+stderr al log linea por linea. Devuelve el exit code.
function Invoke-Logged([string]$exe, [string[]]$argv) {
    & $exe @argv 2>&1 | ForEach-Object { Add-Content -Path $LOG -Value "$_" -Encoding UTF8 }
    return $LASTEXITCODE
}

function Notify([string]$title, [string]$msg) {
    try {
        [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
        $xml = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
        $nodes = $xml.GetElementsByTagName("text")
        $nodes.Item(0).AppendChild($xml.CreateTextNode($title)) | Out-Null
        $nodes.Item(1).AppendChild($xml.CreateTextNode($msg)) | Out-Null
        $aumid = '{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe'
        [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($aumid).Show([Windows.UI.Notifications.ToastNotification]::new($xml))
    } catch {
        Log "AVISO: no se pudo mostrar la notificacion de Windows: $($_.Exception.Message)"
    }
}

function Finish([int]$code, [string]$title, [string]$msg, [switch]$Quiet) {
    $min = [math]::Round(((Get-Date) - $T0).TotalMinutes, 1)
    Log "$title | $msg | $min min | exit $code"
    if (-not $Quiet) { Notify $title $msg }
    Get-ChildItem $LOGS -Filter "auto_*.log" |
        Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-60) } |
        Remove-Item -Force
    exit $code
}

Log "Inicio corrida automatica (Force=$Force DryRun=$DryRun) en $ROOT"

# 0. Solo dias habiles
if (-not $Force -and (Get-Date).DayOfWeek -in @('Saturday', 'Sunday')) {
    Finish 0 "Dashboard: fin de semana" "Hoy es $((Get-Date).DayOfWeek); la corrida automatica es solo de lunes a viernes." -Quiet
}

# 1. Ya hubo deploy exitoso hoy
if (-not $Force -and -not $DryRun -and (Test-Path $STAMP) -and ((Get-Content $STAMP -TotalCount 1) -eq $HOY)) {
    Finish 0 "Dashboard: ya actualizado hoy" "Hubo deploy exitoso hoy ($HOY); no se repite." -Quiet
}

# 2. Arbol de trabajo limpio
$dirty = @(git -C $ROOT status --porcelain)
if ($dirty.Count -gt 0) {
    $dirty | ForEach-Object { Log "  sin commitear: $_" }
    Finish 1 "Dashboard NO actualizado" "Hay $($dirty.Count) archivo(s) sin commitear en el repo. Commitea o descarta y corre actualizar_dashboard.ps1."
}

# 3. Probe ADC. Un 403 (exit 2) no se arregla esperando; un error de red si.
$probe = 1
foreach ($i in 1..3) {
    $probe = Invoke-Logged $PY @($CHECK, '--probe')
    if ($probe -eq 0 -or $probe -eq 2) { break }
    if ($i -lt 3) {
        Log "Probe fallo (exit $probe), posible red no lista. Reintento en 3 min ($i/3)."
        Start-Sleep -Seconds 180
    }
}
if ($probe -eq 2) {
    Finish 1 "Dashboard NO actualizado" "Credenciales ADC sin permisos de Apps Script (403). Hay que re-autenticar: los 2 comandos estan en el log."
}
if ($probe -ne 0) {
    Finish 1 "Dashboard NO actualizado" "No se pudo contactar a Google tras 3 intentos (exit $probe). Ver log."
}

# 4. Ciclo completo: genera -> deploya -> commit + push
if (-not $DryRun) {
    Log "Corriendo actualizar_dashboard.ps1 ..."
    $rc = Invoke-Logged "powershell.exe" @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', "$ROOT\actualizar_dashboard.ps1")
    if ($rc -ne 0) {
        $stage = if (Select-String -Path $LOG -Pattern '\[2/2\]' -Quiet) { "el deploy a Apps Script" } else { "la generacion (BigQuery)" }
        Finish 1 "Dashboard NO actualizado" "Fallo $stage (exit $rc). Ver $LOG"
    }
    Set-Content -Path $STAMP -Value $HOY -Encoding ASCII
}

# 5. Push y web app
$ahead = [int](git -C $ROOT rev-list --count origin/main..HEAD)
$verifyOut = @(& $PY $CHECK --verify 2>&1 | ForEach-Object { "$_" })
$verify = $LASTEXITCODE
$verifyOut | ForEach-Object { Add-Content -Path $LOG -Value $_ -Encoding UTF8 }
$version = ($verifyOut | Select-String 'VERSION=(\d+)' | Select-Object -First 1 | ForEach-Object { $_.Matches[0].Groups[1].Value })

if ($verify -ne 0) {
    Finish 1 "Dashboard: revisar acceso" "Web app v$version con config distinta a DOMAIN / USER_DEPLOYING (exit $verify). Parte del equipo podria no entrar. Ver log."
}
if ($ahead -gt 0) {
    Finish 1 "Dashboard publicado, GitHub no" "v$version publicada, pero quedan $ahead commit(s) sin subir a GitHub. Ver log."
}
if ($DryRun) {
    Finish 0 "Dashboard: prueba OK" "Guardias, credenciales y web app (v$version) en orden. No se genero ni publico nada."
}

# Corte de datos: Individuals Perf fija el corte del dashboard (alarma 90 del log de generacion)
$corte = ""
$m = Select-String -Path $LOG -Pattern 'Individuals Perf hasta \.+ (\d{4}-\d{2}-\d{2})', 'Fuentes alineadas: .* hasta (\d{4}-\d{2}-\d{2})' | Select-Object -First 1
if ($m) {
    $fecha = [datetime]::ParseExact($m.Matches[0].Groups[1].Value, 'yyyy-MM-dd', $null)
    $corte = " Pagados hasta $($fecha.ToString('yyyy-MM-dd')) (D-$(((Get-Date).Date - $fecha).Days))."
}
Finish 0 "Dashboard actualizado" "v$version publicada.$corte"
