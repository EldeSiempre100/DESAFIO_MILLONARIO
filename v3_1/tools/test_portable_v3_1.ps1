$ErrorActionPreference = "Stop"

$v3Root = [System.IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$projectRoot = [System.IO.Path]::GetFullPath((Split-Path -Parent $v3Root))
$sourceFolder = Join-Path $projectRoot "release\Millonario_Educativo_V3_1"
$tempRoot = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath())
$testFolder = [System.IO.Path]::GetFullPath(
    (Join-Path $tempRoot "millonario-educativo-usb-smoke-v3-1")
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
    $testExe = Join-Path $testFolder "MillonarioEducativoV3_1.exe"
    $template = Join-Path $testFolder "templates\Banco_preguntas_V2.xlsx"
    $mobile = Join-Path $testFolder "mobile\index.html"
    if (-not (Test-Path -LiteralPath $testExe)) {
        throw "La copia portátil no contiene el ejecutable."
    }
    if (-not (Test-Path -LiteralPath $template)) {
        throw "La copia portátil no contiene la plantilla Excel."
    }
    if (-not (Test-Path -LiteralPath $mobile)) {
        throw "La copia portátil no contiene los pulsadores móviles."
    }

    $env:MILLONARIO_START_GAME = "1"
    $env:MILLONARIO_SMOKE_TEST = "1"
    $env:MILLONARIO_SMOKE_TEST_MS = "8000"
    $process = Start-Process `
        -FilePath $testExe `
        -WorkingDirectory $testFolder `
        -WindowStyle Hidden `
        -PassThru

    $health = $null
    for ($attempt = 0; $attempt -lt 20; $attempt++) {
        Start-Sleep -Milliseconds 250
        try {
            $health = Invoke-RestMethod `
                -Uri "http://127.0.0.1:8787/health" `
                -TimeoutSec 1
            break
        }
        catch {
            if ($process.HasExited) {
                break
            }
        }
    }
    if ($null -eq $health -or $health.status -ne "ok") {
        throw "El servidor local de la copia portátil no respondió."
    }
    $page = Invoke-WebRequest `
        -UseBasicParsing `
        -Uri "http://127.0.0.1:8787/" `
        -TimeoutSec 2
    if ($page.Content -notmatch "Pulsador interactivo") {
        throw "La página móvil no fue publicada correctamente."
    }

    $process.WaitForExit()
    if ($process.ExitCode -ne 0) {
        throw "La copia portátil terminó con código $($process.ExitCode)."
    }
    $process.Dispose()
    Write-Output "Prueba portátil V3.1 superada desde: $testFolder"
}
finally {
    Remove-Item Env:\MILLONARIO_START_GAME -ErrorAction SilentlyContinue
    Remove-Item Env:\MILLONARIO_SMOKE_TEST -ErrorAction SilentlyContinue
    Remove-Item Env:\MILLONARIO_SMOKE_TEST_MS -ErrorAction SilentlyContinue
    for ($cleanupAttempt = 0; $cleanupAttempt -lt 20; $cleanupAttempt++) {
        if (-not (Test-Path -LiteralPath $testFolder)) {
            break
        }
        try {
            Remove-Item -LiteralPath $testFolder -Recurse -Force
            break
        }
        catch {
            if ($cleanupAttempt -eq 19) {
                throw
            }
            Start-Sleep -Milliseconds 250
        }
    }
}
