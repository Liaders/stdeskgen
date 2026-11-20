param([switch]$BuildOnly)
$ErrorActionPreference = 'Stop'
$flutter = 'C:\src\flutter\bin\flutter.bat'
if (-not (Test-Path -LiteralPath $flutter)) { $flutter = (Get-Command flutter -ErrorAction Stop).Source }
$drive = 90..71 | ForEach-Object { ([char]$_).ToString() + ':' } | Where-Object { -not (Test-Path ($_ + '\')) } | Select-Object -First 1
if (-not $drive) { throw 'No free drive letter for the winter stand.' }
& subst.exe $drive (Split-Path -Parent $PSScriptRoot)
if ($LASTEXITCODE -ne 0) { throw 'Could not map the stand directory.' }
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
} finally { & subst.exe $drive /D }
