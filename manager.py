import argparse
import hashlib
import os
import re
import subprocess
import sys
import time
import threading
import queue
import tkinter as tk
from tkinter import filedialog, scrolledtext


def abs_path(*parts):
    return os.path.abspath(os.path.join(*parts))


def file_hash(path):
    try:
        h = hashlib.sha256()
        with open(path, 'rb') as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()
    except FileNotFoundError:
        return None


def run_script(path, interactive=False):
    if not path:
        print("[!] Ruta de script no proporcionada.")
        return False
    if not os.path.exists(path):
        print(f"[!] Script no encontrado: {path}")
        return False

    print(f"-> Ejecutando: {path}")
    try:
        if interactive:
            subprocess.Popen([sys.executable, path])
            return True
        else:
            res = subprocess.run([sys.executable, path])
            return res.returncode == 0
    except Exception as e:
        print(f"[!] Error ejecutando {path}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Manager que coordina translator → minify → html2pdf")
    parser.add_argument('target', nargs='?', default='', help='Archivo a vigilar (ruta relativa o absoluta). Si se omite se abre la GUI')
    parser.add_argument('--gui', action='store_true', help='Forzar apertura de la interfaz GUI')
    parser.add_argument('--interval', type=float, default=2.0, help='Intervalo de comprobación en segundos')
    parser.add_argument('--once', action='store_true', help='Ejecutar la cadena una vez y salir')
    parser.add_argument('targets', nargs='*', help='Uno o varios archivos a vigilar (rutas). Si se omiten se abre la GUI')
    parser.add_argument('--no-html', action='store_true', help='No lanzar el generador HTML→PDF (evita GUI)')
    args = parser.parse_args()

    repo_root = abs_path(os.path.dirname(__file__), '..', '..')

    def find_latest_script(dir_path, name_hint=None):
        """Busca el archivo .py más adecuado en la carpeta:
        - Si hay ficheros con prefijo numérico (ej. '9_...py' o '01-...py'), elige el mayor.
        - Si no, intenta devolver `name_hint` si existe.
        - Si no, devuelve el más reciente por fecha de modificación.
        """
        if not os.path.isdir(dir_path):
            return None
        candidates = [f for f in os.listdir(dir_path) if f.endswith('.py')]
        if not candidates:
            return None

        # Buscar prefijos numéricos
        numbered = []
        for fn in candidates:
            m = re.match(r'^\s*(\d+)[_\-].*', fn)
            full = os.path.join(dir_path, fn)
            if m:
                try:
                    numbered.append((int(m.group(1)), os.path.getmtime(full), full))
                except Exception:
                    numbered.append((int(m.group(1)), 0, full))

        if numbered:
            numbered.sort(key=lambda x: (x[0], x[1]), reverse=True)
            return numbered[0][2]

        # Prefer hint name if present
        if name_hint:
            hint_path = os.path.join(dir_path, name_hint)
            if os.path.exists(hint_path):
                return hint_path

        # Fallback: más reciente por mtime
        full_paths = [os.path.join(dir_path, f) for f in candidates]
        full_paths.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        return full_paths[0]

    translator_script = find_latest_script(abs_path(repo_root, 'dev', 'scripts', 'translator'), 'translator.py')
    minify_script = find_latest_script(abs_path(repo_root, 'dev', 'scripts', 'asset-optimizer'), 'minify_assets.py')
    html2pdf_script = find_latest_script(abs_path(repo_root, 'dev', 'scripts', 'html-2-pdf'))

    # GUI implementation
    class ManagerGUI:
        def __init__(self, master, initial_target=None, interval=args.interval, no_html=args.no_html):
            self.master = master
            self.master.title('Manager: translator → minify → html2pdf')
            self.queue = queue.Queue()
            self.watch_thread = None
            self.watching = False
            self.interval = interval
            self.no_html = no_html

            # scripts
            self.translator_script = translator_script
            self.minify_script = minify_script
            self.html2pdf_script = html2pdf_script

            frm = tk.Frame(master, padx=10, pady=10)
            frm.pack(fill='both', expand=True)

            tk.Label(frm, text='Target file to watch:').grid(row=0, column=0, sticky='w')
            self.target_var = tk.StringVar(value=initial_target or '')
            tk.Entry(frm, textvariable=self.target_var, width=60).grid(row=0, column=1, sticky='we')
            tk.Button(frm, text='Select...', command=self.select_target).grid(row=0, column=2)

            tk.Label(frm, text='Interval (s):').grid(row=1, column=0, sticky='w')
            self.interval_var = tk.StringVar(value=str(self.interval))
            tk.Entry(frm, textvariable=self.interval_var, width=8).grid(row=1, column=1, sticky='w')

            # Script labels
            tk.Label(frm, text='Translator:').grid(row=2, column=0, sticky='w')
            self.lbl_trans = tk.Label(frm, text=self.translator_script or 'Not found', fg='blue')
            self.lbl_trans.grid(row=2, column=1, sticky='w')

            tk.Label(frm, text='Minify:').grid(row=3, column=0, sticky='w')
            self.lbl_min = tk.Label(frm, text=self.minify_script or 'Not found', fg='blue')
            self.lbl_min.grid(row=3, column=1, sticky='w')

            tk.Label(frm, text='HTML→PDF:').grid(row=4, column=0, sticky='w')
            self.lbl_pdf = tk.Label(frm, text=self.html2pdf_script or 'Not found', fg='blue')
            self.lbl_pdf.grid(row=4, column=1, sticky='w')

            # Buttons
            btn_fr = tk.Frame(frm)
            btn_fr.grid(row=5, column=0, columnspan=3, pady=(8,0))
            tk.Button(btn_fr, text='Run Translator', command=self.threaded(self.run_translator)).pack(side='left', padx=4)
            tk.Button(btn_fr, text='Run Minify', command=self.threaded(self.run_minify)).pack(side='left', padx=4)
            tk.Button(btn_fr, text='Run HTML→PDF', command=self.threaded(self.run_html)).pack(side='left', padx=4)
            tk.Button(btn_fr, text='Run All', command=self.threaded(self.run_all)).pack(side='left', padx=8)

            watch_fr = tk.Frame(frm)
            watch_fr.grid(row=6, column=0, columnspan=3, pady=(8,0))
            self.watch_btn = tk.Button(watch_fr, text='Start Watching', command=self.toggle_watch)
            self.watch_btn.pack(side='left')
            tk.Button(watch_fr, text='Detect Scripts', command=self.detect_scripts).pack(side='left', padx=6)
            tk.Button(watch_fr, text='Open Portfolio Updater', command=self.threaded(self.run_portfolio_updater)).pack(side='left', padx=6)

            # Log area
            tk.Label(frm, text='Log:').grid(row=7, column=0, sticky='nw')
            self.log = scrolledtext.ScrolledText(frm, height=12, width=80)
            self.log.grid(row=7, column=1, columnspan=2, pady=(6,0))
            self.log.config(state='disabled')

            self.master.protocol('WM_DELETE_WINDOW', self.on_close)
            self.master.after(200, self.process_queue)

        def select_target(self):
            paths = filedialog.askopenfilenames(title='Select one or more target files')
            if paths:
                # store as semicolon-separated
                self.target_var.set(';'.join(paths))
                self.log_msg(f'Selected {len(paths)} target(s)')

        def get_targets(self):
            raw = (self.target_var.get() or '').strip()
            if not raw:
                return []
            parts = [p.strip() for p in raw.split(';') if p.strip()]
            return parts

        def detect_scripts(self):
            # re-detect using existing functions
            repo_root = abs_path(os.path.dirname(__file__), '..', '..')
            self.translator_script = find_latest_script(abs_path(repo_root, 'dev', 'scripts', 'translator'), 'translator.py')
            self.minify_script = find_latest_script(abs_path(repo_root, 'dev', 'scripts', 'asset-optimizer'), 'minify_assets.py')
            self.html2pdf_script = find_latest_script(abs_path(repo_root, 'dev', 'scripts', 'html-2-pdf'))
            self.lbl_trans.config(text=self.translator_script or 'Not found')
            self.lbl_min.config(text=self.minify_script or 'Not found')
            self.lbl_pdf.config(text=self.html2pdf_script or 'Not found')
            self.log_msg('Scripts re-detectados')

        def log_msg(self, msg):
            self.queue.put(msg)

        def process_queue(self):
            try:
                while True:
                    msg = self.queue.get_nowait()
                    self.log.config(state='normal')
                    self.log.insert('end', msg + '\n')
                    self.log.see('end')
                    self.log.config(state='disabled')
            except queue.Empty:
                pass
            self.master.after(200, self.process_queue)

        def threaded(self, fn):
            def wrapper():
                t = threading.Thread(target=fn, daemon=True)
                t.start()
            return wrapper

        def run_translator(self):
            if not self.translator_script:
                self.log_msg('[!] Translator no encontrado')
                return
            self.log_msg('-> Ejecutando translator')
            ok = run_script(self.translator_script)
            self.log_msg(f'   Translator finished: {ok}')

        def run_minify(self):
            if not self.minify_script:
                self.log_msg('[!] Minify no encontrado')
                return
            self.log_msg('-> Ejecutando minify')
            ok = run_script(self.minify_script)
            self.log_msg(f'   Minify finished: {ok}')

        def run_html(self):
            if not self.html2pdf_script:
                self.log_msg('[!] HTML→PDF no encontrado')
                return
            if self.no_html:
                self.log_msg('-> Omitido HTML→PDF por configuración')
                return
            self.log_msg('-> Ejecutando HTML→PDF (interactivo)')
            ok = run_script(self.html2pdf_script, interactive=True)
            self.log_msg(f'   HTML→PDF launched: {ok}')

        def run_portfolio_updater(self):
            # find latest in portfolio-updater folder
            repo_root = abs_path(os.path.dirname(__file__), '..', '..')
            pu_dir = abs_path(repo_root, 'dev', 'scripts', 'portfolio-updater.py')
            pu_script = find_latest_script(pu_dir)
            if not pu_script:
                self.log_msg('[!] No se encontró portfolio-updater')
                return
            self.log_msg(f'-> Abriendo Portfolio Updater: {os.path.basename(pu_script)}')
            ok = run_script(pu_script, interactive=True)
            self.log_msg(f'   Portfolio Updater launched: {ok}')

        def run_all(self):
            self.log_msg('--- Run All started ---')
            self.run_translator()
            self.run_minify()
            self.run_html()
            self.log_msg('--- Run All finished ---')

        def toggle_watch(self):
            if not self.watching:
                targets = self.get_targets()
                if not targets:
                    self.log_msg('[!] No hay targets seleccionados para watch')
                    return
                missing = [t for t in targets if not os.path.exists(t)]
                if missing:
                    self.log_msg(f'[!] Targets no encontrados: {len(missing)}')
                    return
                try:
                    self.interval = float(self.interval_var.get())
                except Exception:
                    self.interval = 2.0
                self.watching = True
                self.watch_btn.config(text='Stop Watching')
                self.watch_thread = threading.Thread(target=self.watch_loop, daemon=True)
                self.watch_thread.start()
                # initialize last hashes
                self._last_hashes = {t: file_hash(t) for t in targets}
                self.log_msg(f'Watch iniciado para {len(targets)} target(s)')
            else:
                self.watching = False
                self.watch_btn.config(text='Start Watching')
                self.log_msg('Watch detenido')

        def watch_loop(self):
            while self.watching:
                time.sleep(self.interval)
                targets = self.get_targets()
                if not targets:
                    self.log_msg('[!] No hay targets para vigilar en watch_loop')
                    continue
                for t in targets:
                    cur = file_hash(t)
                    if cur is None:
                        self.log_msg(f'[!] Target eliminado: {t}')
                        self._last_hashes[t] = None
                        continue
                    if self._last_hashes.get(t) != cur:
                        self.log_msg(f'[+] Cambio detectado en: {t} (watch). Ejecutando cadena...')
                        self.run_all()
                        self._last_hashes[t] = cur

        def on_close(self):
            self.watching = False
            self.master.destroy()

    # If GUI requested, launch it
    if getattr(args, 'gui', False):
        root = tk.Tk()
        app = ManagerGUI(root, initial_target=args.target if 'target' in args else None, interval=args.interval, no_html=args.no_html)
        root.mainloop()
        return

    # Normalize targets list
    targets = args.targets or []

    if args.gui or not targets:
        root = tk.Tk()
        initial = None
        if targets:
            initial = ';'.join(targets)
        app = ManagerGUI(root, initial_target=initial, interval=args.interval, no_html=args.no_html)
        root.mainloop()
        return

    # Modo CLI: validar targets y seguir con el watch loop para múltiples archivos
    target_paths = [os.path.abspath(t) for t in targets]
    for p in target_paths:
        if not os.path.exists(p):
            print(f"[!] Archivo objetivo no existe: {p}")
            sys.exit(1)

    print(f"Vigilando: {', '.join(target_paths)}")

    last_hashes = {p: file_hash(p) for p in target_paths}
    if args.once:
        print("-- Ejecutando una vez (modo --once)")
        changed = True
    else:
        changed = False

    try:
        while True:
            if not args.once:
                time.sleep(args.interval)
                for p in target_paths:
                    current_hash = file_hash(p)
                    if current_hash is None:
                        print(f"[!] El archivo {p} desapareció. Esperando...")
                        last_hashes[p] = None
                        continue
                    if last_hashes.get(p) != current_hash:
                        print(f"[+] Cambio detectado en: {p}")
                        changed = True
                        last_hashes[p] = current_hash

            if changed:
                # 1) Traducir
                ok_trans = run_script(translator_script)

                # 2) Minificar
                ok_min = run_script(minify_script)

                # 3) HTML -> PDF (si está permitido)
                if not args.no_html:
                    print("-> Lanzando el generador HTML→PDF (puede abrir una GUI).")
                    run_script(html2pdf_script, interactive=True)
                else:
                    print("-> Omitido HTML→PDF por flag --no-html")

                print("[✔] Cadena finalizada. Esperando próximos cambios...")
                changed = False

            if args.once:
                break

    except KeyboardInterrupt:
        print("\nSaliendo por petición del usuario.")


if __name__ == '__main__':
    main()
