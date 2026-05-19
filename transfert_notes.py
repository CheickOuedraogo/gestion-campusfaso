#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Transfert de Notes - PV vers Examens (multi-fichiers)
Backups automatiques | Rapport d'Audit | Alertes aberrantes
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from tkinterdnd2 import TkinterDnD, DND_FILES
import pandas as pd
import os
import datetime
import shutil
import re

# ─── Paramètres Globaux ──────────────────────────────────────────────────────
DECIMAL_SEPARATOR = '.'
MIN_NOTE_ALERTE   = 0.0
MAX_NOTE_ALERTE   = 20.0

# ─── Couleurs & Style ────────────────────────────────────────────────────────
BG_DARK      = "#1a1a2e"
BG_CARD      = "#16213e"
BG_INPUT     = "#0f3460"
BG_DROP      = "#1a2c4e"
BG_ROW       = "#0d2240"
ACCENT       = "#e94560"
TEXT_LIGHT   = "#eaeaea"
TEXT_DIM     = "#8892b0"
SUCCESS      = "#00d2d3"
ERROR_COL    = "#ff6b6b"
BORDER       = "#233554"
LOG_BG       = "#0d1117"
LOG_INFO     = "#58a6ff"
LOG_OK       = "#3fb950"
LOG_WARN     = "#d29922"
LOG_ERR      = "#f85149"
LOG_DATA     = "#e3b341"


# ─── Utilitaires ─────────────────────────────────────────────────────────────

