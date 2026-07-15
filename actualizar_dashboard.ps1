# actualizar_dashboard.ps1
# Flujo completo: genera dashboard_v1.html, lo sube a Apps Script y sincroniza a GitHub.
# Uso: .\actualizar_dashboard.ps1 (desde la raiz del proyecto)

$ROOT = $PSScriptRoot
$VENV = "$ROOT\vEnv_Meli_Code1\Scripts\python.exe"
$URL  = "https://script.google.com/a/macros/mercadolibre.com.mx/s/AKfycbxHzvNnIYbSphnHxh2kzAzUdE1Edpiljz1x5GiBCstbY3SXnsABKUtp_2cnhHUrVTwP/exec"

if (-not (Test-Path $VENV)) {
    Write-Host "ERROR: venv no encontrado en $VENV" -ForegroundColor Red
    Write-Host "Corre primero: python -m venv vEnv_Meli_Code1 && .\vEnv_Meli_Code1\Scripts\pip install -r requirements.txt"
    exit 1
}

Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  MLM ADQ N+R Dashboard — Actualizar  " -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# Paso 1 — Generar HTML
Write-Host "[1/2] Generando dashboard_v1.html..." -ForegroundColor Yellow
$t1 = Get-Date
& $VENV "$ROOT\src\gen_dashboard_v1.py"
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR en gen_dashboard_v1.py (exit $LASTEXITCODE)" -ForegroundColor Red
    exit $LASTEXITCODE
}
$dur1 = [math]::Round(((Get-Date) - $t1).TotalSeconds)
Write-Host "  OK — generado en $dur1s" -ForegroundColor Green

# Paso 2 — Deploy
Write-Host ""
Write-Host "[2/2] Subiendo a Apps Script..." -ForegroundColor Yellow
$t2 = Get-Date
& $VENV "$ROOT\src\deploy_appscript_v1.py"
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR en deploy_appscript_v1.py (exit $LASTEXITCODE)" -ForegroundColor Red
    exit $LASTEXITCODE
}
$dur2 = [math]::Round(((Get-Date) - $t2).TotalSeconds)
Write-Host "  OK — deployado en $dur2s" -ForegroundColor Green

# Paso 3 — Sincronizar a GitHub
Write-Host ""
Write-Host "[3/3] Sincronizando a GitHub..." -ForegroundColor Yellow
$fecha = Get-Date -Format "yyyy-MM-dd"
git -C $ROOT add .
git -C $ROOT commit -m "Actualizacion dashboard $fecha"
if ($LASTEXITCODE -ne 0) {
    Write-Host "  AVISO: nada nuevo que commitear o error en commit" -ForegroundColor Yellow
} else {
    git -C $ROOT push origin main
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ERROR en git push — verifica autenticacion GitHub" -ForegroundColor Red
    } else {
        Write-Host "  OK — GitHub sincronizado" -ForegroundColor Green
    }
}

$total = [math]::Round(((Get-Date) - $t1).TotalSeconds)
Write-Host ""
Write-Host "======================================" -ForegroundColor Green
Write-Host "  LISTO — Total: $total segundos" -ForegroundColor Green
Write-Host "  $URL" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Green
Write-Host ""
