<#
.SYNOPSIS
    JinshiAgent pytest runner with scope selection
.PARAMETER Scope
    unit | core | integration | full  (default unit)
.PARAMETER File
    specific test file name (without test_ prefix / .py), overrides Scope
.PARAMETER DryRun
    print command only, do not run
#>
param(
    [ValidateSet("unit","core","integration","full")]
    [string]$Scope = "unit",
    [string]$File = "",
    [switch]$DryRun
)
. "$PSScriptRoot\..\..\_shared\scripts\find-project-root.ps1"
$ProjectRoot = Find-ProjectRoot
Set-Location $ProjectRoot
$py = Get-ProjectPython

if ($File) {
    $cmd = "$py -m pytest tests/test_$File.py --tb=short -v"
} else {
    $extra = switch ($Scope) {
        "unit"        { "--ignore=tests/test_mcp.py --ignore=tests/test_long_term_memory.py -k 'not mcp and not long_term'" }
        "core"        { "tests/test_core.py tests/test_multi_agent.py tests/test_config_memory.py" }
        "integration" { "--ignore=tests/test_long_term_memory.py" }
        "full"        { "" }
    }
    $cmd = "$py -m pytest $extra --tb=short -v"
}

Write-Host ""
Write-Host "=== Running Tests (scope=$Scope file=$File) ===" -ForegroundColor Cyan
Write-Host "  $cmd" -ForegroundColor Gray

if ($DryRun) { Write-Host "  [DryRun]" -ForegroundColor Yellow; exit 0 }

Invoke-Expression $cmd 2>&1 | ForEach-Object { Write-Host $_ }
$exit = $LASTEXITCODE

Write-Host ""
Write-Host "=== Summary ===" -ForegroundColor Cyan
Write-Host "  exit=$exit" -ForegroundColor $(if($exit -eq 0){"Green"}else{"Red"})
exit $exit
