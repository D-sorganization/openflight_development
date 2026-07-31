# Build the technology review PDF with MiKTeX pdflatex.
# Runs pdflatex three times (TOC/cross-refs) plus bibtex if a .bib is present.
$ErrorActionPreference = 'Stop'
$pdflatex = "$env:LOCALAPPDATA\Programs\MiKTeX\miktex\bin\x64\pdflatex.exe"
if (-not (Test-Path $pdflatex)) { $pdflatex = 'pdflatex' }
Set-Location $PSScriptRoot
& $pdflatex -interaction=nonstopmode -halt-on-error main.tex
& $pdflatex -interaction=nonstopmode -halt-on-error main.tex
& $pdflatex -interaction=nonstopmode -halt-on-error main.tex
Write-Host "Built main.pdf"
