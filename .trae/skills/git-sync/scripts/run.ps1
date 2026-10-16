<#
.SYNOPSIS
    JinshiAgent git sync: fetch -> diff analysis -> safe pull/rebase
.PARAMETER DryRun
    analyze only
.PARAMETER NoStash
    do not auto-stash local changes
#>
param(
    [switch]$DryRun,
    [switch]$NoStash
)
. "$PSScriptRoot\..\..\_shared\scripts\find-project-root.ps1"
$ProjectRoot = Find-ProjectRoot
Set-Location $ProjectRoot

Write-Host ""
Write-Host "=== Git Sync ===" -ForegroundColor Cyan

# Step 1: Snapshot
$branch = git --no-pager branch --show-current
Write-Host ""
Write-Host "[1] Branch: $branch" -ForegroundColor Yellow
$hasUpstream = git --no-pager rev-parse --abbrev-ref --symbolic-full-name "@{u}" 2>$null
if ($LASTEXITCODE -ne 0) { Write-Host "  [X] no upstream binding" -ForegroundColor Red; exit 1 }
Write-Host "  upstream: $hasUpstream" -ForegroundColor Gray

$porcelain = git --no-pager status --porcelain 2>&1
$porcelainStr = $porcelain -join "`n"
$hasLocalChanges = ($porcelainStr -match "\S")
Write-Host "  local changes: $hasLocalChanges" -ForegroundColor $(if($hasLocalChanges){"Yellow"}else{"Green"})

# Step 2: Fetch
Write-Host ""
Write-Host "[2] Fetching..." -ForegroundColor Yellow
& git fetch --all --prune 2>&1 | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }
Write-Host "  fetched" -ForegroundColor Green

# Step 3: Diff
$behind = (& git --no-pager rev-list --count "HEAD..origin/$branch" 2>&1) -join ""
$ahead  = (& git --no-pager rev-list --count "origin/$branch..HEAD" 2>&1) -join ""
# ensure numeric
if ($ahead -notmatch "^\d+$") { $ahead = 0 } else { $ahead = [int]$ahead }
if ($behind -notmatch "^\d+$") { $behind = 0 } else { $behind = [int]$behind }

Write-Host ""
Write-Host "[3] Diff: ahead=$ahead  behind=$behind  local_changes=$hasLocalChanges" -ForegroundColor Cyan

if ($ahead -eq 0 -and $behind -eq 0) {
    Write-Host "  already in sync" -ForegroundColor Green; exit 0
}

if ($ahead -gt 0 -and $behind -eq 0 -and -not $hasLocalChanges) {
    Write-Host "  local ahead $ahead, no pull needed" -ForegroundColor Yellow
    Write-Host "  push with git-workflow skill" -ForegroundColor Yellow; exit 0
}

$stashed = $false
if ($ahead -gt 0 -and $behind -gt 0) {
    Write-Host "  ahead $ahead, behind $behind -- rebase needed" -ForegroundColor Yellow
    if ($hasLocalChanges) {
        if ($NoStash) { Write-Host "  [X] local changes + NoStash, cannot continue" -ForegroundColor Red; exit 1 }
        Write-Host "  stashing local changes first..." -ForegroundColor Yellow
        & git stash push -m "trae-auto-stash-before-rebase" 2>&1 | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }
        $stashed = $true
    }
}

# Step 4: Execute
$rebase = $false
if ($ahead -gt 0) { $rebase = $true }
$cmd = "git pull origin $branch"
if ($rebase) { $cmd = "git pull --rebase origin $branch" }

Write-Host ""
Write-Host "[4] $cmd" -ForegroundColor Yellow
if ($DryRun) { Write-Host "  [DryRun]" -ForegroundColor Yellow; exit 0 }

& git $cmd.Split(' ') 2>&1 | ForEach-Object { Write-Host "  $_" -ForegroundColor $(if($_ -match "Updating|Already|Fast-forward|Rebase"){"Green"}else{"Gray"}) }
$pullExit = $LASTEXITCODE

if ($pullExit -ne 0) {
    Write-Host "  [X] Pull failed (exit=$pullExit)" -ForegroundColor Red
    Write-Host "  for rebase conflict: git rebase --abort" -ForegroundColor Yellow
    exit 1
}

if ($stashed) {
    Write-Host ""
    Write-Host "[4b] Restoring stash..." -ForegroundColor Yellow
    & git stash pop 2>&1 | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }
}

# Step 5: Verify
Write-Host ""
Write-Host "[5] Verify" -ForegroundColor Yellow
git --no-pager status -sb | ForEach-Object { Write-Host "  $_" -ForegroundColor Green }

$finalAhead  = (& git --no-pager rev-list --count "origin/$branch..HEAD" 2>&1) -join ""
$finalBehind = (& git --no-pager rev-list --count "HEAD..origin/$branch" 2>&1) -join ""
if ($finalAhead -notmatch "^\d+$") { $finalAhead = 0 } else { $finalAhead = [int]$finalAhead }
if ($finalBehind -notmatch "^\d+$") { $finalBehind = 0 } else { $finalBehind = [int]$finalBehind }
Write-Host "  final: ahead=$finalAhead behind=$finalBehind" -ForegroundColor Cyan

Write-Host ""
Write-Host "=== Sync done (OK) ===" -ForegroundColor Green
exit 0
