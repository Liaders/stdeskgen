$ErrorActionPreference = 'Stop'
$destination = Join-Path $PSScriptRoot 'lib\models'
New-Item -ItemType Directory -Force $destination | Out-Null
$python = Join-Path $PSScriptRoot '..\.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { $python = (Get-Command python -ErrorAction Stop).Source }
& $python (Join-Path $PSScriptRoot 'prepare_stand.py')
if ($LASTEXITCODE -ne 0) { throw 'Could not synchronize the production toolbar shell.' }
