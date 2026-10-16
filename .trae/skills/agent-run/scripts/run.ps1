<#
.SYNOPSIS
    JinshiAgent CLI launch validator
.DESCRIPTION
    Start python -m jinshiagent non-interactively (echo "quit" | ...), capture banner, verify launch success
.PARAMETER Async
    use async mode
.PARAMETER Verbose
    verbose logging
#>
param(
    [switch]$Async,
    [switch]$Verbose
)
. "$PSScriptRoot\..\..\_shared\scripts\find-project-root.ps1"
$ProjectRoot = Find-ProjectRoot
Set-Location $ProjectRoot
$py = Get-ProjectPython

Write-Host ""
Write-Host "=== Agent Run ===" -ForegroundColor Cyan

$args = @("-m","jinshiagent")
if ($Async) { $args += "--async" }
if ($Verbose) { $args += "--verbose" }

# echo "quit" to auto-exit
$inputStr = "quit`n"

Write-Host "  command: $py $($args -join ' ')" -ForegroundColor Gray
Write-Host ""

# Run with timeout
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $py
$psi.Arguments = ($args -join " ")
$psi.WorkingDirectory = $ProjectRoot
$psi.RedirectStandardInput = $true
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$psi.UseShellExecute = $false
$psi.CreateNoWindow = $true

$proc = New-Object System.Diagnostics.Process
$proc.StartInfo = $psi
[void]$proc.Start()
$proc.StandardInput.WriteLine("quit")
$proc.StandardInput.Flush()
$proc.StandardInput.Close()

# Read output with timeout
$output = ""
$errorOut = ""
$deadline = (Get-Date).AddSeconds(15)
while ((Get-Date) -lt $deadline -and -not $proc.HasExited) {
    Start-Sleep -Milliseconds 300
}
if (-not $proc.HasExited) {
    $proc.Kill()
    Write-Host "  [TIMEOUT] forced kill after 15s" -ForegroundColor Yellow
}

$output = $proc.StandardOutput.ReadToEnd()
$errorOut = $proc.StandardError.ReadToEnd()
$proc.WaitForExit()

Write-Host $output
if ($errorOut) { Write-Host ""; Write-Host "STDERR:" -ForegroundColor Red; Write-Host $errorOut }

# Check banner indicators
$ok = $false
if ($output -match "JinshiAgent" -and $output -match "Agent") { $ok = $true }
if ($output -match "Mock" -or $output -match "OPENAI_API_KEY") { $ok = $true }

Write-Host ""
if ($ok) {
    Write-Host "  Agent started OK (exit=$($proc.ExitCode))" -ForegroundColor Green
    Write-Host "  Interactive mode needs your own terminal" -ForegroundColor Yellow
    exit 0
} else {
    Write-Host "  [X] Agent did not start correctly (exit=$($proc.ExitCode))" -ForegroundColor Red
    exit 1
}
