# Local constructor → GitHub Actions
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath '.venv/Scripts/python.exe')) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Python could not create the virtual environment.' }
}
& '.venv/Scripts/python.exe' -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
$localGit = Get-Command git -ErrorAction SilentlyContinue
if ($localGit) {
    $env:GIT_EXECUTABLE = $localGit.Source
} else {
    $bundledGit = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/native/git/cmd/git.exe'
    if (-not (Test-Path -LiteralPath $bundledGit)) { throw 'Install Git for Windows and sign in to GitHub with Git Credential Manager.' }
    $env:GIT_EXECUTABLE = $bundledGit
}
$env:LOCAL_GITHUB_BUILD = 'true'
if (-not $env:GHUSER) { $env:GHUSER = 'Liaders' }
if (-not $env:REPONAME) { $env:REPONAME = 'stdeskgen' }
& '.venv/Scripts/python.exe' manage.py migrate
if ($LASTEXITCODE -ne 0) { throw 'Database initialization failed.' }
Write-Host 'Open http://127.0.0.1:8765 in your browser. Keep this window open while using the constructor.'
& '.venv/Scripts/python.exe' manage.py runserver 127.0.0.1:8765 --noreload
