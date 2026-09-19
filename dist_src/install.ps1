<#
  The Drifter 简体中文汉化 —— 安装 / 卸载
  由 安装.bat / 卸载.bat 调用，一般不需要手动运行。
#>
param([switch]$Uninstall, [string]$GamePath)

$ErrorActionPreference = "Stop"
$here = $PSScriptRoot
$patch = Join-Path $here "patch"

function Info($m) { Write-Host $m }
function Ok($m)   { Write-Host $m -ForegroundColor Green }
function Warn($m) { Write-Host $m -ForegroundColor Yellow }
function Err($m)  { Write-Host $m -ForegroundColor Red }

function Fail($m) {
    Err ""
    Err "  $m"
    Err ""
    Read-Host "按回车键退出"
    exit 1
}

# ---------- 找游戏目录 ----------
function Test-Game($dir) {
    # 目录可能在不存在的盘上，Join-Path 会抛异常，这里统一挡掉
    if ([string]::IsNullOrWhiteSpace($dir)) { return $false }
    try { return (Test-Path -LiteralPath ([IO.Path]::Combine($dir, "TheDrifter.exe"))) } catch { return $false }
}

function Find-Game {
    $hits = @()

    # 1) Steam 主库 + 所有附加库（libraryfolders.vdf）
    $steam = $null
    foreach ($k in @("HKLM:\SOFTWARE\WOW6432Node\Valve\Steam", "HKLM:\SOFTWARE\Valve\Steam", "HKCU:\SOFTWARE\Valve\Steam")) {
        try { $v = (Get-ItemProperty $k -ErrorAction Stop); if ($v.InstallPath) { $steam = $v.InstallPath; break } elseif ($v.SteamPath) { $steam = $v.SteamPath; break } } catch {}
    }
    $libs = @()
    if ($steam) {
        $libs += $steam
        $vdf = Join-Path $steam "steamapps\libraryfolders.vdf"
        if (Test-Path $vdf) {
            foreach ($m in [regex]::Matches((Get-Content $vdf -Raw), '"path"\s+"([^"]+)"')) {
                $libs += $m.Groups[1].Value -replace '\\\\', '\'
            }
        }
    }
    foreach ($l in $libs) {
        $p = [IO.Path]::Combine($l, "steamapps\common\The Drifter")
        if (Test-Game $p) { $hits += $p }
    }

    # 2) 每个盘符下的常见位置
    $roots = (Get-PSDrive -PSProvider FileSystem -ErrorAction SilentlyContinue | ForEach-Object { $_.Root })
    foreach ($r in $roots) {
        foreach ($sub in @("Program Files (x86)\Steam\steamapps\common\The Drifter",
                           "Steam\steamapps\common\The Drifter",
                           "SteamLibrary\steamapps\common\The Drifter",
                           "Games\The Drifter", "GOG Games\The Drifter", "The Drifter")) {
            $p = [IO.Path]::Combine($r, $sub)
            if (Test-Game $p) { $hits += $p }
        }
    }
    if (Test-Game "$env:USERPROFILE\Desktop\The Drifter") { $hits += "$env:USERPROFILE\Desktop\The Drifter" }

    # 3) 跟本脚本放在一起（整个文件夹被丢进游戏目录的情况）
    foreach ($d in @($here, (Split-Path $here -Parent))) {
        if (Test-Game $d) { $hits += $d }
    }

    $hits | Select-Object -Unique | Select-Object -First 1
}

if (-not $GamePath) { $GamePath = Find-Game }

if (-not (Test-Game $GamePath)) {
    Err ""
    Err "  没有自动找到游戏目录。"
    Info ""
    Info "  两个办法："
    Info "    1. 把整个汉化文件夹复制进游戏目录（TheDrifter.exe 所在的那层），再运行一次"
    Info "    2. 把游戏目录拖到这个窗口里，然后按回车"
    Info ""
    $GamePath = (Read-Host "  游戏目录").Trim('"', ' ')
    if (-not (Test-Game $GamePath)) { Fail "这个目录里没有 TheDrifter.exe，安装中止。" }
}

Info ""
Info "  游戏目录: $GamePath"

if (Get-Process -Name "TheDrifter*" -ErrorAction SilentlyContinue) { Fail "游戏正在运行，请先完全退出游戏再安装。" }

# ---------- 权限不够就以管理员身份重来 ----------
function Test-Writable($dir) {
    try {
        $f = [IO.Path]::Combine($dir, ".drifter_write_test")
        [IO.File]::WriteAllText($f, "x"); [IO.File]::Delete($f); return $true
    } catch { return $false }
}

