param([switch]$BuildOnly)
$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'prepare.ps1')
$flutter = 'C:\src\flutter\bin\flutter.bat'
if (-not (Test-Path $flutter)) { $flutter = (Get-Command flutter -ErrorAction Stop).Source }
$mapping = & (Join-Path (Split-Path -Parent $PSScriptRoot) 'stand-drive.ps1') -Root (Split-Path -Parent $PSScriptRoot)
$drive = $mapping.Drive
try {
    Push-Location ($drive + '\toolbar_stand')
    try {
        $marker = Join-Path $PSScriptRoot '.stand-build-drive'
        if (-not (Test-Path $marker) -or (Get-Content $marker -Raw).Trim() -ne ($drive + '/toolbar_stand')) {
            & $flutter clean
            if ($LASTEXITCODE -ne 0) { throw 'Flutter clean failed.' }
            Set-Content $marker ($drive + '/toolbar_stand')
        }
        & $flutter pub get
        if ($LASTEXITCODE -ne 0) { throw 'Flutter pub get failed.' }
        if ($BuildOnly) { & $flutter build windows --debug } else { & $flutter run -d windows }
        if ($LASTEXITCODE -ne 0) { throw 'Flutter stand failed.' }
    } finally { Pop-Location }
} finally {
    try { & subst.exe $drive /D }
    finally { $mapping.Lease.ReleaseMutex(); $mapping.Lease.Dispose() }
}

