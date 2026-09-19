# 安装 / 回滚 CJK 换行补丁
# 用法：
#   powershell -ExecutionPolicy Bypass -File tools\dllpatch\install.ps1
#   powershell -ExecutionPolicy Bypass -File tools\dllpatch\install.ps1 -Restore
param([switch]$Restore)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$managed = "C:\Program Files (x86)\Steam\steamapps\common\The Drifter\TheDrifter_Data\Managed"
$backup = Join-Path $root "backup\managed\Assembly-CSharp-firstpass.dll"
$patched = Join-Path $PSScriptRoot "build\Assembly-CSharp-firstpass.patched.dll"
$helper = Join-Path $PSScriptRoot "build\CjkWrap.dll"

if (Get-Process -Name "TheDrifter*" -ErrorAction SilentlyContinue) {
    Write-Host "游戏正在运行，请先退出游戏再执行。" -ForegroundColor Red
    exit 1
}

if ($Restore) {
    Copy-Item $backup (Join-Path $managed "Assembly-CSharp-firstpass.dll") -Force
    Remove-Item (Join-Path $managed "CjkWrap.dll") -Force -ErrorAction SilentlyContinue
    Write-Host "已还原为原版换行（英文断行规则）。" -ForegroundColor Yellow
    exit 0
}

foreach ($f in @($backup, $patched, $helper)) {
    if (-not (Test-Path $f)) { Write-Host "缺少文件: $f" -ForegroundColor Red; exit 1 }
}

Copy-Item $helper (Join-Path $managed "CjkWrap.dll") -Force
Copy-Item $patched (Join-Path $managed "Assembly-CSharp-firstpass.dll") -Force
Write-Host "已安装中文换行补丁。原版备份在 backup\managed\。" -ForegroundColor Green
Write-Host "回滚：install.ps1 -Restore"
