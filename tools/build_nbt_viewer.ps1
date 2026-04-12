# 在 third_party/vscode-nbt 中构建 editor.js 并复制到 resources/web/nbt-viewer/
# 需已安装 Node.js（npm、npx 可用）。
$ErrorActionPreference = "Stop"
$env:Path = "$env:ProgramFiles\nodejs;$env:Path"
$root = Split-Path -Parent $PSScriptRoot
Set-Location "$root\third_party\vscode-nbt"
npm ci
npx rollup --config
$pkg = "$root\src\litematicaba\resources\web\nbt-viewer\editor.js"
Copy-Item -Force "out\editor.js" $pkg
Write-Host "OK: editor.js -> $pkg"
$dataOut = "$root\data\minecraft-assets\nbt-viewer\editor.js"
if (Test-Path (Split-Path $dataOut -Parent)) {
    Copy-Item -Force "out\editor.js" $dataOut
    Write-Host "OK: editor.js -> $dataOut (外置热更新)"
}
