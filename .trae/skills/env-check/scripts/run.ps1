<#
.SYNOPSIS
    JinshiAgent env-check: Python, venv, imports, deps, .env, git
.PARAMETER Json
    also write env-check-report.json
#>
param([switch]$Json)
. "$PSScriptRoot\..\..\_shared\scripts\find-project-root.ps1"
$ProjectRoot = Find-ProjectRoot
Set-Location $ProjectRoot
$py = Get-ProjectPython

$results = @()
function Record($name, $status, $detail, $fix) {
    $script:results += [PSCustomObject]@{ name=$name; status=$status; detail=$detail; fix=$fix }
    $icon = "[?]"; if ($status -eq "PASS") { $icon = "[OK]" }; if ($status -eq "FAIL") { $icon = "[X]" }; if ($status -eq "WARN") { $icon = "[!]" }
    Write-Host "  [$status] $icon $name -- $detail" -ForegroundColor $(if($status -eq "PASS"){"Green"}elseif($status -eq "FAIL"){"Red"}elseif($status -eq "WARN"){"Yellow"}else{"Gray"})
}

Write-Host ""
Write-Host "=== JinshiAgent Environment Report ===" -ForegroundColor Cyan
Write-Host "Project: $ProjectRoot" -ForegroundColor Gray

# 1. Python version
$v = & python --version 2>&1
$st = "FAIL"; if ($LASTEXITCODE -eq 0) { $st = "PASS" }
Record "Python version" $st $v "Install Python >= 3.11"

# 2. pyproject.toml
$exists = Test-Path "pyproject.toml"
$st = "FAIL"; if ($exists) { $st = "PASS" }
Record "pyproject.toml exists" $st $exists "Run from repo root"

# 3 + 4. venv
$venv = Test-Path ".venv\Scripts\python.exe"
$st = "WARN"; $dt = "not found"
if ($venv) { $st = "PASS"; $dt = ".venv" }
Record "venv exists" $st $dt "Run env-setup"
if ($venv) {
    $vv = & $py --version 2>&1
    Record "venv Python" "PASS" $vv ""
}

# 5. Submodule imports
$imports = @(
    @{ name="jinshiagent package"; cmd="import jinshiagent; print(jinshiagent.__version__)" },
    @{ name="core";              cmd="from jinshiagent.core import Agent, ToolRegistry; print('ok')" },
    @{ name="llm";               cmd="from jinshiagent.llm import LLMClient; print('ok')" },
    @{ name="memory";            cmd="from jinshiagent.memory import LongTermMemory; print('ok')" },
    @{ name="mcp";               cmd="from jinshiagent.mcp import MCPClient; print('ok')" },
    @{ name="tools";             cmd="from jinshiagent.tools import get_weather, search_web, calculator; print('ok')" },
    @{ name="config";            cmd="from jinshiagent.config import load_config; print('ok')" }
)
foreach ($i in $imports) {
    $out = & $py -c $i.cmd 2>&1
    $st = "FAIL"; if ($LASTEXITCODE -eq 0) { $st = "PASS" }
    Record "import $($i.name)" $st ($out -join "") "pip install -e ."
}

# 6. Pip deps
$deps = @("jinshiagent","pytest","fastapi","pydantic","uvicorn")
foreach ($d in $deps) {
    $v = & $py -m pip show $d 2>&1 | Select-String "^Version"
    if ($v) { Record "pip $d" "PASS" ($v.ToString().Trim()) "" } else { Record "pip $d" "FAIL" "not installed" "pip install $d" }
}

# 7. Optional deps
foreach ($d in @("chromadb","streamlit")) {
    $try = & $py -c "import $d; print('ok')" 2>&1
    $st = "WARN"
    if ($LASTEXITCODE -eq 0) { $st = "PASS" }
    Record "optional $d" $st ($(if($LASTEXITCODE -eq 0){"installed"}else{"not installed (optional)"})) "pip install jinshiagent[memory]"
}

# 8. .env
if (Test-Path ".env") {
    $hasKey = Select-String -Path ".env" -Pattern "OPENAI_API_KEY" -ErrorAction SilentlyContinue
    $dt = "present, no key (Mock mode OK)"
    if ($hasKey) { $dt = "OPENAI_API_KEY configured" }
    Record ".env file" "PASS" $dt ""
} else {
    Record ".env file" "WARN" "missing" "Copy-Item .env.example .env"
}

# 9. Git
$git = & git --no-pager rev-parse --is-inside-work-tree 2>&1
$st = "FAIL"; if ($git -eq "true") { $st = "PASS" }
Record "git repo" $st $git "git init"

# Summary
Write-Host ""
Write-Host "=== Summary ===" -ForegroundColor Cyan
$pass = ($results | Where-Object { $_.status -eq "PASS" }).Count
$fail = ($results | Where-Object { $_.status -eq "FAIL" }).Count
$warn = ($results | Where-Object { $_.status -eq "WARN" }).Count
$color = "Green"; if ($fail -gt 0) { $color = "Red" }
Write-Host "  PASS=$pass  FAIL=$fail  WARN=$warn" -ForegroundColor $color

if ($Json) { $results | ConvertTo-Json -Depth 3 | Out-File "env-check-report.json" -Encoding utf8; Write-Host ""; Write-Host "Report saved: env-check-report.json" }
if ($fail -eq 0) { exit 0 } else { exit 1 }
