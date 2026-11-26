param([switch]$BuildOnly, [switch]$Profile)
if ($BuildOnly -and $Profile) { throw "Use either BuildOnly or Profile." }
$ErrorActionPreference = 'Stop'
$flutter = 'C:\src\flutter\bin\flutter.bat'
if (-not (Test-Path $flutter)) { $flutter = (Get-Command flutter -ErrorAction Stop).Source }
$mapping = & (Join-Path (Split-Path -Parent $PSScriptRoot) 'stand-drive.ps1') -Root (Split-Path -Parent $PSScriptRoot)
try {
    Push-Location ($mapping.Drive + '\winter_lab')
    try {
        if (-not (Test-Path 'windows')) {
            & $flutter create --platforms=windows --project-name=statusdesk_winter_lab .
            if ($LASTEXITCODE -ne 0) { throw 'Flutter project creation failed.' }
        }
        $locationKey = $mapping.Drive + '/winter_lab'
        if ((Test-Path '.stand-build-drive') -and (Get-Content '.stand-build-drive' -Raw).Trim() -ne $locationKey) {
            & $flutter clean
            if ($LASTEXITCODE -ne 0) { throw 'Flutter clean failed.' }
        }
        Set-Content '.stand-build-drive' $locationKey
        & $flutter pub get
        if ($LASTEXITCODE -ne 0) { throw 'Flutter pub get failed.' }
        if ($BuildOnly) { & $flutter build windows --release } elseif ($Profile) { & $flutter run -d windows --profile } else { & $flutter run -d windows --release }
        if ($LASTEXITCODE -ne 0) { throw 'Winter lab failed.' }
    } finally { Pop-Location }
} finally {
    try { & subst.exe $mapping.Drive /D }
    finally { $mapping.Lease.ReleaseMutex(); $mapping.Lease.Dispose() }
}
