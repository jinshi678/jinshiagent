<#
.SYNOPSIS
    JinshiAgent env-setup: venv + pip + .env + verify
.PARAMETER Tier
    core | dev | memory | web | all  (default dev)
.PARAMETER SkipEnv
    skip .env template creation
#>
param(
    [ValidateSet("core","dev","memory","web","all")]
    [string]$Tier = "dev",
    [switch]$SkipEnv
)
$ErrorActionPreference = "Stop"
. "$PSScriptRoot\..\..\_shared\scripts\find-project-root.ps1"
$ProjectRoot = Find-ProjectRoot
Set-Location $ProjectRoot

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " JinshiAgent Environment Setup" -ForegroundColor Cyan
Write-Host " Tier: $Tier" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 1. Python
Write-Host ""
Write-Host "[1/6] Checking Python..." -ForegroundColor Yellow
$pyVer = & python --version 2>&1
Write-Host "  $pyVer" -ForegroundColor Gray
if ($LASTEXITCODE -ne 0) { Write-Host "  [X] python not found" -ForegroundColor Red; exit 1 }
$major = [int]($pyVer.ToString() -replace '.*(\d+)\.(\d+).*','$1')
$minor = [int]($pyVer.ToString() -replace '.*(\d+)\.(\d+).*','$2')
$verOk = ($major -ge 3) -and -not ($major -eq 3 -and $minor -lt 11)
if (-not $verOk) { Write-Host "  [X] Python >= 3.11 required, got $major.$minor" -ForegroundColor Red; exit 1 }
Write-Host "  Python OK" -ForegroundColor Green

# 2. venv
Write-Host ""
Write-Host "[2/6] Virtual environment..." -ForegroundColor Yellow
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    & python -m venv .venv
    Write-Host "  Created .venv" -ForegroundColor Green
} else {
    Write-Host "  .venv already exists" -ForegroundColor Gray
}

# 3. pip upgrade
Write-Host ""
Write-Host "[3/6] Upgrading pip..." -ForegroundColor Yellow
& .\.venv\Scripts\python.exe -m pip install --upgrade pip 2>&1 | Out-Null
Write-Host "  pip upgraded" -ForegroundColor Green

# 4. Install
Write-Host ""
Write-Host "[4/6] Installing dependencies (tier=$Tier)..." -ForegroundColor Yellow
$installTarget = "."; if ($Tier -ne "core") { $installTarget = ".[$Tier]" }
& .\.venv\Scripts\python.exe -m pip install -e $installTarget 2>&1 | ForEach-Object { Write-Host "  $_" -ForegroundColor DarkGray }
if ($LASTEXITCODE -ne 0) {
    Write-Host "  [X] install failed, retrying with mirror..." -ForegroundColor Red
    & .\.venv\Scripts\python.exe -m pip install -e $installTarget --index-url https://pypi.tuna.tsinghua.edu.cn/simple
}
Write-Host "  Dependencies installed" -ForegroundColor Green

# 5. .env
Write-Host ""
Write-Host "[5/6] .env configuration..." -ForegroundColor Yellow
if ($SkipEnv) {
    Write-Host "  skipped (-SkipEnv)" -ForegroundColor Gray
} elseif (Test-Path ".env") {
    Write-Host "  .env already exists" -ForegroundColor Green
} elseif (Test-Path ".env.example") {
    Copy-Item .env.example .env
    Write-Host "  Created .env from .env.example" -ForegroundColor Green
    Write-Host "  Please edit .env and add OPENAI_API_KEY" -ForegroundColor Yellow
} else {
    Write-Host "  .env.example not found, skipping" -ForegroundColor Yellow
}

# 6. Verify
Write-Host ""
Write-Host "[6/6] Verifying install..." -ForegroundColor Yellow
$py = ".\.venv\Scripts\python.exe"
$tests = @(
    @{ name = "jinshiagent package"; cmd = "import jinshiagent; print(jinshiagent.__version__)" },
    @{ name = "core (Agent, ToolRegistry)"; cmd = "from jinshiagent.core import Agent, ToolRegistry; print('ok')" },
    @{ name = "llm (LLMClient)"; cmd = "from jinshiagent.llm import LLMClient; print('ok')" }
)
$allOk = $true
foreach ($t in $tests) {
    $result = & $py -c $t.cmd 2>&1
    if ($LASTEXITCODE -eq 0) { Write-Host "  [OK] $($t.name)" -ForegroundColor Green }
    else { Write-Host "  [X] $($t.name) -- $result" -ForegroundColor Red; $allOk = $false }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
if ($allOk) { Write-Host "  Environment ready!" -ForegroundColor Green; Write-Host "  Activate: .\.venv\Scripts\Activate.ps1" -ForegroundColor White }
else { Write-Host "  Some verifications failed" -ForegroundColor Red }
Write-Host "========================================" -ForegroundColor Cyan
exit $(if ($allOk) { 0 } else { 1 })
