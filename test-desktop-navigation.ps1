$ErrorActionPreference = 'Stop'
$tokens = $null
$parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot 'start-desktop.ps1'), [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count) { throw ($parseErrors | Out-String) }
$switch = $ast.Find({ param($node) $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq 'Show-ConstructorPage' }, $true)
if (-not $switch) { throw 'Missing page switch function' }
Invoke-Expression $switch.Extent.Text
$preload = $ast.Find({ param($node) $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq 'Initialize-ConstructorPages' }, $true)
if (-not $preload) { throw 'Missing page preload function' }
Invoke-Expression $preload.Extent.Text

# Execute the real switching function without starting Windows Forms or WebView2.
$content = [pscustomobject]@{}
$content | Add-Member ScriptMethod SuspendLayout {}
$content | Add-Member ScriptMethod ResumeLayout {}
$viewsByRoute = @{}
foreach ($route in @('/desktop/publication', '/', '/desktop/builds-page')) {
    $page = [pscustomobject]@{ Page = $route; Visible = ($route -eq '/'); Draft = 'Retained configuration'; Raises = 0; Initializations = 0 }
    $page | Add-Member ScriptMethod BringToFront { $this.Raises++ }
    $page | Add-Member ScriptMethod Focus { throw 'Page switch forced focus to first link' }
    $page | Add-Member ScriptMethod EnsureCoreWebView2Async { param($environment) $this.Initializations++ }
    $viewsByRoute[$route] = $page
}
$navigation = @{ Route = '/' }
Initialize-ConstructorPages
if (@($viewsByRoute.Values | Where-Object { $_.Initializations -ne 1 }).Count) { throw 'Not all pages were preloaded' }
if ($navigation.Route -ne '/') { throw 'Preload changed the selected page' }
foreach ($route in @('/', '/desktop/builds-page', '/desktop/builds-page', '/desktop/publication', '/', '/desktop/publication', '/desktop/publication')) {
    $samePage = $navigation.Route -eq $route
    $raises = $viewsByRoute[$route].Raises
    Show-ConstructorPage $route
    $visible = @($viewsByRoute.Values | Where-Object Visible)
    if ($visible.Count -ne 1 -or $visible[0].Page -ne $route) { throw "Wrong page displayed for $route" }
    if ($samePage -and $viewsByRoute[$route].Raises -ne $raises) { throw 'Clicking the current page changed the view' }
    if (@($viewsByRoute.Values | Where-Object { $_.Draft -ne 'Retained configuration' }).Count) { throw 'Configuration was lost' }
}

$node = (Get-Command node -ErrorAction SilentlyContinue).Source
if (-not $node) { $node = 'C:/Program Files/nodejs/node.exe' }
if (-not (Test-Path -LiteralPath $node)) { throw 'Node.js is required for navigation message checks' }
$testFile = [IO.Path]::GetTempFileName()
try {
    @'
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const messages=[];let click;
const document={querySelector:()=>({hidden:true}),addEventListener:(type,handler)=>{if(type==='click')click=handler;},getElementById:()=>({})};
const location={href:'http://127.0.0.1:8765/',origin:'http://127.0.0.1:8765'};
const window={chrome:{webview:{postMessage:message=>messages.push(message)}}};
vm.runInNewContext(fs.readFileSync(process.argv[2],'utf8'),{document,location,window,URL,Set});
for(const route of ['/','/desktop/builds-page','/desktop/publication','/desktop/publication']){
 let prevented=false;
 click({target:{closest:()=>({href:location.origin+route})},preventDefault:()=>prevented=true});
 assert(prevented);assert.strictEqual(messages.at(-1).route,route);
}
const count=messages.length;
click({target:{closest:()=>({href:'https://example.com/desktop/publication'})},preventDefault:()=>assert.fail('External link intercepted')});
assert.strictEqual(messages.length,count);
console.log('Navigation messages match clicked pages');
'@ | Set-Content -LiteralPath $testFile -Encoding UTF8
    & $node $testFile (Join-Path $PSScriptRoot 'rdgenerator/templates/shell-nav.js')
    if ($LASTEXITCODE -ne 0) { throw 'Navigation message checks failed' }
} finally { Remove-Item -LiteralPath $testFile -Force }
'Page selection, repeated clicks and retained configuration: OK'
