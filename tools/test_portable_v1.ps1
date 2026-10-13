$ErrorActionPreference = "Stop"

$projectRoot = [System.IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$sourceFolder = Join-Path $projectRoot "release\Millonario_Educativo_V1"
$tempRoot = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath())
$testFolder = [System.IO.Path]::GetFullPath(
    (Join-Path $tempRoot "millonario-educativo-usb-smoke-v1")
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
    if (-not (Test-Path -LiteralPath $testExe)) {
        throw "La copia portátil no contiene el ejecutable."
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

    Write-Output "Prueba portátil superada desde: $testFolder"
}
finally {
    Remove-Item Env:\MILLONARIO_SMOKE_TEST -ErrorAction SilentlyContinue
    if (Test-Path -LiteralPath $testFolder) {
        Remove-Item -LiteralPath $testFolder -Recurse -Force
    }
}
