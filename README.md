Manager para coordinar `translator` → `minify_assets` → `html-2-pdf` (GUI + CLI)

Descripción

- Interfaz mínima y CLI para orquestar la traducción, minificación y generación de PDFs del proyecto. Soporta múltiples archivos objetivo y selección automática de la versión más reciente de cada script en `dev/scripts`.

Modos de uso

- GUI (por defecto si no pasas targets):

```bash
python dev/manager/manager.py
```

- Botones: `Run Translator`, `Run Minify`, `Run HTML→PDF`, `Run All`.
- `Select...` permite seleccionar múltiples archivos para vigilar (se guardan separados por `;`).
- `Start Watching` vigila todos los targets seleccionados y ejecuta la cadena si cualquiera cambia.

- CLI (watching / once) — varios targets:

```bash
python dev/manager/manager.py js/cv_data.js js/projects-opti.js --once --no-html
```

- `--once` ejecuta la cadena una vez y sale.
- `--no-html` evita lanzar el generador HTML→PDF (útil en servidores o CI).

Cómo selecciona los scripts

- Busca en las carpetas de `dev/scripts` y:
  - si hay ficheros con prefijo numérico (ej. `9_...py`) elige el de prefijo más alto;
  - si no hay prefijos, elige `name_hint` si existe (p.ej. `translator.py`), o el más reciente por fecha.

Notas técnicas

- El manager detecta cambios usando hash SHA256 por archivo.
- `Run HTML→PDF` lanza el script con `interactive=True` (se abre la GUI del generador). Usa `--no-html` para omitirlo.

Ejemplo de flujo recomendado

1. Abrir GUI: `python dev/manager/manager.py`.
2. `Select...` — elegir `js/cv_data.js` y `js/projects-opti.js`.
3. `Detect Scripts` para refrescar las rutas a los scripts.
4. `Start Watching` o usar `Run All` para ejecutar la cadena manualmente.
5. `Open Portfolio Updater` abre la versión más reciente de la herramienta GUI para editar datasets (`dev/scripts/portfolio-updater.py`). Útil para revisar/editar datos antes o después de la ejecución automática.
