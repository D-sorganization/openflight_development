# Build the technology review PDF (Windows / MiKTeX).
#
# Sequence: pdflatex -> biber -> pdflatex -> pdflatex
#   pass 1  writes .aux/.bcf and collects citation keys
#   biber   resolves references.bib into main.bbl
#   pass 2  inserts the bibliography and numbers it
#   pass 3  settles the table of contents and all cross-references
#
# Fails loudly on LaTeX errors, undefined citations, and undefined
# references so local builds match the CI gate (.github/workflows/tech-review.yml).
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

$bin = "$env:LOCALAPPDATA\Programs\MiKTeX\miktex\bin\x64"
$pdflatex = if (Test-Path "$bin\pdflatex.exe") { "$bin\pdflatex.exe" } else { 'pdflatex' }
$biber    = if (Test-Path "$bin\biber.exe")    { "$bin\biber.exe"    } else { 'biber' }

& $pdflatex -interaction=nonstopmode -halt-on-error main.tex | Out-Null
if ($LASTEXITCODE -ne 0) { throw "pdflatex pass 1 failed - see main.log" }

& $biber main | Out-Null
if ($LASTEXITCODE -ne 0) { throw "biber failed - see main.blg" }

& $pdflatex -interaction=nonstopmode -halt-on-error main.tex | Out-Null
& $pdflatex -interaction=nonstopmode -halt-on-error main.tex | Out-Null
if ($LASTEXITCODE -ne 0) { throw "pdflatex final pass failed - see main.log" }

# Undefined citations/references are warnings to LaTeX but errors to us:
# they mean a \cite key is missing from references.bib, or a \cref target
# does not exist.
$undefined = Select-String -Path main.log -Pattern 'Citation .* undefined|Reference .* undefined'
if ($undefined) {
    $undefined | ForEach-Object { Write-Host $_.Line }
    throw "Undefined citations or references found - fix before committing"
}

$pages = (Select-String -Path main.log -Pattern 'Output written on main\.pdf \((\d+) pages').Matches.Groups[1].Value
Write-Host "Built main.pdf ($pages pages) with no undefined citations or references."
