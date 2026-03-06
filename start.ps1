#!/usr/bin/env pwsh
# TeacherBot - Quick Start (PowerShell)
# Usage: .\start.ps1

param(
    [switch]$Setup,
    [switch]$Run,
    [switch]$Deps,
    [switch]$Clean
)

Push-Location $PSScriptRoot
try {
    python start.py $(
        if ($Setup) { '--setup' }
        if ($Run) { '--run' }
        if ($Deps) { '--deps' }
        if ($Clean) { '--clean' }
    )
}
finally {
    Pop-Location
}
