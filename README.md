# Millonario educativo — V2

Aplicación de escritorio privada y educativa basada en el PowerPoint de
referencia. La V2 conserva el juego y el editor de la V1, y agrega importación
desde Excel y rondas de cuatro preguntas con control de repeticiones.

## Funciones principales

- Menú inicial con **Iniciar juego** y **Editar preguntas**.
- Banco de hasta 12 preguntas.
- Rondas de cuatro preguntas.
- Historial persistente para reducir repeticiones.
- Con 12 preguntas, las tres primeras rondas no repiten contenido.
- Administrador manual para crear, duplicar, eliminar, ordenar y editar.
- Importación desde una plantilla Excel validada.
- Cuatro alternativas y respuesta correcta A–D.
- Comodines 50:50, llamada y público.
- Sonidos, temporizador, puntaje y cierre de ronda.
- Tres respaldos rotativos del banco de preguntas.

## Plantilla Excel

La plantilla válida está en:

`templates\Banco_preguntas_V2.xlsx`

Contiene una hoja **Preguntas** y otra de **Instrucciones**. No se deben cambiar
los nombres de la hoja ni de las columnas obligatorias.

Para cargarla:

1. Abrir la aplicación.
2. Seleccionar **Editar preguntas**.
3. Elegir **Importar banco desde Excel**.
4. Seleccionar el archivo `.xlsx`.
5. Pulsar **Cargar banco**.

La importación crea un respaldo antes de reemplazar el banco.

## Abrir en modo desarrollo

```powershell
.\.venv\Scripts\python.exe main.py
```

Atajos:

- `F11`: alternar pantalla completa.
- `Ctrl+E`: abrir el administrador manual.
- `Esc`: cerrar el editor o salir de pantalla completa.

## Pruebas

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

El resultado esperado es `24 passed`.

## Generar la versión portátil V2

```powershell
.\tools\build_v2.ps1
```

La salida queda en `release\Millonario_Educativo_V2\`. Se debe copiar la
carpeta completa al pendrive, no solamente el ejecutable.

Para simular el traslado a otra ubicación:

```powershell
.\tools\test_portable_v2.ps1
```

## Continuidad

- `src/millonario/excel_import.py`: lectura y validación del Excel.
- `src/millonario/rounds.py`: selección e historial de rondas.
- `src/millonario/controller.py`: coordinación del juego y la importación.
- `qml/Main.qml`: menú, juego, editor e importador.
- `templates/Banco_preguntas_V2.xlsx`: formato oficial de carga.
- `projects/demo.juego`: banco activo.
- `projects/demo.history.json`: historial generado durante el uso.
- `tools/build_v2.ps1`: construcción portable.
- `tools/test_portable_v2.ps1`: prueba desde otra ubicación.

La carpeta `release\Millonario_Educativo_V1` permanece intacta como respaldo de
la versión anterior.