if (-not (Test-Writable $GamePath)) {
    $isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    if ($isAdmin) { Fail "游戏目录不可写，请检查文件是否被设为只读。" }
    Warn "  游戏装在受保护的目录，需要管理员权限，正在重新启动..."
    $a = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$PSCommandPath`"", "-GamePath", "`"$GamePath`"")
    if ($Uninstall) { $a += "-Uninstall" }
    try { Start-Process powershell -Verb RunAs -ArgumentList $a } catch { Fail "提权被取消。请右键「安装.bat」->「以管理员身份运行」。" }
    exit 0
}

$data      = Join-Path $GamePath "TheDrifter_Data"
$managed   = Join-Path $data "Managed"
$backupDir = Join-Path $GamePath "_汉化备份"

$targets = @(
    @{ Name = "translation.csv";              Path = Join-Path $GamePath "translation.csv" }
    @{ Name = "sharedassets1.assets";         Path = Join-Path $data "sharedassets1.assets" }
    @{ Name = "Assembly-CSharp-firstpass.dll"; Path = Join-Path $managed "Assembly-CSharp-firstpass.dll" }
    @{ Name = "CjkWrap.dll";                  Path = Join-Path $managed "CjkWrap.dll" }
)

# ---------- 卸载 ----------
if ($Uninstall) {
    if (-not (Test-Path $backupDir)) { Fail "找不到备份文件夹 _汉化备份，无法还原。可以用 Steam「验证游戏文件完整性」恢复原版。" }
    foreach ($t in $targets) {
        $b = Join-Path $backupDir $t.Name
        if (Test-Path $b) { Copy-Item $b $t.Path -Force; Info "  还原 $($t.Name)" }
        elseif ($t.Name -eq "CjkWrap.dll") { Remove-Item $t.Path -Force -ErrorAction SilentlyContinue }
    }
    Remove-Item (Join-Path $GamePath "translation.csv") -Force -ErrorAction SilentlyContinue
    Remove-Item (Join-Path $managed "CjkWrap.dll") -Force -ErrorAction SilentlyContinue
    Ok ""
    Ok "  已还原为英文原版。"
    Info ""
    Read-Host "按回车键退出"
    exit 0
}

# ---------- 安装 ----------
foreach ($f in @("translation.csv", "CjkWrap.dll", "assets.delta", "firstpass.delta", "BinDelta.exe")) {
    if (-not (Test-Path (Join-Path $patch $f))) { Fail "汉化包不完整，缺少 patch\$f" }
}

# 备份（只备份一次，避免把已汉化的文件当成原版覆盖掉备份）
if (-not (Test-Path $backupDir)) { New-Item -ItemType Directory $backupDir | Out-Null }
foreach ($t in $targets) {
    $b = Join-Path $backupDir $t.Name
    if ((Test-Path $t.Path) -and -not (Test-Path $b)) { Copy-Item $t.Path $b -Force }
}
Info "  原版文件已备份到 _汉化备份"

$bin = Join-Path $patch "BinDelta.exe"

# 临时文件直接生成在目标目录，避免跨盘移动和系统 TEMP 短路径的怪问题
Info "  正在打字体补丁（约 10 秒）..."
$tmpA = Join-Path $data "sharedassets1.assets.new"
& $bin apply (Join-Path $backupDir "sharedassets1.assets") (Join-Path $patch "assets.delta") $tmpA
if ($LASTEXITCODE -ne 0) { Remove-Item -LiteralPath $tmpA -Force -ErrorAction SilentlyContinue; Fail "字体补丁失败。多半是游戏版本与汉化包不一致，请到发布页确认版本。" }

Info "  正在打换行补丁..."
$tmpF = Join-Path $managed "Assembly-CSharp-firstpass.dll.new"
& $bin apply (Join-Path $backupDir "Assembly-CSharp-firstpass.dll") (Join-Path $patch "firstpass.delta") $tmpF
if ($LASTEXITCODE -ne 0) { Remove-Item -LiteralPath $tmpA, $tmpF -Force -ErrorAction SilentlyContinue; Fail "换行补丁失败。多半是游戏版本与汉化包不一致，请到发布页确认版本。" }

Move-Item -LiteralPath $tmpA -Destination (Join-Path $data "sharedassets1.assets") -Force
Move-Item -LiteralPath $tmpF -Destination (Join-Path $managed "Assembly-CSharp-firstpass.dll") -Force
Copy-Item -LiteralPath (Join-Path $patch "CjkWrap.dll") -Destination (Join-Path $managed "CjkWrap.dll") -Force
Copy-Item -LiteralPath (Join-Path $patch "translation.csv") -Destination (Join-Path $GamePath "translation.csv") -Force

Ok ""
Ok "  安装完成！"
Info ""
Info "  启动游戏后，如果显示的还是英文："
Info "    Options -> Language -> 选择 简体中文"
Info ""
Info "  想还原英文版：运行 卸载.bat"
Info "  注意：Steam 更新或「验证游戏文件完整性」会覆盖补丁，重新运行 安装.bat 即可。"
Info ""
Read-Host "按回车键退出"
