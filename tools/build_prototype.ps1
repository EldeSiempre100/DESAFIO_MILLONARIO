$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$entryPoint = Join-Path $projectRoot "main.py"
$outputDirectory = Join-Path $projectRoot "dist"

if (-not (Test-Path -LiteralPath $python)) {
    throw "No existe el entorno .venv del proyecto."
}

Push-Location $projectRoot
try {
    & $python -m nuitka `
        --standalone `
        --enable-plugin=pyside6 `
        --include-qt-plugins=multimedia,platforminputcontexts,qml `
        --include-data-dir=qml=qml `
        --include-data-dir=assets=assets `
        --include-data-files=projects/demo.juego=projects/demo.juego `
        --output-dir="$outputDirectory" `
        --output-filename=MillonarioEducativo.exe `
        --windows-console-mode=disable `
        --company-name="Proyecto educativo privado" `
        --product-name="Millonario educativo" `
        --file-description="Prototipo audiovisual editable" `
        --file-version=0.1.0.0 `
        --product-version=0.1.0.0 `
        --assume-yes-for-downloads `
        --remove-output `
        "$entryPoint"

    $executable = Join-Path $outputDirectory "main.dist\MillonarioEducativo.exe"
    if (-not (Test-Path -LiteralPath $executable)) {
        throw "Nuitka finalizó sin producir el ejecutable esperado."
    }
    Write-Output $executable
}
finally {
    Pop-Location
}
