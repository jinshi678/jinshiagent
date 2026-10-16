<#
.SYNOPSIS
    Walk up directories from $PSScriptRoot to find the dir containing pyproject.toml
.DESCRIPTION
    Used by every skill script to locate the project root reliably.
    Usage inside a skill script:
        . "$PSScriptRoot\..\..\_shared\scripts\find-project-root.ps1"
        $ProjectRoot = Find-ProjectRoot
#>

function Find-ProjectRoot {
    param([string]$StartDir = $PSScriptRoot)
    $dir = $StartDir
    while ($dir -and (Test-Path $dir)) {
        if (Test-Path (Join-Path $dir "pyproject.toml")) {
            return $dir
        }
        $parent = Split-Path -Parent $dir
        if ($parent -eq $dir) { break }
        $dir = $parent
    }
    return $StartDir
}

function Get-ProjectPython {
    param([string]$Root = (Find-ProjectRoot))
    $venvPy = Join-Path $Root ".venv\Scripts\python.exe"
    if (Test-Path $venvPy) { return $venvPy }
    return "python"
}
