$ErrorActionPreference = "Stop"

$v3Root = [System.IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$projectRoot = [System.IO.Path]::GetFullPath((Split-Path -Parent $v3Root))
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$entryPoint = Join-Path $v3Root "main.py"
$distRoot = Join-Path $v3Root "dist"
$releaseRoot = Join-Path $projectRoot "release"
$portableFolder = Join-Path $releaseRoot "Millonario_Educativo_V3_1"
$portableExe = Join-Path $portableFolder "MillonarioEducativoV3_1.exe"
$sourceRoot = Join-Path $v3Root "src"
$previousPythonPath = $env:PYTHONPATH

if (-not (Test-Path -LiteralPath $python)) {
    throw "No existe el entorno de construcción .venv."
}

Push-Location $v3Root
try {
    $env:PYTHONPATH = if ($previousPythonPath) {
        "$sourceRoot$([System.IO.Path]::PathSeparator)$previousPythonPath"
    }
    else {
        $sourceRoot
    }
    # Uvicorn resuelve estos backends mediante cadenas en tiempo de ejecución.
    # FastAPI, Starlette, Pydantic, WebSockets y Segno se detectan por imports normales.
    & $python -m nuitka `
        --standalone `
        --enable-plugin=pyside6 `
        --include-qt-plugins=multimedia,platforminputcontexts,qml `
        --noinclude-dlls=Qt63D* `
        --noinclude-dlls=Qt65Compat* `
        --noinclude-dlls=Qt6Charts* `
        --noinclude-dlls=Qt6DataVisualization* `
        --noinclude-dlls=Qt6Graphs* `
        --noinclude-dlls=Qt6Location* `
        --noinclude-dlls=Qt6Pdf* `
        --noinclude-dlls=Qt6Positioning* `
        --noinclude-dlls=Qt6Quick3D* `
        --noinclude-dlls=Qt6Sensors* `
        --noinclude-dlls=Qt6Test* `
        --noinclude-dlls=Qt6TextToSpeech* `
        --noinclude-dlls=Qt6WebChannel* `
        --noinclude-dlls=Qt6WebEngine* `
        --noinclude-dlls=Qt6WebSockets* `
        --noinclude-dlls=Qt6WebView* `
        --noinclude-dlls=*/qml/QtQuickEffectMaker/* `
        --noinclude-qt-translations `
        --include-package=millonario_v3 `
        --include-module=uvicorn.loops.asyncio `
        --include-module=uvicorn.protocols.http.h11_impl `
        --include-module=uvicorn.protocols.websockets.websockets_sansio_impl `
        --include-module=uvicorn.lifespan.on `
        --include-data-dir=qml=qml `
        --include-data-dir=assets=assets `
        --include-data-dir=templates=templates `
        --include-data-dir=mobile=mobile `
        --include-data-files=projects/demo.juego=projects/demo.juego `
        --output-dir=$distRoot `
        --output-filename=MillonarioEducativoV3_1.exe `
        --windows-console-mode=disable `
        --windows-icon-from-ico=assets/icons/millonario.ico `
        --company-name="Proyecto educativo privado" `
        --product-name="Millonario educativo V3.1.4" `
        --file-description="Juego audiovisual participativo con sala local" `
        --file-version=3.1.4.0 `
        --product-version=3.1.4.0 `
        --assume-yes-for-downloads `
        --remove-output `
        $entryPoint

    if ($LASTEXITCODE -ne 0) {
        throw "Nuitka terminó con código $LASTEXITCODE."
    }
    $builtFolder = Join-Path $distRoot "main.dist"
    if (-not (Test-Path -LiteralPath $builtFolder)) {
        throw "La compilación terminó sin producir main.dist."
    }
    if (-not (Test-Path -LiteralPath $releaseRoot)) {
        New-Item -ItemType Directory -Path $releaseRoot | Out-Null
    }

    $resolvedReleaseRoot = [System.IO.Path]::GetFullPath($releaseRoot)
    $resolvedPortableFolder = [System.IO.Path]::GetFullPath($portableFolder)
    if (-not $resolvedPortableFolder.StartsWith(
        $resolvedReleaseRoot + [System.IO.Path]::DirectorySeparatorChar,
        [System.StringComparison]::OrdinalIgnoreCase
    )) {
        throw "La salida V3.1 no está contenida en release."
    }
    if ($resolvedPortableFolder -like "*Millonario_Educativo_V2*") {
        throw "La construcción V3.1 no puede apuntar a la carpeta V2."
    }

    if (Test-Path -LiteralPath $portableFolder) {
        Remove-Item -LiteralPath $portableFolder -Recurse -Force
    }
    Move-Item -LiteralPath $builtFolder -Destination $portableFolder
    New-Item -ItemType Directory -Force `
        -Path (Join-Path $portableFolder "data\sessions"), `
              (Join-Path $portableFolder "data\runtime") | Out-Null

    Copy-Item -LiteralPath (Join-Path $v3Root "DISTRIBUCION_LEEME_V3_1.txt") `
        -Destination (Join-Path $portableFolder "LEEME.txt")
    $closingReport = Join-Path $v3Root "INFORME_CIERRE_V3_1.md"
    if (Test-Path -LiteralPath $closingReport) {
        Copy-Item -LiteralPath $closingReport `
            -Destination (Join-Path $portableFolder "INFORME_CIERRE_V3_1.md")
    }
    $reportedErrors = Join-Path $v3Root "docs\errores_reportados"
    if (Test-Path -LiteralPath $reportedErrors) {
        Copy-Item -LiteralPath $reportedErrors `
            -Destination (Join-Path $portableFolder "errores") `
            -Recurse
    }

    if (-not (Test-Path -LiteralPath $portableExe)) {
        throw "No se encontró el ejecutable portátil V3.1."
    }
    Write-Output $portableFolder
}
finally {
    if ($null -eq $previousPythonPath) {
        Remove-Item Env:\PYTHONPATH -ErrorAction SilentlyContinue
    }
    else {
        $env:PYTHONPATH = $previousPythonPath
    }
    Pop-Location
}
