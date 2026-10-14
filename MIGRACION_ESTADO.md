# Migración Desafío Millonario

Origen privado: `EldeSiempre100/QUIEN_QUIERE_SER_` (solo lectura).

## Inventario verificado

Origen `main`: 176 archivos, commit `13c304f81aa0b3f47f02e6bf75fadd6a6bed2456`.
Destino antes de este ajuste: 159 archivos, 158 con hashes Git idénticos al origen y este informe adicional.

Se excluyen 5 documentos Word/PowerPoint y 3 capturas de diagnóstico en `v3_1/docs/errores_reportados/` que muestran nombre de usuario y dirección de sesión local. El conjunto público depurado requiere 168 rutas del origen. Faltan 10 rutas funcionales, equivalentes a 5 contenidos duplicados entre `assets/` y `v3_1/assets/`:

| Archivo relativo en ambos directorios | SHA Git | Tamaño |
| --- | --- | ---: |
| `audio/audience.wav` | `79e69f24e8ed6f69ceb3506c099e84a9a1d5d3b7` | 1.664.590 |
| `audio/question_music.mp3` | `42fb915793d0bf8f83681981620267903bba1bad` | 2.560.136 |
| `images/game_background_v2.png` | `2d32f505ecf97ea96d5725951e2250bd41e5bb31` | 1.686.328 |
| `images/game_background_v3_clean.png` | `547477bd27099f705611209e77196ae12abcf979` | 1.755.603 |
| `images/menu_background_v2.png` | `11438532fa4209bf5bcabf3df5df5ab4306a0a8f` | 1.811.345 |

El conector GitHub no entrega los bytes de archivos de más de 1 MB. La descarga ZIP del navegador no produjo un archivo accesible en el runtime. Hay que aportar una copia de esos cinco binarios o un archivo ZIP del origen para terminar y comprobar la integridad. No sustituirlos por marcadores ni excluirlos.

## Validación y despliegue

La sintaxis de 60 archivos Python transferidos se comprobó con AST. Las pruebas de ejecución aún no se han realizado porque faltan recursos y dependencias en el runtime. `render.yaml` del repositorio público apunta a `main`; el origen conserva su configuración. La aplicación FastAPI sirve el frontend y usa WebSockets, por lo que se recomienda un único servicio web Render. Falta configurar `ADMIN_PASSWORD` en Render, desplegar y comprobar salud, frontend y participación real. No hay publicación verificada.
