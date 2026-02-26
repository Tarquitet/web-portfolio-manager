# ⚙️ Project Manager & Build Orchestrator

This repository contains the Project Manager — a hybrid CLI + GUI orchestrator that automates a local build workflow by chaining translation, minification and PDF generation into a single pipeline.

![1769443877856](images/README/1769443877856.png)

This manager watches key project files (for example `js/cv_data.js`) and, when changes are detected, runs a chained process that updates translations, minifies assets and regenerates export PDFs.

[![Leer en Español](https://img.shields.io/badge/Leer%20en%20Espa%C3%B1ol-ES-blue?style=flat-square&logo=github)](README_es.md)

## ✨ Key Features

- **Smart File Watcher:** Monitors multiple files in real-time using SHA-256 hashes to detect precise code changes.
- **Auto-Discovery of Scripts:** Automatically finds the most recent helper scripts in your `dev/scripts/` folder using numeric prefixes (for example, prefers `9_script.py` over `8_script.py`).
- **Hybrid Mode (GUI & CLI):** Use the graphical interface on desktop or integrate into automated pipelines via the terminal.
- **Threaded Execution:** Sub-script outputs are streamed to the GUI panel without freezing the interface.
- **Skip Heavy Steps:** Flags like `--no-html` allow skipping PDF generation when only compilation/minification is needed.

---

## ⚙️ Requirements & Installation

- Python 3.8 or newer.
- Standard Python libraries (`hashlib`, `threading`, `tkinter`). No external packages required by default.

Keep the manager in `dev/manager/` and helper scripts in `dev/scripts/` for the default discovery logic.

---

## 📖 Usage Guide

### GUI Mode

Run without arguments to open the GUI:

```bash
python dev/manager/manager.py
```

GUI actions:

- **Select...**: Choose file(s) to watch (e.g. `cv_data.js`).
- **Detect Scripts**: Refresh available helper scripts.
- **Run All**: Execute the full chain once.
- **Start Watching**: Begin background file watching; saving a watched file triggers the chain.

### Terminal Mode

Watch files in background (no GUI):

```bash
python dev/manager/manager.py js/cv_data.js js/projects-opti.js
```

Run once and exit (CI):

```bash
python dev/manager/manager.py js/cv_data.js --once
```

Run everything except PDF generation:

```bash
python dev/manager/manager.py js/cv_data.js --once --no-html
```

### Build Chain

When a watched file changes, the manager runs this sequence:

- 🌐 Translator: (`translator.py`) Updates language variants.
- ⚡ Minifier: (`minify_assets.py`) Generates minified JS/CSS.
- 📄 PDF Generator: (`HTML-2-PDF-Python.py`) Uses a headless browser to render HTML and produce optimized PDFs (skip with `--no-html`).
