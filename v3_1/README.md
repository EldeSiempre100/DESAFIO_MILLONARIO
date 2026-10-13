# Millonario educativo V3.1.4

Evolución participativa e independiente de la V2. La aplicación PySide6 sigue
siendo el anfitrión audiovisual y publica una sala local para un máximo oficial
de 30 teléfonos.

La revisión 3.1.1 simplifica el ingreso: el QR abre la única sala activa mediante
`http://IP:puerto/`, sin usar el código de sala como parte de la dirección.

La revisión 3.1.2 separa la vista previa de la pregunta y la apertura de los
pulsadores, además de recuperar correctamente los teléfonos que pierden
momentáneamente la conexión.

La revisión 3.1.3 abre la clasificación automáticamente durante 30 segundos al
cerrar la sala, clasifica dos jugadores sin desempate y permite repetir el juego
manteniendo todos los teléfonos enrolados.

La revisión 3.1.4 convierte la interfaz móvil en un pulsador genérico y agrega
ocho avatares seleccionables. La elección queda asociada al alias y aparece en
las pantallas del anfitrión.

## Desarrollo

Desde la carpeta global del proyecto:

```powershell
.\.venv\Scripts\python.exe .\v3_1\main.py
```

Pruebas:

```powershell
.\.venv\Scripts\python.exe -m pytest -q .\v3_1\tests
```

Construcción del paquete portable:

```powershell
.\v3_1\tools\build_v3_1.ps1
```

Prueba del ejecutable desde una copia temporal independiente:

```powershell
.\v3_1\tools\test_portable_v3_1.ps1
```

La salida utilizable se genera en
`release\Millonario_Educativo_V3_1`. Debe copiarse la carpeta completa, no
solamente el ejecutable.

La V2 estable permanece en `release\Millonario_Educativo_V2`.
