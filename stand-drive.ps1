param([Parameter(Mandatory=$true)][string]$Root)
$ErrorActionPreference = 'Stop'
$target = [IO.Path]::GetFullPath($Root).TrimEnd('\')
$sha = [Security.Cryptography.SHA256]::Create()
try { $key = [BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($target.ToLowerInvariant()))).Replace('-', '') }
finally { $sha.Dispose() }
# One Flutter stand owns this mapping at a time. Windows releases the mutex
# automatically if its PowerShell host is terminated before finally runs.
$lease = [Threading.Mutex]::new($false, ('Local\StatusDeskStand-' + $key))
$held = $false
try {
    try { $held = $lease.WaitOne(0) }
    catch [Threading.AbandonedMutexException] { $held = $true }
    if (-not $held) { throw 'Another StatusDesk stand is running. Close it before starting this stand.' }
    $drive = $null
    foreach ($line in (& subst.exe)) {
        if ($line -match '^([A-Za-z]:)\\: => (.+)$' -and
            [string]::Equals($matches[2].TrimEnd('\'), $target, [StringComparison]::OrdinalIgnoreCase)) {
            $drive = $matches[1]
            break
        }
    }
    if (-not $drive) {
        $drive = 90..71 | ForEach-Object { ([char]$_).ToString() + ':' } |
            Where-Object { -not (Test-Path ($_ + '\')) } | Select-Object -First 1
        if (-not $drive) { throw 'No free drive letter for the Flutter stand.' }
        & subst.exe $drive $target
        if ($LASTEXITCODE -ne 0) { throw 'Could not map the stand directory.' }
    }
    [pscustomobject]@{ Drive = $drive; Lease = $lease }
} catch {
    if ($held) { $lease.ReleaseMutex() }
    $lease.Dispose()
    throw
}
