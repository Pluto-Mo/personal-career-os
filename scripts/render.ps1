# render.ps1 — 简历 HTML → PDF + PNG，并校验「一页纸」硬约束
#
# 用法:
#   pwsh scripts/render.ps1 -Html template/resume.html
#   pwsh scripts/render.ps1 -Html "applications/2026-07-05-某公司-某岗位/resume.html" -Name "城市-学校-姓名-专业-年级"
#
# 参数:
#   -Html     输入的 HTML 文件（必填）
#   -OutDir   输出目录（默认与 HTML 同目录）
#   -Name     输出文件基名（默认与 HTML 同名；投递时按「城市-学校-姓名-专业-年级」命名）
#   -MaxPages 页数上限（默认 1，超出则退出码 1）
#
# 依赖: Microsoft Edge（Windows 自带），无需安装任何东西。

param(
    [Parameter(Mandatory = $true)][string]$Html,
    [string]$OutDir,
    [string]$Name,
    [int]$MaxPages = 1
)

$ErrorActionPreference = 'Stop'

# ── 定位输入输出 ──────────────────────────────────────────────
$htmlPath = (Resolve-Path -LiteralPath $Html).Path
if (-not $OutDir) { $OutDir = Split-Path -Parent $htmlPath }
if (-not (Test-Path -LiteralPath $OutDir)) { New-Item -ItemType Directory -Force -Path $OutDir | Out-Null }
$OutDir = (Resolve-Path -LiteralPath $OutDir).Path
if (-not $Name) { $Name = [IO.Path]::GetFileNameWithoutExtension($htmlPath) }

$pdfPath = Join-Path $OutDir "$Name.pdf"
$pngPath = Join-Path $OutDir "$Name.png"
$fileUrl = ([Uri]$htmlPath).AbsoluteUri

# ── 定位 Edge ────────────────────────────────────────────────
$edgeCandidates = @(
    (Join-Path ${env:ProgramFiles(x86)} 'Microsoft\Edge\Application\msedge.exe'),
    (Join-Path $env:ProgramFiles       'Microsoft\Edge\Application\msedge.exe')
)
$edge = $edgeCandidates | Where-Object { $_ -and (Test-Path -LiteralPath $_) } | Select-Object -First 1
if (-not $edge) { throw '未找到 Microsoft Edge（msedge.exe），无法渲染。' }

# 独立的临时浏览器配置目录，避免与正在运行的 Edge 冲突
$tmpProfile = Join-Path $env:TEMP 'career-os-edge-profile'

# Start-Process 不会自动为含空格的参数加引号（本项目路径含空格），统一手动处理
function Quote-Arg([string]$a) { if ($a -match '\s') { "`"$a`"" } else { $a } }

$baseArgs = @(
    # 注意：本机 Edge 用 --headless=new 会静默失败（exit 0 但不产出文件），必须用 --headless
    '--headless', '--disable-gpu', '--hide-scrollbars',
    (Quote-Arg "--user-data-dir=$tmpProfile"),
    '--no-first-run', '--no-default-browser-check'
)

# ── 渲染 PDF ────────────────────────────────────────────────
foreach ($f in @($pdfPath, $pngPath)) {
    if (Test-Path -LiteralPath $f) { Remove-Item -LiteralPath $f -Force }
}
Start-Process -FilePath $edge -Wait -WindowStyle Hidden -ArgumentList ($baseArgs + @(
    '--no-pdf-header-footer', (Quote-Arg "--print-to-pdf=$pdfPath"), (Quote-Arg $fileUrl)
))
if (-not (Test-Path -LiteralPath $pdfPath)) { throw 'PDF 渲染失败（未生成文件）。' }

# ── 渲染 PNG（A4 比例，2 倍清晰度，适合手机端/微信发送） ────────
Start-Process -FilePath $edge -Wait -WindowStyle Hidden -ArgumentList ($baseArgs + @(
    (Quote-Arg "--screenshot=$pngPath"), '--window-size=793,1123', '--force-device-scale-factor=2', (Quote-Arg "$fileUrl`?clean=1")
))
if (-not (Test-Path -LiteralPath $pngPath)) { throw 'PNG 渲染失败（未生成文件）。' }

# ── 校验页数（一页纸硬约束） ─────────────────────────────────
$raw = [Text.Encoding]::GetEncoding('ISO-8859-1').GetString([IO.File]::ReadAllBytes($pdfPath))
$pages = [regex]::Matches($raw, '/Type\s*/Page(?![a-zA-Z])').Count
if ($pages -le 0) {
    $counts = [regex]::Matches($raw, '/Count\s+(\d+)') | ForEach-Object { [int]$_.Groups[1].Value }
    if ($counts) { $pages = ($counts | Measure-Object -Maximum).Maximum }
}

Write-Host "PDF : $pdfPath"
Write-Host "PNG : $pngPath"
Write-Host "页数: $pages"

if ($pages -lt 1) {
    Write-Warning '无法解析 PDF 页数，请人工打开确认。'
} elseif ($pages -gt $MaxPages) {
    Write-Error "内容超出 $MaxPages 页（实际 $pages 页）！删减内容后重新渲染。" -ErrorAction Continue
    exit 1
} else {
    Write-Host "✓ 一页纸校验通过" -ForegroundColor Green
}
