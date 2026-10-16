<#
.SYNOPSIS
    JinshiAgent git push + verify with optional quality gate
.PARAMETER Gate
    none | diff | strict  (default diff)
.PARAMETER DryRun
    print only, do not execute
#>
param(
    [ValidateSet("none","diff","strict")]
    [string]$Gate = "diff",
    [switch]$DryRun
)
. "$PSScriptRoot\..\..\_shared\scripts\find-project-root.ps1"
$ProjectRoot = Find-ProjectRoot
Set-Location $ProjectRoot

Write-Host ""
Write-Host "=== Git Workflow (Gate=$Gate) ===" -ForegroundColor Cyan

# Snapshot
Write-Host ""
Write-Host "[Snapshot]" -ForegroundColor Yellow
git --no-pager remote -v | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }
git --no-pager branch --show-current | ForEach-Object { Write-Host "  branch: $_" -ForegroundColor Gray }
git --no-pager status -sb | ForEach-Object { Write-Host "  status: $_" -ForegroundColor Gray }

# Staged check
$porcelain = git --no-pager status --porcelain 2>&1
$porcelainStr = $porcelain -join "`n"
if ($porcelainStr -match "\S") {
    Write-Host ""
    Write-Host "  local changes detected. Run git add + git commit first, then this script." -ForegroundColor Yellow
    $porcelain -split "`n" | ForEach-Object { if ($_ -match "\S") { Write-Host "    $_" -ForegroundColor DarkGray } }
    exit 0
}

# Gate
if ($Gate -ne "none") {
    Write-Host ""
    Write-Host "[Gate] git diff --check" -ForegroundColor Yellow
    git --no-pager diff --check 2>&1 | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }
    if ($LASTEXITCODE -ne 0) { Write-Host "  [X] diff --check failed, fix whitespace" -ForegroundColor Red; exit 1 }

    if ($Gate -eq "strict") {
        Write-Host ""
        Write-Host "[Gate] ruff + mypy" -ForegroundColor Yellow
        if (Test-Path ".venv\Scripts\python.exe") {
            .\.venv\Scripts\python.exe -m ruff check src/ tests/ --fix 2>&1 | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }
            .\.venv\Scripts\python.exe -m ruff format src/ tests/ 2>&1 | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }
            .\.venv\Scripts\python.exe -m mypy src/ --ignore-missing-imports 2>&1 | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }
        } else {
            Write-Host "  [SKIP] no .venv, cannot run ruff/mypy" -ForegroundColor Yellow
        }
    }
}

# Push
$branch = git --no-pager branch --show-current
$hasUpstream = git --no-pager rev-parse --abbrev-ref --symbolic-full-name "@{u}" 2>$null
$needUpstream = $false; if ($LASTEXITCODE -ne 0) { $needUpstream = $true }
$pushCmd = "git push -u origin $branch"; if (-not $needUpstream) { $pushCmd = "git push origin $branch" }

Write-Host ""
Write-Host "[Push] $pushCmd" -ForegroundColor Yellow
if ($DryRun) { Write-Host "  [DryRun]" -ForegroundColor Yellow; exit 0 }

$env:GIT_TERMINAL_PROMPT = "0"
& git push -u origin $branch 2>&1 | ForEach-Object { Write-Host "  $_" -ForegroundColor $(if ($_ -match "->|\.\."){"Green"}else{"Gray"}) }
$pushExit = $LASTEXITCODE

if ($pushExit -ne 0) {
    Write-Host ""
    Write-Host "  [X] Push failed (exit=$pushExit)" -ForegroundColor Red
    Write-Host "  likely no cached credentials -- push once in your own terminal" -ForegroundColor Yellow
    exit 1
}

# Verify
Write-Host ""
Write-Host "[Verify]" -ForegroundColor Yellow
git --no-pager status -sb | ForEach-Object { Write-Host "  $_" -ForegroundColor Green }
$remoteHead = git --no-pager ls-remote origin "refs/heads/$branch" 2>&1
Write-Host "  remote head: $remoteHead" -ForegroundColor Gray

Write-Host ""
Write-Host "=== Done (OK) ===" -ForegroundColor Green
exit 0
