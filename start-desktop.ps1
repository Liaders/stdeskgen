# StatusDesk desktop shell. All build and publication operations remain local.
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()
$server = $null
$form = $null
try {
    if (-not [Environment]::Is64BitProcess) { throw 'Запустите приложение через start-desktop.cmd (нужен PowerShell x64).' }
    Set-Location -LiteralPath $PSScriptRoot
    $state = Join-Path $PSScriptRoot '.desktop'
    New-Item -ItemType Directory -Path $state -Force | Out-Null
    $python = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
    if (-not (Test-Path -LiteralPath $python)) {
        & python -m venv (Join-Path $PSScriptRoot '.venv')
        if ($LASTEXITCODE -ne 0) { throw 'Не удалось создать Python venv.' }
        & $python -m pip install -r (Join-Path $PSScriptRoot 'requirements.txt')
        if ($LASTEXITCODE -ne 0) { throw 'Не удалось установить зависимости Python.' }
    }
    $git = Get-Command git -ErrorAction SilentlyContinue
    if ($git) { $env:GIT_EXECUTABLE = $git.Source }
    else { $env:GIT_EXECUTABLE = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/native/git/cmd/git.exe' }
    if (-not (Test-Path -LiteralPath $env:GIT_EXECUTABLE)) { throw 'Установите Git for Windows и войдите в GitHub через Git Credential Manager.' }
    $env:LOCAL_GITHUB_BUILD = 'true'
    $env:PYTHONUTF8 = '1'
    if (-not $env:GHUSER) { $env:GHUSER = 'Liaders' }
    if (-not $env:REPONAME) { $env:REPONAME = 'stdeskgen' }
    $expectedRevision = (& $python -c 'from rdgenerator.constructor_version import revision; print(revision())').Trim()
    if ($LASTEXITCODE -ne 0 -or $expectedRevision -notmatch '^[0-9a-f]{64}$') { throw 'Не удалось определить версию конструктора.' }
    $url = 'http://127.0.0.1:8765'
    $ready = $false
    $health = $null
    try { $health = Invoke-RestMethod "$url/desktop/status" -TimeoutSec 2; $ready = $health.desktop_api -eq 1 -and $health.constructor_revision -eq $expectedRevision } catch {}
    if (-not $ready) {
        $occupied = Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue
        if ($occupied) {
            if ($health.desktop_api -eq 1) { throw 'Работает прежняя версия сервера конструктора. Закройте окно конструктора и запустите restart-desktop.cmd из папки rdgen.' }
            throw 'Порт 8765 занят другим приложением. Освободите порт и повторите запуск.'
        }
        & $python manage.py migrate --noinput *> (Join-Path $state 'migrate.log')
        if ($LASTEXITCODE -ne 0) { throw 'Не удалось подготовить базу. См. .desktop/migrate.log.' }
        $server = Start-Process -FilePath $python -ArgumentList @('manage.py','runserver','127.0.0.1:8765','--noreload') -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $state 'server.log') -RedirectStandardError (Join-Path $state 'server-error.log') -PassThru
        for ($attempt=0; $attempt -lt 45; $attempt++) {
            try { $health = Invoke-RestMethod "$url/desktop/status" -TimeoutSec 1; if ($health.desktop_api -eq 1 -and $health.constructor_revision -eq $expectedRevision) { $ready=$true; break } } catch {}
            if ($server.HasExited) { break }
            Start-Sleep -Milliseconds 500
        }
        if (-not $ready) { throw 'Локальный сервер не запустился. См. .desktop/server-error.log.' }
    }
    $version = '1.0.3650.58'
    $sdk = Join-Path $PSScriptRoot ".tools/webview2-$version"
    $formsDll = Join-Path $sdk 'lib/net462/Microsoft.Web.WebView2.WinForms.dll'
    $coreDll = Join-Path $sdk 'lib/net462/Microsoft.Web.WebView2.Core.dll'
    $loaderDll = Join-Path $sdk 'runtimes/win-x64/native/WebView2Loader.dll'
    if (-not (Test-Path -LiteralPath $formsDll) -or -not (Test-Path -LiteralPath $coreDll) -or -not (Test-Path -LiteralPath $loaderDll)) {
        & $python (Join-Path $PSScriptRoot 'rdgenerator/desktop_setup.py') *> (Join-Path $state 'webview-setup.log')
        if ($LASTEXITCODE -ne 0) { throw 'Не удалось загрузить SDK Microsoft WebView2. См. .desktop/webview-setup.log.' }
    }
    $env:PATH = (Join-Path $sdk 'runtimes/win-x64/native') + ';' + $env:PATH
    Add-Type -Path (Join-Path $sdk 'lib/net462/Microsoft.Web.WebView2.Core.dll')
    Add-Type -Path $formsDll
    $form = New-Object System.Windows.Forms.Form
    $form.Text = 'StatusDesk — конструктор и публикация'
    $form.Size = New-Object Drawing.Size(1280,900)
    $form.MinimumSize = New-Object Drawing.Size(960,680)
    $form.StartPosition = 'CenterScreen'
    $form.BackColor = [Drawing.Color]::FromArgb(20,20,20)
    $content = New-Object System.Windows.Forms.Panel
    $content.Dock = 'Fill'
    $viewsByRoute = @{}
    $navigation = @{ Route = '/' }
    function Show-ConstructorPage([string]$route) {
        if (-not $viewsByRoute.ContainsKey($route) -or $navigation.Route -eq $route) { return }
        $targetView = $viewsByRoute[$route]
        $navigation.Route = $route
        $content.SuspendLayout()
        try {
            $targetView.Visible = $true
            $targetView.BringToFront()
            foreach ($otherRoute in $viewsByRoute.Keys) {
                if ($otherRoute -ne $route) { $viewsByRoute[$otherRoute].Visible = $false }
            }
        } finally { $content.ResumeLayout() }
        $targetView.Focus() | Out-Null
    }
    foreach ($route in @('/', '/desktop/builds-page', '/desktop/publication')) {
        $view = New-Object Microsoft.Web.WebView2.WinForms.WebView2
        $view.Dock='Fill'
        $view.Visible = ($route -eq '/')
        $view.Tag = $route
        $properties = New-Object Microsoft.Web.WebView2.WinForms.CoreWebView2CreationProperties
        $properties.UserDataFolder = Join-Path $state 'webview-profile'
        $view.CreationProperties = $properties
        $view.add_CoreWebView2InitializationCompleted({
            param($sender,$eventArgs)
            if (-not $eventArgs.IsSuccess) {
                [System.Windows.Forms.MessageBox]::Show('Не удалось запустить Edge WebView2. Установите Microsoft Edge WebView2 Runtime. ' + $eventArgs.InitializationException.Message,'StatusDesk') | Out-Null
                return
            }
            $sender.CoreWebView2.add_WebMessageReceived({
                param($web,$messageEvent)
                if (-not $messageEvent.Source.StartsWith($url + '/')) { return }
                try {
                    $message = $messageEvent.WebMessageAsJson | ConvertFrom-Json
                    if ($message.route -is [string] -and $viewsByRoute.ContainsKey($message.route)) {
                        Show-ConstructorPage $message.route
                    }
                    if ($message.reload -eq $true) {
                        $viewsByRoute[$navigation.Route].Reload()
                    }
                } catch { }
            })
            $sender.CoreWebView2.add_NewWindowRequested({
                param($web,$eventArgs)
                $eventArgs.Handled=$true
                $target=[Uri]$eventArgs.Uri
                if ($target.Scheme -in @('http','https')) { Start-Process $target.AbsoluteUri }
            })
        })
        $view.add_NavigationStarting({
            param($sender,$eventArgs)
            $target=[Uri]$eventArgs.Uri
            if ($target.Host -ne '127.0.0.1' -or $target.Port -ne 8765) {
                $eventArgs.Cancel=$true
                if ($target.Scheme -in @('http','https')) { Start-Process $target.AbsoluteUri }
            }
        })
        $viewsByRoute[$route] = $view
        $view.Source = [Uri]($url + $route)
        $content.Controls.Add($view)
    }
    $form.Controls.Add($content)
    [System.Windows.Forms.Application]::Run($form)
} catch {
    [System.Windows.Forms.MessageBox]::Show($_.Exception.Message,'StatusDesk — ошибка',[System.Windows.Forms.MessageBoxButtons]::OK,[System.Windows.Forms.MessageBoxIcon]::Error) | Out-Null
} finally {
    if ($form) { $form.Dispose() }
    if ($server -and -not $server.HasExited) { & taskkill.exe /PID $server.Id /T /F *> $null }
}