def detect_separator(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            lines = []
            for _ in range(10):
                line = f.readline()
                if not line:
                    break
                if line.strip():
                    lines.append(line.strip())
            if not lines:
                return ','
            sc_count = sum(l.count(';') for l in lines)
            co_count = sum(l.count(',') for l in lines)
            return ';' if sc_count >= co_count else ','
    except Exception:
        pass
    return ','


def load_file(filepath):
    ext = os.path.splitext(filepath)[1].lower()
    try:
        if ext in ('.xlsx', '.xls'):
            df = pd.read_excel(filepath, dtype=str, keep_default_na=False)
        elif ext == '.csv':
            sep = detect_separator(filepath)
            try:
                df = pd.read_csv(filepath, sep=sep, dtype=str, encoding='utf-8', keep_default_na=False)
            except pd.errors.ParserError as e:
                msg = str(e)
                match = re.search(r"line (\d+)", msg)
                line_data = ""
                if match:
                    line_num = int(match.group(1))
                    try:
                        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                            for i, line in enumerate(f, 1):
                                if i == line_num:
                                    line_data = f"\n\n👉 LIGNE {line_num} :\n{line.strip()}"
                                    break
                    except Exception:
                        pass
                raise ValueError(
                    f"Erreur de structure CSV.\nMessage : {msg}{line_data}\n\n"
                    f"Vérifiez les '{sep}' dans cette ligne."
                )
        else:
            raise ValueError(f"Format non supporté : {ext}")
        df.columns = [col.strip().lstrip('﻿') for col in df.columns]
        return df
    except Exception as e:
        if isinstance(e, ValueError):
            raise e
        raise ValueError(f"Erreur lecture fichier : {e}")


def save_file(df, filepath, sep=None):
    ext = os.path.splitext(filepath)[1].lower()
    if ext in ('.xlsx', '.xls'):
        df.to_excel(filepath, index=False)
    elif ext == '.csv':
        if sep is None:
            sep = detect_separator(filepath)
        df.to_csv(filepath, sep=sep, index=False, encoding='utf-8')


def normalize_note(value):
    if value is None or str(value).strip() in ('', 'nan', 'NaN', 'None'):
        return '0', False
    val = str(value).strip().replace(',', '.')
    try:
        num = float(val)
        is_aberrant = (num < MIN_NOTE_ALERTE or num > MAX_NOTE_ALERTE)
        formatted = str(int(num)) if num == int(num) else str(round(num, 4))
        formatted = formatted.replace('.', DECIMAL_SEPARATOR)
        return formatted, is_aberrant
    except ValueError:
        return val, True


# ─── Widgets ─────────────────────────────────────────────────────────────────

class DropZone(tk.Frame):
    """Zone de dépôt mono-fichier (pour le PV)."""
    def __init__(self, parent, text, command, **kwargs):
        super().__init__(parent, bg=BG_DROP, bd=1, highlightbackground=ACCENT, highlightthickness=1, **kwargs)
        self.command = command
        self.label = tk.Label(self, text=text, bg=BG_DROP, fg=TEXT_DIM, font=('Segoe UI', 11), cursor="hand2")
        self.label.pack(expand=True, fill='both', padx=10, pady=25)
        for w in (self, self.label):
            w.bind('<Button-1>', self._on_click)
            w.bind('<Enter>', self._on_hover)
            w.bind('<Leave>', self._on_leave)
        self.drop_target_register(DND_FILES)
        self.dnd_bind('<<Drop>>', self._on_drop)

    def _on_hover(self, _):
        self.configure(bg=BG_INPUT)
        self.label.configure(bg=BG_INPUT, fg=TEXT_LIGHT)

    def _on_leave(self, _):
        self.configure(bg=BG_DROP)
        self.label.configure(bg=BG_DROP, fg=TEXT_DIM)

    def _on_click(self, _):
        self.command()

    def _on_drop(self, event):
        file_list = self.tk.splitlist(event.data)
        if file_list:
            self.command(file_list[0])


class MultiDropZone(tk.Frame):
    """Zone de dépôt multi-fichiers (pour les examens)."""
    def __init__(self, parent, text, command_multiple, **kwargs):
        super().__init__(parent, bg=BG_DROP, bd=1, highlightbackground=ACCENT, highlightthickness=1, **kwargs)
        self.command_multiple = command_multiple
        self.label = tk.Label(self, text=text, bg=BG_DROP, fg=TEXT_DIM, font=('Segoe UI', 11), cursor="hand2")
        self.label.pack(expand=True, fill='both', padx=10, pady=20)
        for w in (self, self.label):
            w.bind('<Button-1>', self._on_click)
            w.bind('<Enter>', self._on_hover)
            w.bind('<Leave>', self._on_leave)
        self.drop_target_register(DND_FILES)
        self.dnd_bind('<<Drop>>', self._on_drop)

    def _on_hover(self, _):
        self.configure(bg=BG_INPUT)
        self.label.configure(bg=BG_INPUT, fg=TEXT_LIGHT)

    def _on_leave(self, _):
        self.configure(bg=BG_DROP)
        self.label.configure(bg=BG_DROP, fg=TEXT_DIM)

    def _on_click(self, _):
        paths = filedialog.askopenfilenames(
            title="Sél. Fichiers Examen",
            filetypes=[("CSV/Excel", "*.csv *.xlsx *.xls")]
        )
        if paths:
            self.command_multiple(list(paths))

    def _on_drop(self, event):
        file_list = self.tk.splitlist(event.data)
        if file_list:
            self.command_multiple(list(file_list))


# ─── Application Principale ──────────────────────────────────────────────────

class TransfertNotesApp:
    def __init__(self, root):
        self.root = root
        self.root.title("T.Notes — Sécurisé et Audit")
        self.root.geometry("900x860")
        self.root.configure(bg=BG_DARK)
        self.root.minsize(700, 600)

        self.pv_df            = None
        self.pv_filepath      = None
        self.pv_sep           = ','
        self.pv_matricule_col = None
        self.examen_entries   = []
        self.history          = []

        self.last_pv_note_col      = None
        self.last_examen_matricule = None
        self.last_examen_note_col  = None

        self._setup_styles()
        self._build_ui()
        self._log("info", "Application démarrée en mode sécurisé.")
        self._log("info", f"Séparateur décimal paramétré : « {DECIMAL_SEPARATOR} »")

    # ─── Styles ──────────────────────────────────────────────────────────────

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Dark.TFrame',      background=BG_DARK)
        style.configure('Card.TFrame',      background=BG_CARD)
        style.configure('Row.TFrame',       background=BG_ROW)
        style.configure('Title.TLabel',     background=BG_DARK,  foreground=TEXT_LIGHT, font=('Segoe UI', 17, 'bold'))
        style.configure('Subtitle.TLabel',  background=BG_DARK,  foreground=TEXT_DIM,   font=('Segoe UI', 10))
        style.configure('CardTitle.TLabel', background=BG_CARD,  foreground=TEXT_LIGHT, font=('Segoe UI', 12, 'bold'))
        style.configure('CardText.TLabel',  background=BG_CARD,  foreground=TEXT_DIM,   font=('Segoe UI', 10))
        style.configure('Info.TLabel',      background=BG_CARD,  foreground=SUCCESS,    font=('Segoe UI', 10, 'bold'))
        style.configure('History.TLabel',   background=BG_DARK,  foreground=SUCCESS,    font=('Segoe UI', 9))
        style.configure('Success.TButton',  background=SUCCESS,   foreground=BG_DARK,   font=('Segoe UI', 10, 'bold'), padding=(12, 7))
        style.map('Success.TButton', background=[('active', '#00b5b5'), ('disabled', BORDER)])

    # ─── UI ──────────────────────────────────────────────────────────────────

    def _build_ui(self):
        header = ttk.Frame(self.root, style='Dark.TFrame')
        header.pack(fill='x', padx=25, pady=(18, 4))
        ttk.Label(header, text="📋 Transfert Sécurisé", style='Title.TLabel').pack(anchor='w')
        ttk.Label(header, text="Multi-fichiers | Backups & Rapports Intégrés", style='Subtitle.TLabel').pack(anchor='w', pady=(2, 0))

        sep = tk.Frame(self.root, bg=ACCENT, height=2)
        sep.pack(fill='x', padx=25, pady=(8, 0))

        # Log en bas (packée avant la zone scrollable pour réserver l'espace)
        self._build_log_panel(self.root)

        # Zone scrollable principale
        main_frame = ttk.Frame(self.root, style='Dark.TFrame')
        main_frame.pack(fill='both', expand=True, padx=0, pady=(5, 0))

        self.main_canvas = tk.Canvas(main_frame, bg=BG_DARK, highlightthickness=0)
        sb = ttk.Scrollbar(main_frame, orient='vertical', command=self.main_canvas.yview)
        self.scroll_frame = ttk.Frame(self.main_canvas, style='Dark.TFrame')

        self.scroll_frame.bind(
            "<Configure>",
            lambda e: self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all"))
        )
        self.main_canvas.create_window((0, 0), window=self.scroll_frame, anchor='nw')
        self.main_canvas.configure(yscrollcommand=sb.set)
        self.main_canvas.pack(side='left', fill='both', expand=True, padx=(25, 0))
        sb.pack(side='right', fill='y', padx=(0, 5))

        self.main_canvas.bind_all("<Button-4>", lambda e: self.main_canvas.yview_scroll(-1, "units"))
        self.main_canvas.bind_all("<Button-5>", lambda e: self.main_canvas.yview_scroll(1, "units"))

        self._build_pv_section()
        self.examen_section  = ttk.Frame(self.scroll_frame, style='Dark.TFrame')
        self.history_section = ttk.Frame(self.scroll_frame, style='Dark.TFrame')

    def _build_log_panel(self, parent):
        log_outer = tk.Frame(parent, bg=BG_DARK)
        log_outer.pack(fill='x', side='bottom', padx=25, pady=(0, 10))

        log_header = tk.Frame(log_outer, bg=BG_CARD)
        log_header.pack(fill='x')
        tk.Label(
            log_header, text="🖥  Console", bg=BG_CARD, fg=TEXT_LIGHT,
            font=('Segoe UI', 10, 'bold')
        ).pack(side='left', padx=8, pady=6)
        tk.Button(
            log_header, text="Effacer", bg=BORDER, fg=TEXT_DIM, relief='flat',
            font=('Segoe UI', 8), cursor='hand2', command=self._clear_log
        ).pack(side='right', padx=8, pady=4)

        self.log_text = scrolledtext.ScrolledText(
            log_outer, bg=LOG_BG, fg='#c9d1d9', font=('Courier New', 9),
            relief='flat', bd=0, wrap='word', state='disabled', height=14
        )
        self.log_text.pack(fill='x')

        self.log_text.tag_configure('info', foreground=LOG_INFO)
        self.log_text.tag_configure('ok',   foreground=LOG_OK)
        self.log_text.tag_configure('warn', foreground=LOG_WARN)
        self.log_text.tag_configure('err',  foreground=LOG_ERR)
        self.log_text.tag_configure('data', foreground=LOG_DATA)
        self.log_text.tag_configure('dim',  foreground='#484f58')

    def _log(self, level, message):
        icons = {'info': 'ℹ', 'ok': '✓', 'warn': '⚠', 'err': '✗', 'data': '→'}
        ts = datetime.datetime.now().strftime('%H:%M:%S')
        self.log_text.configure(state='normal')
        self.log_text.insert('end', f"[{ts}] ", 'dim')
        self.log_text.insert('end', f"{icons.get(level, '·')} ", level)
        self.log_text.insert('end', f"{message}\n", level)
        self.log_text.configure(state='disabled')
        self.log_text.see('end')

    def _clear_log(self):
        self.log_text.configure(state='normal')
        self.log_text.delete('1.0', 'end')
        self.log_text.configure(state='disabled')

    # ─── Section PV ──────────────────────────────────────────────────────────

    def _build_pv_section(self):
        card = self._create_card(self.scroll_frame, "1️⃣ Fichier PV Général")

        self.pv_file_label = ttk.Label(card, text="Aucun PV chargé.", style='CardText.TLabel')
        self.pv_file_label.pack(anchor='w', pady=(0, 5))

        self.pv_dropzone = DropZone(card, text="📥 PV : Glissez le fichier ici (ou cliquez)", command=self._load_pv)
        self.pv_dropzone.pack(fill='x', pady=(0, 10))

        self.pv_matricule_frame = ttk.Frame(card, style='Card.TFrame')
        ttk.Label(self.pv_matricule_frame, text="Colonne Matricule :", style='CardText.TLabel').pack(anchor='w')
        self.pv_matricule_combo = ttk.Combobox(self.pv_matricule_frame, state='readonly', font=('Segoe UI', 10))
        self.pv_matricule_combo.pack(fill='x', pady=(3, 8))
        ttk.Button(
            self.pv_matricule_frame, text="✅ Valider", style='Success.TButton',
            command=self._validate_pv
        ).pack(anchor='e')

        self.pv_info_label = ttk.Label(card, text="", style='Info.TLabel')
        self.pv_info_label.pack(anchor='w', pady=(5, 0))

    def _load_pv(self, filepath=None):
        if not filepath:
            filepath = filedialog.askopenfilename(
                title="Sél. PV", filetypes=[("CSV/Excel", "*.csv *.xlsx *.xls")]
            )
            if not filepath:
                return
        self._log('info', f"Chargement PV : {os.path.basename(filepath)}")
        try:
            self.pv_sep = detect_separator(filepath) if filepath.lower().endswith('.csv') else ','
            self.pv_df  = load_file(filepath)
            self.pv_filepath = filepath
            columns = list(self.pv_df.columns)

            self.pv_file_label.configure(
                text=f"✅ {os.path.basename(filepath)} ({len(self.pv_df)} lignes)",
                foreground=SUCCESS
            )
            self.pv_dropzone.label.configure(text=f"Chargé : {os.path.basename(filepath)}")
            self.pv_matricule_combo['values'] = columns

            for i, col in enumerate(columns):
                if any(k in col.lower() for k in ('matricule', 'matric', 'num', 'immat', 'etud')):
                    self.pv_matricule_combo.current(i)
                    break
            else:
                if columns:
                    self.pv_matricule_combo.current(0)

            self.pv_matricule_frame.pack(fill='x', pady=(10, 0))
            self.examen_section.pack_forget()
            self.history_section.pack_forget()
            self._log('ok', f"PV chargé : {len(self.pv_df)} lignes | Colonnes : {', '.join(columns)}")

        except Exception as e:
            self._log('err', f"Erreur PV : {e}")
            messagebox.showerror("Erreur", f"Impossible de charger le PV :\n{e}")

    def _validate_pv(self):
        col = self.pv_matricule_combo.get()
        if not col:
            return
        self.pv_matricule_col = col
        unique = self.pv_df[col].nunique()
        self.pv_info_label.configure(text=f"✅ PV validé — {unique} matricules uniques dans « {col} »")
        self._log('ok', f"PV validé | Colonne matricule : « {col} » | {unique} entrées uniques")
        self._build_examen_section()
        self._build_history_section()

    # ─── Section Examens (multi-fichiers) ────────────────────────────────────

    def _build_examen_section(self):
        for w in self.examen_section.winfo_children():
            w.destroy()
        self.examen_entries.clear()
        self.examen_section.pack(fill='x', pady=(12, 0))

        card = self._create_card(self.examen_section, "2️⃣ Fichiers Examen (Réception)")

        # Colonne note PV partagée
        ttk.Label(
            card,
            text="Colonne NOTE dans le PV (source commune à tous les fichiers) :",
            style='CardText.TLabel'
        ).pack(anchor='w', pady=(0, 3))
        self.pv_note_combo = ttk.Combobox(
            card, state='readonly', font=('Segoe UI', 10), values=list(self.pv_df.columns)
        )
        self.pv_note_combo.pack(fill='x', pady=(0, 12))
        if self.last_pv_note_col and self.last_pv_note_col in self.pv_df.columns:
            self.pv_note_combo.set(self.last_pv_note_col)

        # Zone de dépôt multi-fichiers
        multi_drop = MultiDropZone(
            card,
            text="📥 Examens : Glissez les fichiers ici (ou cliquez — sélection multiple)",
            command_multiple=self._add_examen_files
        )
        multi_drop.pack(fill='x', pady=(0, 10))

        # Conteneur des lignes de fichiers
        self.examen_files_container = ttk.Frame(card, style='Card.TFrame')
        self.examen_files_container.pack(fill='x', pady=(4, 0))

        # Zone bouton transfert (rechargée dynamiquement)
        self.btn_transfer_frame = ttk.Frame(card, style='Card.TFrame')
        self.btn_transfer_frame.pack(fill='x', pady=(8, 0))

        self.transfer_result_label = ttk.Label(card, text="", style='Info.TLabel')
        self.transfer_result_label.pack(anchor='w', pady=(5, 0))

    def _add_examen_files(self, filepaths):
        for fp in filepaths:
            self._add_single_examen_entry(fp)

    def _add_single_examen_entry(self, filepath):
        self._log('info', f"Chargement examen : {os.path.basename(filepath)}")
        try:
            sep     = detect_separator(filepath) if filepath.lower().endswith('.csv') else ','
            df      = load_file(filepath)
            columns = list(df.columns)
        except Exception as e:
            self._log('err', f"Erreur chargement {os.path.basename(filepath)} : {e}")
            messagebox.showerror("Erreur", f"Impossible de charger :\n{os.path.basename(filepath)}\n\n{e}")
            return

        # Ligne de fichier
        row_outer = tk.Frame(
            self.examen_files_container, bg=BG_ROW, bd=0,
            highlightthickness=1, highlightbackground=BORDER
        )
        row_outer.pack(fill='x', pady=(0, 6))

        inner = tk.Frame(row_outer, bg=BG_ROW)
        inner.pack(fill='x', padx=10, pady=8)

        # Ligne titre + bouton supprimer
        title_row = tk.Frame(inner, bg=BG_ROW)
        title_row.pack(fill='x')
        tk.Label(
            title_row, text=f"📄 {os.path.basename(filepath)}",
            bg=BG_ROW, fg=TEXT_LIGHT, font=('Segoe UI', 9, 'bold')
        ).pack(side='left')
        tk.Label(
            title_row, text=f"  ({len(df)} lignes, {len(columns)} col.)",
            bg=BG_ROW, fg=TEXT_DIM, font=('Segoe UI', 9)
        ).pack(side='left')

        # Sélecteurs de colonnes
        cols_row = tk.Frame(inner, bg=BG_ROW)
        cols_row.pack(fill='x', pady=(6, 0))

        tk.Label(cols_row, text="Matricule :", bg=BG_ROW, fg=TEXT_DIM, font=('Segoe UI', 9)).pack(side='left', padx=(0, 4))
        mat_combo = ttk.Combobox(cols_row, state='readonly', font=('Segoe UI', 9), values=columns, width=20)
        mat_combo.pack(side='left', padx=(0, 14))

        tk.Label(cols_row, text="Note dest. :", bg=BG_ROW, fg=TEXT_DIM, font=('Segoe UI', 9)).pack(side='left', padx=(0, 4))
        note_combo = ttk.Combobox(cols_row, state='readonly', font=('Segoe UI', 9), values=columns, width=20)
        note_combo.pack(side='left')

        # Auto-sélection colonnes
        mat_set = False
        for i, col in enumerate(columns):
            if any(k in col.lower() for k in ('matricule', 'matric', 'num', 'immat', 'etud')):
                mat_combo.current(i)
                mat_set = True
                break
        if not mat_set:
            if self.last_examen_matricule and self.last_examen_matricule in columns:
                mat_combo.set(self.last_examen_matricule)
            elif columns:
                mat_combo.current(0)

        if self.last_examen_note_col and self.last_examen_note_col in columns:
            note_combo.set(self.last_examen_note_col)
        elif len(columns) > 1:
            note_combo.current(1)
        elif columns:
            note_combo.current(0)

        entry = {
            'filepath'  : filepath,
            'df'        : df,
            'sep'       : sep,
            'frame'     : row_outer,
            'mat_combo' : mat_combo,
            'note_combo': note_combo,
        }

        def make_remove(e):
            def _remove():
                e['frame'].destroy()
                if e in self.examen_entries:
                    self.examen_entries.remove(e)
                self._log('info', f"Fichier retiré : {os.path.basename(e['filepath'])}")
                self._refresh_transfer_btn()
            return _remove

        tk.Button(
            title_row, text="✕", bg=BG_ROW, fg=ERROR_COL, relief='flat',
            font=('Segoe UI', 9, 'bold'), cursor='hand2', command=make_remove(entry)
        ).pack(side='right')

        self.examen_entries.append(entry)
        self._log('ok', f"Examen chargé : {os.path.basename(filepath)} — {len(df)} lignes | Colonnes : {', '.join(columns)}")
        self._refresh_transfer_btn()

    def _refresh_transfer_btn(self):
        for w in self.btn_transfer_frame.winfo_children():
            w.destroy()
        if self.examen_entries:
            n = len(self.examen_entries)
            label = f"🚀 Transférer vers {n} fichier{'s' if n > 1 else ''}"
            ttk.Button(
                self.btn_transfer_frame, text=label,
                style='Success.TButton', command=self._execute_transfer
            ).pack(anchor='e', pady=(5, 0))

    # ─── Historique ──────────────────────────────────────────────────────────

    def _build_history_section(self):
        for w in self.history_section.winfo_children():
            w.destroy()
        if not self.history:
            return
        self.history_section.pack(fill='x', pady=(12, 20))
        card = self._create_card(self.history_section, "📜 Historique")
        for i, e in enumerate(reversed(self.history), 1):
            ttk.Label(
                card,
                text=f"  {i}. {e['examen_file']} → {e['matched']}/{e['total']} notes",
                style='History.TLabel'
            ).pack(anchor='w', pady=1)

    # ─── Utilitaire UI ───────────────────────────────────────────────────────

    def _create_card(self, parent, title):
        card = tk.Frame(parent, bg=BG_CARD, bd=0, highlightthickness=1, highlightbackground=BORDER)
        card.pack(fill='x', pady=(8, 0))
        inner = ttk.Frame(card, style='Card.TFrame')
        inner.pack(fill='x', padx=18, pady=14)
        ttk.Label(inner, text=title, style='CardTitle.TLabel').pack(anchor='w', pady=(0, 10))
        return inner

    # ─── Transfert ───────────────────────────────────────────────────────────

    def _execute_transfer(self):
        pv_note_col = self.pv_note_combo.get()
        if not pv_note_col:
            messagebox.showwarning("Attention", "Sélectionnez la colonne NOTE du PV.")
            return
        if not self.examen_entries:
            messagebox.showwarning("Attention", "Ajoutez au moins un fichier examen.")
            return
        for entry in self.examen_entries:
            if not entry['mat_combo'].get() or not entry['note_combo'].get():
                messagebox.showwarning(
                    "Attention",
                    f"Colonnes non sélectionnées pour :\n{os.path.basename(entry['filepath'])}"
                )
                return

        try:
            # Construction de l'index PV (une seule fois)
            pv_notes = {}
            for _, row in self.pv_df.iterrows():
                mat = str(row[self.pv_matricule_col]).strip()
                if mat and mat.lower() not in ('nan', 'none'):
                    pv_notes[mat.lower()] = row.get(pv_note_col, '')

            self._log('info', f"━━━ DÉBUT TRANSFERT — {len(self.examen_entries)} fichier(s) | Col. PV : « {pv_note_col} » ━━━")
            self._log('data', f"Index PV construit : {len(pv_notes)} entrées matricule → note")

            # Dry-run sur tous les fichiers
            all_results = []
            total_matched = total_not_found = total_overwritten = total_aberrants = 0

            for entry in self.examen_entries:
                ex_mat_col = entry['mat_combo'].get()
                ex_not_col = entry['note_combo'].get()
                fname      = os.path.basename(entry['filepath'])

                matched = not_found = overwritten = aberrants = 0
                audit_lines = [
                    "=== RAPPORT D'AUDIT DE TRANSFERT ===",
                    f"Date        : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    f"Fichier PV  : {self.pv_filepath} (col. note: {pv_note_col})",
                    f"Fichier Exam: {entry['filepath']} (col. dest: {ex_not_col})",
                    "─────────────────────────────────────",
                ]

                preview_df = entry['df'].copy()

                for idx in preview_df.index:
                    raw_mat  = str(preview_df.at[idx, ex_mat_col]).strip()
                    key      = raw_mat.lower()
                    old_note = str(preview_df.at[idx, ex_not_col]).strip()

                    if key in pv_notes:
                        note_str, is_aberr = normalize_note(pv_notes[key])
                        preview_df.at[idx, ex_not_col] = note_str
                        matched += 1
                        if old_note not in ('', '0', 'nan', 'NaN') and old_note != note_str:
                            overwritten += 1
                            audit_lines.append(f"[ÉCRASEMENT]  {raw_mat} : {old_note} → {note_str}")
                        else:
                            audit_lines.append(f"[TRANSFÉRÉ]   {raw_mat} : → {note_str}")
                        if is_aberr:
                            aberrants += 1
                            audit_lines.append(f"[! ABERRANT!] {raw_mat} : {note_str}")
                    else:
                        preview_df.at[idx, ex_not_col] = '0'
                        not_found += 1
                        audit_lines.append(f"[NON TROUVÉ]  {raw_mat} → forcé à 0")

                preview_df[ex_not_col] = preview_df[ex_not_col].apply(
                    lambda x: '0' if str(x).strip() in ('', 'nan', 'NaN') else str(x)
                )

                all_results.append({
                    'entry'       : entry,
                    'preview_df'  : preview_df,
                    'matched'     : matched,
                    'not_found'   : not_found,
                    'overwritten' : overwritten,
                    'aberrants'   : aberrants,
                    'audit_lines' : audit_lines,
                    'ex_mat_col'  : ex_mat_col,
                    'ex_not_col'  : ex_not_col,
                })
                total_matched     += matched
                total_not_found   += not_found
                total_overwritten += overwritten
                total_aberrants   += aberrants

            # Écran de confirmation
            files_summary = "\n".join(
                f"  • {os.path.basename(r['entry']['filepath'])} : "
                f"{r['matched']} trouvés, {r['not_found']} manquants"
                for r in all_results
            )
            msg = (
                f"⚠️ PRÉVISUALISATION — {len(all_results)} fichier(s)\n\n"
                f"{files_summary}\n\n"
                f"Totaux :\n"
                f"▶ Notes trouvées         : {total_matched}\n"
                f"▶ Non trouvées (→ 0)     : {total_not_found}\n"
                f"▶ Notes écrasées         : {total_overwritten}\n"
                f"▶ Valeurs aberrantes     : {total_aberrants}\n\n"
                f"Un backup automatique sera créé par fichier avant sauvegarde.\n"
                f"Souhaitez-vous continuer ?"
            )

            if not messagebox.askyesno("Confirmation de sécurité", msg, icon='warning'):
                self._log('warn', "Transfert annulé par l'utilisateur.")
                return

            # Exécution
            backup_tag = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

            for res in all_results:
                entry = res['entry']
                fname = os.path.basename(entry['filepath'])
                base_name, ext = os.path.splitext(entry['filepath'])

                # Backup
                backup_path = f"{base_name}_backup_{backup_tag}{ext}"
                shutil.copyfile(entry['filepath'], backup_path)
                self._log('ok', f"[{fname}] Backup → {os.path.basename(backup_path)}")

                # Sauvegarde
                save_file(res['preview_df'], entry['filepath'], sep=entry['sep'])
                self._log('ok', f"[{fname}] Sauvegardé — {res['matched']} notes écrites, {res['not_found']} → 0")

                if res['overwritten']:
                    self._log('warn', f"[{fname}] {res['overwritten']} note(s) écrasée(s)")
                if res['aberrants']:
                    self._log('warn', f"[{fname}] {res['aberrants']} valeur(s) aberrante(s)")

                # Log détaillé ligne par ligne
                for line in res['audit_lines']:
                    if line.startswith('[TRANSFÉRÉ]'):
                        self._log('data', line)
                    elif line.startswith('[ÉCRASEMENT]'):
                        self._log('warn', line)
                    elif line.startswith('[NON TROUVÉ]'):
                        self._log('warn', line)
                    elif line.startswith('[! ABERRANT'):
                        self._log('err', line)

                # Rapport d'audit
                audit_path = f"{base_name}_audit_{backup_tag}.txt"
                with open(audit_path, 'w', encoding='utf-8') as f:
                    f.write("\n".join(res['audit_lines']))
                self._log('info', f"[{fname}] Audit → {os.path.basename(audit_path)}")

                self.last_pv_note_col      = pv_note_col
                self.last_examen_matricule = res['ex_mat_col']
                self.last_examen_note_col  = res['ex_not_col']

                self.history.append({
                    'examen_file': fname,
                    'pv_col'     : pv_note_col,
                    'examen_col' : res['ex_not_col'],
                    'matched'    : res['matched'],
                    'total'      : len(res['preview_df']),
                })

                entry['df'] = res['preview_df'].copy()

            self._log('ok', f"━━━ TRANSFERT TERMINÉ — {len(all_results)} fichier(s) | {total_matched} notes écrites ━━━")

            self.transfer_result_label.configure(
                text=f"✅ {total_matched} notes transférées vers {len(all_results)} fichier(s)"
            )
            messagebox.showinfo(
                "Succès",
                f"Transfert terminé !\n\n"
                f"• {len(all_results)} fichier(s) traité(s)\n"
                f"• {total_matched} notes écrites au total\n"
                f"• {total_not_found} matricules non trouvés (→ 0)\n\n"
                f"Backups & rapports d'audit dans les mêmes dossiers."
            )
            self._build_history_section()

        except Exception as e:
            self._log('err', f"Erreur critique : {e}")
            messagebox.showerror("Erreur Critique", str(e))


def main():
    root = TkinterDnD.Tk()
    try:
        root.tk.call('tk', 'scaling', 1.1)
    except Exception:
        pass
    app = TransfertNotesApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()
