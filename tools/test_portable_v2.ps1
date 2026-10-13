$ErrorActionPreference = "Stop"

$projectRoot = [System.IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$sourceFolder = Join-Path $projectRoot "release\Millonario_Educativo_V2"
$tempRoot = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath())
$testFolder = [System.IO.Path]::GetFullPath(
    (Join-Path $tempRoot "millonario-educativo-usb-smoke-v2")
)

if (-not $testFolder.StartsWith(
    $tempRoot,
    [System.StringComparison]::OrdinalIgnoreCase
)) {
    throw "La carpeta de prueba no está contenida en la carpeta temporal."
}

if (Test-Path -LiteralPath $testFolder) {
    throw "La carpeta temporal de prueba ya existe: $testFolder"
}

try {
    Copy-Item -LiteralPath $sourceFolder -Destination $testFolder -Recurse
    $testExe = Join-Path $testFolder "MillonarioEducativo.exe"
    $template = Join-Path $testFolder "templates\Banco_preguntas_V2.xlsx"
    if (-not (Test-Path -LiteralPath $testExe)) {
        throw "La copia portátil no contiene el ejecutable."
    }
    if (-not (Test-Path -LiteralPath $template)) {
        throw "La copia portátil no contiene la plantilla Excel."
    }

    $env:MILLONARIO_SMOKE_TEST = "1"
    $process = Start-Process `
        -FilePath $testExe `
        -WorkingDirectory $testFolder `
        -PassThru
    $process.WaitForExit()

    if ($process.ExitCode -ne 0) {
        throw "La copia portátil terminó con código $($process.ExitCode)."
    }

    Write-Output "Prueba portátil V2 superada desde: $testFolder"
}
finally {
    Remove-Item Env:\MILLONARIO_SMOKE_TEST -ErrorAction SilentlyContinue
    if (Test-Path -LiteralPath $testFolder) {
        Remove-Item -LiteralPath $testFolder -Recurse -Force
    }
}
