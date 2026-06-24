# Kuri IA - Script de Preparacao de Assets Pesados
# Uso: powershell -ExecutionPolicy Bypass -File scripts\download_assets.ps1

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$ModelsDir   = Join-Path $ProjectRoot "models\whisper-base"
$Live2DDir   = Join-Path $ProjectRoot "assets\live2d\kuri_model"
$AvatarDir   = Join-Path $ProjectRoot "InterfaceAva"

Write-Host "=== Kuri IA - Preparacao de Assets Pesados ===" -ForegroundColor Cyan
Write-Host ""

# 1. Whisper model
Write-Host "[1/3] Modelo Whisper (whisper-base)..." -ForegroundColor Yellow
if (-not (Test-Path (Join-Path $ModelsDir "model.bin"))) {
    Write-Host "   Modelo ainda nao existe localmente." -ForegroundColor DarkYellow
    Write-Host "   Ele sera baixado automaticamente na primeira execucao (faster-whisper)." -ForegroundColor Gray
} else {
    Write-Host "   Modelo ja presente." -ForegroundColor Green
}

# 2. Live2D
Write-Host ""
Write-Host "[2/3] Arquivos Live2D..." -ForegroundColor Yellow
$neededLive2D = @(
    (Join-Path $Live2DDir "kuri.moc3"),
    (Join-Path $Live2DDir "textures\texture_00.png")
)
$missing = $false
foreach ($f in $neededLive2D) {
    if (-not (Test-Path $f)) { $missing = $true; Write-Host "   Faltando: $f" -ForegroundColor Red }
}
if ($missing) {
    Write-Host "   Coloque os arquivos Live2D manualmente em: $Live2DDir" -ForegroundColor Gray
} else {
    Write-Host "   Arquivos Live2D OK!" -ForegroundColor Green
}

# 3. Avatar videos
Write-Host ""
Write-Host "[3/3] Videos de Avatar..." -ForegroundColor Yellow
if (-not (Test-Path $AvatarDir)) { New-Item -ItemType Directory -Path $AvatarDir -Force | Out-Null }

$videos = Get-ChildItem -Path $AvatarDir -Filter "*.mp4" -ErrorAction SilentlyContinue
if ($videos.Count -eq 0) {
    Write-Host "   Nenhum video encontrado." -ForegroundColor Red
    Write-Host "   Voce precisa dos 5 videos em $AvatarDir (fornecidos pelo autor ou backup anterior)." -ForegroundColor Gray
} else {
    Write-Host "   Encontrados $($videos.Count) video(s)." -ForegroundColor Green
}

Write-Host ""
Write-Host "=== Fase 0 de Higiene concluida ===" -ForegroundColor Green
Write-Host "Execute o Kuri. O Whisper baixa sozinho. Os demais assets devem ser restaurados manualmente." -ForegroundColor Cyan