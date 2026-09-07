$ErrorActionPreference = 'Stop'
$taskRuntime = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\pythonw.exe'
if (-not (Test-Path -LiteralPath $taskRuntime)) {
    Add-Type -AssemblyName PresentationFramework
    [System.Windows.MessageBox]::Show('起動用Pythonが見つかりません。Codexに「ゲームリストの起動を直して」とお伝えください。', 'ゲームの棚') | Out-Null
    exit 1
}
Start-Process -FilePath $taskRuntime -ArgumentList @(('"' + (Join-Path $PSScriptRoot 'game_library.py') + '"'), '--open') -WorkingDirectory $PSScriptRoot -WindowStyle Hidden
