param([switch]$BuildOnly)
$ErrorActionPreference = 'Stop'
$flutter = 'C:\src\flutter\bin\flutter.bat'
if (-not (Test-Path -LiteralPath $flutter)) { $flutter = (Get-Command flutter -ErrorAction Stop).Source }
$mapping = & (Join-Path (Split-Path -Parent $PSScriptRoot) 'stand-drive.ps1') -Root (Split-Path -Parent $PSScriptRoot)
$drive = $mapping.Drive
try {
    Push-Location ($drive + '\winter_stand')
    try {
        $marker = Join-Path $PSScriptRoot '.stand-build-drive'
        if (-not (Test-Path -LiteralPath $marker) -or (Get-Content -LiteralPath $marker -Raw).Trim() -ne ($drive + '/winter_stand')) {
            & $flutter clean
            if ($LASTEXITCODE -ne 0) { throw 'Flutter clean failed.' }
            Set-Content -LiteralPath $marker ($drive + '/winter_stand')
        }
        & $flutter pub get
        if ($LASTEXITCODE -ne 0) { throw 'Flutter pub get failed.' }
        if ($BuildOnly) { & $flutter build windows --release } else { & $flutter run -d windows --release }
        if ($LASTEXITCODE -ne 0) { throw 'Flutter winter stand failed.' }
    } finally { Pop-Location }
} finally {
    try { & subst.exe $drive /D }
    finally { $mapping.Lease.ReleaseMutex(); $mapping.Lease.Dispose() }
}
