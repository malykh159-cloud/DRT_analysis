param([string]$Name = 'DRTAnalyzer')
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$pythonExe = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonExe)) { throw 'Create .venv and install requirements-dev.txt first.' }
if ($Name -notmatch '^[A-Za-z0-9_-]+$') { throw 'Build name must contain only letters, numbers, underscores and hyphens.' }
if (Get-Process -Name $Name -ErrorAction SilentlyContinue) { throw "Close $Name.exe before rebuilding." }
$env:OPENBLAS_NUM_THREADS = '1'
$env:OMP_NUM_THREADS = '1'
& $pythonExe -m pytest -q
if ($LASTEXITCODE -ne 0) { throw 'Tests failed; build stopped.' }
$buildArgs = @('-m', 'PyInstaller', '--noconfirm', '--onedir', '--windowed', '--name', $Name,
    '--paths', 'src', '--add-data', 'docs;docs', '--add-data', 'README.md;.',
    '--add-data', 'CHANGELOG.md;.', '--add-data', 'THIRD_PARTY_NOTICES.md;.',
    '--hidden-import', 'PySide6.QtSvg')
foreach ($packageName in @('numpy', 'scipy', 'PySide6', 'PySide6_Essentials', 'PySide6_Addons', 'shiboken6', 'pyqtgraph', 'openpyxl')) {
    $buildArgs += @('--copy-metadata', $packageName)
}
$buildArgs += @('--exclude-module', 'PySide6.QtWebEngineCore', '--exclude-module', 'PySide6.QtWebEngineWidgets',
    '--exclude-module', 'PySide6.QtPdf', '--exclude-module', 'tkinter', '--exclude-module', 'matplotlib',
    '--exclude-module', 'pytest', '--exclude-module', '_pytest', '--exclude-module', 'pyqtgraph.opengl', 'run.py')
& $pythonExe @buildArgs
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed.' }
$distribution = Join-Path $PSScriptRoot "dist\$Name"
# Also place documentation next to the exe for normal file browsing.
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'docs') -Destination $distribution -Recurse -Force
foreach ($document in @('README.md', 'CHANGELOG.md', 'THIRD_PARTY_NOTICES.md')) {
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot $document) -Destination $distribution -Force
}
$smokeOutput = Join-Path $PSScriptRoot "artifacts\portable_smoke_$Name"
$smokeProcess = Start-Process -FilePath (Join-Path $distribution "$Name.exe") -ArgumentList @('--smoke-test', '--output', "`"$smokeOutput`"") -WindowStyle Hidden -Wait -PassThru
if ($smokeProcess.ExitCode -ne 0) { throw "Portable smoke test failed ($($smokeProcess.ExitCode)); inspect logs." }
Write-Host "Verified portable application: $distribution\$Name.exe"
