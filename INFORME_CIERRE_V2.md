# Informe de cierre — Millonario educativo V2

Fecha de cierre técnico: 29 de julio de 2026.

## Estado

La V2 quedó construida y validada como una aplicación de escritorio Windows,
privada, educativa, editable y portable. Mantiene la base audiovisual y
funcional de la V1 y agrega un banco ampliado, importación desde Excel y
selección de preguntas por rondas.

La versión lista para copiar está en:

`release\Millonario_Educativo_V2\`

Se debe copiar la carpeta completa. El archivo de inicio es:

`MillonarioEducativo.exe`

La V1 permanece intacta en `release\Millonario_Educativo_V1\`.

## Trabajo realizado

- Se conservó el menú inicial, la estética, los sonidos, el temporizador, los
  comodines y el administrador manual de preguntas.
- La opción **Editar preguntas** ahora permite elegir entre:
  - **Administrador manual**.
  - **Importar banco desde Excel**.
- Se eligió Excel `.xlsx` en lugar de Word, porque su estructura fija permite
  validar cada fila sin depender del formato visual del documento.
- Se creó `templates\Banco_preguntas_V2.xlsx` con instrucciones, listas
  desplegables y un banco demostrativo de 12 preguntas.
- El banco contiene cinco preguntas recuperadas del material original y siete
  ejemplos educativos nuevos. Los siete ejemplos están identificados en la
  columna **Observaciones** para su revisión antes de una actividad formal.
- El importador acepta entre 4 y 12 preguntas activas.
- Se validan los encabezados, el enunciado, las cuatro alternativas, la
  respuesta correcta A–D, los duplicados y los límites de texto.
- Al importar un banco válido se crea un respaldo del banco anterior.
- Cada partida utiliza una ronda de cuatro preguntas.
- El sistema registra el historial de rondas en
  `projects\demo.history.json`.
- Con un banco de 12 preguntas, las tres primeras rondas utilizan las 12
  preguntas sin repetir.
- Cuando se agota el banco, el sistema reutiliza primero las preguntas menos
  recientes.
- La importación de un banco nuevo reinicia el historial de rondas.
- Si el pendrive no permite escritura, el juego puede ejecutarse, pero no puede
  guardar ediciones ni mantener el historial para la siguiente ejecución.

## Plantilla oficial de carga

Archivo:

`templates\Banco_preguntas_V2.xlsx`

Hoja obligatoria:

`Preguntas`

Columnas:

1. `ID`
2. `Pregunta`
3. `Alternativa A`
4. `Alternativa B`
5. `Alternativa C`
6. `Alternativa D`
7. `Respuesta correcta`
8. `Activa`
9. `Observaciones`

No se deben cambiar el nombre de la hoja ni los encabezados. El archivo debe
guardarse como `.xlsx`.

## Validaciones realizadas

- 24 pruebas automáticas superadas.
- Importación correcta de las 12 preguntas de la plantilla.
- Rechazo de archivos con extensión o estructura inválida.
- Rechazo de bancos con más de 12 preguntas.
- Tres rondas consecutivas sin repetir preguntas con el banco de 12.
- Reutilización controlada después de agotar el banco.
- Reinicio del historial al importar un banco nuevo.
- Menú, selector de edición, importador, administrador y juego revisados
  visualmente.
- Corrección del estado visual de los botones en Windows.
- Copia completa ejecutada correctamente desde una carpeta temporal externa al
  proyecto, simulando su traslado y ejecución desde un pendrive.
- La versión distribuible inicia sin un historial previo, por lo que comienza
  en la ronda 1.

## Tamaño e integridad

- PowerPoint original: 9,3 MB.
- Carpeta portable V2: 204,8 MB.
- Ejecutable principal: 6,8 MB.
- Archivos de la carpeta portable: 2.678.

El ejecutable necesita las bibliotecas y recursos que lo acompañan. No se debe
copiar solamente el `.exe`.

SHA-256 de `MillonarioEducativo.exe`:

`762C985239596A3E0F2EFCB9AEE60CCC93C5739745DC60334DADD639E602EF5B`

## Uso desde un pendrive

1. Copiar completa la carpeta `release\Millonario_Educativo_V2`.
2. Abrir la carpeta copiada.
3. Ejecutar `MillonarioEducativo.exe`.
4. Usar **Iniciar juego** o **Editar preguntas**.
5. Cerrar la aplicación antes de retirar el pendrive.

El pendrive debe permitir escritura para conservar preguntas, respaldos e
historial. La aplicación no necesita instalación, Python, PowerPoint ni acceso
a Internet.

El ejecutable no está firmado digitalmente. Windows SmartScreen o la política
de seguridad de un equipo corporativo pueden solicitar confirmación o bloquear
su ejecución aunque el programa sea legítimo.

## Continuar manualmente si no está disponible Codex

Todo el trabajo está guardado en esta carpeta local y no depende de la
conversación.

### Abrir y ejecutar desde VS Code

1. Abrir esta carpeta completa en VS Code.
2. Abrir una terminal PowerShell.
3. Ejecutar:

```powershell
.\.venv\Scripts\python.exe main.py
```

### Modificar preguntas manualmente

1. Abrir la aplicación.
2. Pulsar **Editar preguntas**.
3. Elegir **Administrador manual**.
4. Seleccionar una pregunta.
5. Modificar el enunciado, las alternativas y la respuesta correcta.
6. Pulsar **Guardar cambios**.

El banco activo se guarda en `projects\demo.juego`.

### Importar desde Excel

1. Hacer una copia de `templates\Banco_preguntas_V2.xlsx`.
2. Completar entre 4 y 12 filas activas sin cambiar los encabezados.
3. Abrir la aplicación.
4. Pulsar **Editar preguntas**.
5. Elegir **Importar banco desde Excel**.
6. Seleccionar el archivo y pulsar **Cargar banco**.

### Ejecutar las pruebas

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

El resultado esperado es `24 passed`.

### Volver a construir la carpeta portable

```powershell
.\tools\build_v2.ps1
```

La construcción puede tardar varios minutos. Al finalizar reemplaza la carpeta
`release\Millonario_Educativo_V2`.

### Verificar la portabilidad

```powershell
.\tools\test_portable_v2.ps1
```

La prueba copia temporalmente la aplicación, la ejecuta desde otra ubicación y
elimina esa copia al terminar.

### Archivos principales

- `qml\Main.qml`: menú, juego, editor e importador.
- `src\millonario\controller.py`: coordinación general.
- `src\millonario\engine.py`: reglas y estados del juego.
- `src\millonario\model.py`: preguntas y validaciones.
- `src\millonario\storage.py`: guardado, respaldos y recuperación.
- `src\millonario\excel_import.py`: lectura y validación de Excel.
- `src\millonario\rounds.py`: selección e historial de rondas.
- `templates\Banco_preguntas_V2.xlsx`: formato oficial de carga.
- `projects\demo.juego`: banco activo de 12 preguntas.
- `tools\build_v2.ps1`: construcción de la versión portable.
- `tools\test_portable_v2.ps1`: prueba desde otra ubicación.

## Mejoras posibles para una versión posterior

- Elegir la cantidad de preguntas por ronda.
- Mostrar el historial de rondas dentro de la aplicación.
- Incorporar un botón para reiniciar manualmente el historial.
- Exportar el banco actual nuevamente a Excel.
- Firmar digitalmente el ejecutable para reducir advertencias de seguridad.
