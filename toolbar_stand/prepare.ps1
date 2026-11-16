$ErrorActionPreference = 'Stop'
$destination = Join-Path $PSScriptRoot 'lib\models'
New-Item -ItemType Directory -Force $destination | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot '..\customization\compact_session_toolbar.dart') -Destination (Join-Path $destination 'rdgen_compact_session_toolbar.dart') -Force
