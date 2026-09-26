$ErrorActionPreference = "Stop"
$ImageName = "seclab-op-web-tools:1.0"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Write-Host "Building $ImageName from $ScriptDir ..." -ForegroundColor Cyan
docker build -t $ImageName $ScriptDir
if ($LASTEXITCODE -ne 0) { throw "docker build failed (exit $LASTEXITCODE)" }
Write-Host "Done. Quick test:" -ForegroundColor Green
Write-Host "  docker run --rm -p 15901:5901 $ImageName" -ForegroundColor Yellow
Write-Host "  then open a VNC viewer at localhost:15901 (password: 123456)" -ForegroundColor Yellow
