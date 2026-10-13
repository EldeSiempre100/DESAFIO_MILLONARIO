$ErrorActionPreference = "Stop"

$projectRoot = [System.IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$entryPoint = Join-Path $projectRoot "main.py"
$releaseRoot = Join-Path $projectRoot "release"
$portableFolder = Join-Path $releaseRoot "Millonario_Educativo_V1"
$portableExe = Join-Path $portableFolder "MillonarioEducativo.exe"

if (-not (Test-Path -LiteralPath $python)) {
    throw "No existe el entorno de construcción .venv."
}

Push-Location $projectRoot
try {
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
        --include-data-dir=qml=qml `
        --include-data-dir=assets=assets `
        --include-data-files=projects/demo.juego=projects/demo.juego `
        --output-dir=dist `
        --output-filename=MillonarioEducativo.exe `
        --windows-console-mode=disable `
        --windows-icon-from-ico=assets/icons/millonario.ico `
        --company-name="Proyecto educativo privado" `
        --product-name="Millonario educativo" `
        --file-description="Juego audiovisual editable V1" `
        --file-version=1.0.0.0 `
        --product-version=1.0.0.0 `
        --assume-yes-for-downloads `
        --remove-output `
        $entryPoint

    $builtFolder = Join-Path $projectRoot "dist\main.dist"
    if (-not (Test-Path -LiteralPath $builtFolder)) {
        throw "La compilación terminó sin producir dist\main.dist."
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
        throw "La carpeta de salida no está contenida en release."
    }

    if (Test-Path -LiteralPath $portableFolder) {
        Remove-Item -LiteralPath $portableFolder -Recurse -Force
    }

    Move-Item -LiteralPath $builtFolder -Destination $portableFolder

    if (-not (Test-Path -LiteralPath $portableExe)) {
        throw "No se encontró el ejecutable portátil esperado."
    }

    Copy-Item -LiteralPath (Join-Path $projectRoot "DISTRIBUCION_LEEME.txt") `
        -Destination (Join-Path $portableFolder "LEEME.txt")

    Write-Output $portableFolder
}
finally {
    Pop-Location
}
