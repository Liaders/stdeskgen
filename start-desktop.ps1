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
    $url = 'http://127.0.0.1:8765'
    $ready = $false
    try { $health = Invoke-RestMethod "$url/desktop/status" -TimeoutSec 2; $ready = $health.desktop_api -eq 1 } catch {}
    if (-not $ready) {
        $occupied = Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue
        if ($occupied) { throw 'Порт 8765 занят прежним конструктором. Закройте его окно CMD и запустите это приложение снова.' }
        & $python manage.py migrate --noinput *> (Join-Path $state 'migrate.log')
        if ($LASTEXITCODE -ne 0) { throw 'Не удалось подготовить базу. См. .desktop/migrate.log.' }
        $server = Start-Process -FilePath $python -ArgumentList @('manage.py','runserver','127.0.0.1:8765','--noreload') -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $state 'server.log') -RedirectStandardError (Join-Path $state 'server-error.log') -PassThru
        for ($attempt=0; $attempt -lt 45; $attempt++) {
            try { $health = Invoke-RestMethod "$url/desktop/status" -TimeoutSec 1; if ($health.desktop_api -eq 1) { $ready=$true; break } } catch {}
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
    $top = New-Object System.Windows.Forms.FlowLayoutPanel
    $top.Dock='Top'; $top.Height=46; $top.Padding=New-Object System.Windows.Forms.Padding(8)
    $homeButton = New-Object System.Windows.Forms.Button
    $homeButton.Text='Главная'; $homeButton.Width=110; $homeButton.BackColor=[Drawing.Color]::FromArgb(239,127,26); $homeButton.FlatStyle='Flat'
    $reload = New-Object System.Windows.Forms.Button
    $reload.Text='Обновить'; $reload.Width=110; $reload.BackColor=[Drawing.Color]::FromArgb(239,127,26); $reload.FlatStyle='Flat'
    $top.Controls.Add($homeButton); $top.Controls.Add($reload)
    $tabs = New-Object System.Windows.Forms.TabControl
    $tabs.Dock='Fill'; $tabs.Font=New-Object Drawing.Font('Segoe UI',11)
    $views = @()
    foreach ($entry in @(@('Конструктор',"$url/"),@('Публикация',"$url/desktop/publication"))) {
        $page = New-Object System.Windows.Forms.TabPage
        $page.Text=$entry[0]
        $view = New-Object Microsoft.Web.WebView2.WinForms.WebView2
        $view.Dock='Fill'
        $properties = New-Object Microsoft.Web.WebView2.WinForms.CoreWebView2CreationProperties
        $properties.UserDataFolder = Join-Path $state 'webview-profile'
        $view.CreationProperties = $properties
        $view.add_CoreWebView2InitializationCompleted({
            param($sender,$eventArgs)
            if (-not $eventArgs.IsSuccess) {
                [System.Windows.Forms.MessageBox]::Show('Не удалось запустить Edge WebView2. Установите Microsoft Edge WebView2 Runtime. ' + $eventArgs.InitializationException.Message,'StatusDesk') | Out-Null
                return
            }
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
        $view.Source = [Uri]$entry[1]
        $page.Controls.Add($view); $tabs.TabPages.Add($page); $views += $view
    }
    $homeButton.add_Click({$tabs.SelectedIndex=0; $views[0].Source=[Uri]"$url/"})
    $reload.add_Click({$views[$tabs.SelectedIndex].Reload()})
    $form.Controls.Add($tabs); $form.Controls.Add($top)
    [System.Windows.Forms.Application]::Run($form)
} catch {
    [System.Windows.Forms.MessageBox]::Show($_.Exception.Message,'StatusDesk — ошибка',[System.Windows.Forms.MessageBoxButtons]::OK,[System.Windows.Forms.MessageBoxIcon]::Error) | Out-Null
} finally {
    if ($form) { $form.Dispose() }
    if ($server -and -not $server.HasExited) { & taskkill.exe /PID $server.Id /T /F *> $null }
}
