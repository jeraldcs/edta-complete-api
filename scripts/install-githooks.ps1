# Enable repo git hooks that strip Cursor co-author trailers from commits.
Set-Location (Split-Path $PSScriptRoot -Parent)
git config core.hooksPath .githooks
Write-Host "Git hooks enabled: core.hooksPath=.githooks"
