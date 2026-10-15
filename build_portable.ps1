param([string]$Name = 'DRTAnalyzer')
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$pythonExe = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonExe)) { throw 'Create .venv and install requirements-dev.txt first.' }
if ($Name -notmatch '^[A-Za-z0-9_-]+$') { throw 'Build name must contain only letters, numbers, underscores and hyphens.' }
if (Get-Process -Name $Name -ErrorAction SilentlyContinue) { throw "Close $Name.exe before rebuilding." }
$env:OPENBLAS_NUM_THREADS = '1'
$env:OMP_NUM_THREADS = '1'
# Only project Python and OS tools may participate in DLL discovery. A host
# PATH can contain Poppler/Conda ICU builds incompatible with Qt's Windows ICU.
$basePython = (& $pythonExe -c 'import sys; print(sys.base_prefix)').Trim()
if ($LASTEXITCODE -ne 0) { throw 'Cannot determine the base Python directory.' }
$env:PATH = @((Join-Path $PSScriptRoot '.venv\Scripts'), $basePython,
    (Join-Path $basePython 'DLLs'), (Join-Path $env:SystemRoot 'System32'), $env:SystemRoot) -join ';'
& $pythonExe -m pytest -q
if ($LASTEXITCODE -ne 0) { throw 'Tests failed; build stopped.' }
$buildArgs = @('-m', 'PyInstaller', '--noconfirm', '--clean', '--noupx', '--onedir', '--windowed', '--name', $Name,
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
$verificationRoot = Join-Path $PSScriptRoot ("artifacts\portable_smoke_{0}_{1}" -f $Name, (Get-Date -Format 'yyyyMMdd_HHmmss_fff'))
New-Item -ItemType Directory -Path $verificationRoot -Force | Out-Null
& $pythonExe (Join-Path $PSScriptRoot 'scripts\verify_bundle.py') --name $Name --output (Join-Path $verificationRoot 'native_dependencies.json')
if ($LASTEXITCODE -ne 0) { throw 'Native dependency source verification failed.' }
$distribution = Join-Path $PSScriptRoot "dist\$Name"
# Also place documentation next to the exe for normal file browsing.
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'docs') -Destination $distribution -Recurse -Force
foreach ($document in @('README.md', 'CHANGELOG.md', 'THIRD_PARTY_NOTICES.md')) {
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot $document) -Destination $distribution -Force
}
$smokeProcess = Start-Process -FilePath (Join-Path $distribution "$Name.exe") -ArgumentList @('--smoke-test', '--output', "`"$verificationRoot`"") -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $verificationRoot 'stdout.txt') -RedirectStandardError (Join-Path $verificationRoot 'stderr.txt')
# Windows PowerShell can otherwise return a null ExitCode after WaitForExit.
# Keep a native process handle open before the short-lived child exits.
$null = $smokeProcess.Handle
if (-not $smokeProcess.WaitForExit(60000)) {
    $smokeProcess.Kill()
    throw "Portable smoke test timed out; inspect $verificationRoot."
}
if ($smokeProcess.ExitCode -ne 0) { throw "Portable smoke test failed ($($smokeProcess.ExitCode)); inspect $verificationRoot. Native startup errors are in stderr.txt." }
if (-not (Test-Path -LiteralPath (Join-Path $verificationRoot 'smoke_result.json'))) { throw 'Smoke result missing.' }
$smokeResult = Get-Content -LiteralPath (Join-Path $verificationRoot 'smoke_result.json') -Raw | ConvertFrom-Json
if (-not $smokeResult.passed) { throw 'Smoke result did not report success.' }
Write-Host "Verified portable application: $distribution\$Name.exe"
Write-Host "Verification artifacts: $verificationRoot"
