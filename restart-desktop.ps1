# Operator-launched restart of this workspace's constructor backend only.
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
try {
    Set-Location -LiteralPath $PSScriptRoot
    $python = (Join-Path $PSScriptRoot '.venv\Scripts\python.exe').ToLowerInvariant()
    $listeners = @(Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique)
    foreach ($listenerId in $listeners) {
        $process = Get-CimInstance Win32_Process -Filter "ProcessId = $listenerId"
        $command = ([string]$process.CommandLine).Replace('/','\').ToLowerInvariant()
        if (-not $command.Contains($python) -or $command -notmatch '\bmanage\.py\s+runserver\s+127\.0\.0\.1:8765(?:\s|$)') {
            throw "Порт 8765 занят процессом $listenerId, который не удалось подтвердить как сервер этого конструктора. Он не остановлен."
        }
        # Recheck identity immediately before stopping; never stop an unrelated PID.
        $current = Get-CimInstance Win32_Process -Filter "ProcessId = $listenerId"
        if ($current.CreationDate -ne $process.CreationDate -or $current.CommandLine -ne $process.CommandLine) {
            throw 'Процесс на порту 8765 изменился. Повторите запуск.'
        }
        Stop-Process -Id $listenerId -ErrorAction Stop
        Wait-Process -Id $listenerId -Timeout 10 -ErrorAction SilentlyContinue
    }
    & (Join-Path $PSScriptRoot 'start-desktop.ps1')
} catch {
    [System.Windows.Forms.MessageBox]::Show($_.Exception.Message,'StatusDesk — перезапуск конструктора',[System.Windows.Forms.MessageBoxButtons]::OK,[System.Windows.Forms.MessageBoxIcon]::Error) | Out-Null
}
