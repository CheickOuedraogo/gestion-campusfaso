#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Transfert de Notes - PV vers Examen
====================================
Outil GUI pour transférer les notes d'un fichier PV (procès-verbal)
vers des fichiers examen, en se basant sur les matricules étudiants.

Fonctionnalités avancées de sécurité:
- Variable de séparateur décimal modifiable
- Génération de Backups automatiques
- Rapport d'Audit détaillé
- Alertes valeurs aberrantes
- Prévisualisation avant écrasement
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
# C'est ici que tu peux modifier le séparateur pour l'EXPORT des notes.
# Change en ',' si tu souhaites avoir des virgules.
DECIMAL_SEPARATOR = '.'

# Seuils pour les "Valeurs aberrantes" (pour te prévenir si la note est bizarre)
MIN_NOTE_ALERTE = 0.0
MAX_NOTE_ALERTE = 20.0

# ─── Couleurs & Style ───────────────────────────────────────────────────────
BG_DARK      = "#1a1a2e"
BG_CARD      = "#16213e"
BG_INPUT     = "#0f3460"
BG_DROP      = "#1a2c4e"
ACCENT       = "#e94560"
ACCENT_HOVER = "#ff6b6b"
TEXT_LIGHT   = "#eaeaea"
TEXT_DIM     = "#8892b0"
SUCCESS      = "#00d2d3"
WARNING      = "#feca57"
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
    """
    Détecte le séparateur (';' ou ',') en analysant les premières lignes du fichier.
    """
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            # On analyse jusqu'à 10 lignes pour plus de robustesse
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
    """
    Charge un fichier Excel ou CSV avec gestion d'erreurs détaillée.
    """
    ext = os.path.splitext(filepath)[1].lower()
    
    try:
        if ext in ('.xlsx', '.xls'):
            df = pd.read_excel(filepath, dtype=str, keep_default_na=False)
        elif ext == '.csv':
            sep = detect_separator(filepath)
            try:
                df = pd.read_csv(filepath, sep=sep, dtype=str, encoding='utf-8', keep_default_na=False)
            except pd.errors.ParserError as e:
                # Analyse de l'erreur pour extraire la ligne problématique
                msg = str(e)
                match = re.search(r"line (\d+)", msg)
                line_data = ""
                if match:
                    line_num = int(match.group(1))
                    try:
                        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                            for i, line in enumerate(f, 1):
                                if i == line_num:
                                    line_data = f"\n\n👉 CONTENU DE LA LIGNE {line_num} :\n{line.strip()}"
                                    break
                    except:
                        pass
                
                raise ValueError(
                    f"Erreur de structure dans le CSV.\n"
                    f"Message : {msg}{line_data}\n\n"
                    f"Vérifiez s'il n'y a pas des '{sep}' en trop ou manquants dans cette ligne."
                )
        else:
            raise ValueError(f"Format non supporté : {ext}")

        # Nettoyage des noms de colonnes
        df.columns = [col.strip().lstrip('\ufeff') for col in df.columns]
        return df

    except Exception as e:
        # On propage l'erreur avec un message clair
        if isinstance(e, ValueError): raise e
        raise ValueError(f"Erreur lors de la lecture du fichier : {e}")


def save_file(df, filepath, sep=None):
    ext = os.path.splitext(filepath)[1].lower()
    if ext in ('.xlsx', '.xls'):
        df.to_excel(filepath, index=False)
    elif ext == '.csv':
        if sep is None:
            sep = detect_separator(filepath)
        df.to_csv(filepath, sep=sep, index=False, encoding='utf-8')


def normalize_note(value):
    """
    Normalise la note de manière sécurisée et dynamique selon la variable DECIMAL_SEPARATOR.
    Retourne la note formattée en chaîne de caractères, et un booléen indiquant si c'est une valeur aberrante.
    """
    if value is None or str(value).strip() in ('', 'nan', 'NaN', 'None'):
        return '0', False

    val = str(value).strip().replace(',', '.')

    try:
        num = float(val)
        is_aberrant = (num < MIN_NOTE_ALERTE or num > MAX_NOTE_ALERTE)

        if num == int(num):
            formatted = str(int(num))
        else:
            formatted = str(round(num, 4))
            
        # Remplacement dynamique final
        formatted = formatted.replace('.', DECIMAL_SEPARATOR)
        return formatted, is_aberrant
        
    except ValueError:
        # C'est probablement un texte ex: "Absent"
        return val, True


# ─── Zone Drop ───────────────────────────────────────────────────────────────

class DropZone(tk.Frame):
    def __init__(self, parent, text, command, **kwargs):
        super().__init__(parent, bg=BG_DROP, bd=1, highlightbackground=ACCENT, highlightthickness=1, **kwargs)
        self.command = command
        
        self.label = tk.Label(
            self, text=text, bg=BG_DROP, fg=TEXT_DIM, 
            font=('Segoe UI', 11), cursor="hand2"
        )
        self.label.pack(expand=True, fill='both', padx=10, pady=25)
        
        self.bind('<Button-1>', self._on_click)
        self.label.bind('<Button-1>', self._on_click)
        self.bind('<Enter>', self._on_hover)
        self.label.bind('<Enter>', self._on_hover)
        self.bind('<Leave>', self._on_leave)
        self.label.bind('<Leave>', self._on_leave)
        
        self.drop_target_register(DND_FILES)
        self.dnd_bind('<<Drop>>', self._on_drop)
        
    def _on_hover(self, e):
        self.configure(bg=BG_INPUT)
        self.label.configure(bg=BG_INPUT, fg=TEXT_LIGHT)

    def _on_leave(self, e):
        self.configure(bg=BG_DROP)
        self.label.configure(bg=BG_DROP, fg=TEXT_DIM)
        
    def _on_click(self, e):
        self.command()
        
    def _on_drop(self, event):
        paths = event.data
        if not paths:
            return
        file_list = self.tk.splitlist(paths)
        if file_list:
            filepath = file_list[0]
            self.command(filepath)


# ─── Application Principale ─────────────────────────────────────────────────

class TransfertNotesApp:
    def __init__(self, root):
        self.root = root
        self.root.title("T.Notes — Sécurisé et Audit")
        self.root.geometry("980x820")
        self.root.configure(bg=BG_DARK)
        self.root.minsize(860, 600)

        self.pv_df           = None
        self.pv_filepath     = None
        self.pv_sep          = ','
        self.pv_matricule_col = None
        self.history         = []

        self.last_examen_matricule = None
        self.last_pv_note_col      = None
        self.last_examen_note_col  = None

        self._setup_styles()
        self._build_ui()
        self._log("info", "Application démarrée en mode sécurisé.")
        self._log("info", f"Séparateur décimal paramétré : « {DECIMAL_SEPARATOR} »")

    # ─── Styles ──────────────────────────────────────────────────────────────

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')

        style.configure('Dark.TFrame',    background=BG_DARK)
        style.configure('Card.TFrame',    background=BG_CARD)
        style.configure('Title.TLabel',   background=BG_DARK,  foreground=TEXT_LIGHT, font=('Segoe UI', 17, 'bold'))
        style.configure('Subtitle.TLabel',background=BG_DARK,  foreground=TEXT_DIM,   font=('Segoe UI', 10))
        style.configure('CardTitle.TLabel',background=BG_CARD, foreground=TEXT_LIGHT, font=('Segoe UI', 12, 'bold'))
        style.configure('CardText.TLabel', background=BG_CARD, foreground=TEXT_DIM,   font=('Segoe UI', 10))
        style.configure('Info.TLabel',     background=BG_CARD, foreground=SUCCESS,    font=('Segoe UI', 10, 'bold'))
        style.configure('History.TLabel',  background=BG_DARK, foreground=SUCCESS,    font=('Segoe UI', 9))
        style.configure('Success.TButton', background=SUCCESS,  foreground=BG_DARK,   font=('Segoe UI', 10, 'bold'), padding=(12, 7))
        style.map('Success.TButton', background=[('active', '#00b5b5'), ('disabled', BORDER)])

    # ─── UI ──────────────────────────────────────────────────────────────────

    def _build_ui(self):
        header = ttk.Frame(self.root, style='Dark.TFrame')
        header.pack(fill='x', padx=25, pady=(18, 4))

        ttk.Label(header, text="📋 Transfert Sécurisé", style='Title.TLabel').pack(anchor='w')
        ttk.Label(header, text="Génération de Backups & Rapports Intégrés", style='Subtitle.TLabel').pack(anchor='w', pady=(2, 0))

        sep = tk.Frame(self.root, bg=ACCENT, height=2)
        sep.pack(fill='x', padx=25, pady=(8, 0))

        paned = tk.PanedWindow(self.root, orient='horizontal', bg=BG_DARK, sashwidth=6, sashrelief='flat', bd=0)
        paned.pack(fill='both', expand=True, padx=0, pady=5)

        left_frame = ttk.Frame(paned, style='Dark.TFrame')
        paned.add(left_frame, minsize=480)

        self.main_canvas = tk.Canvas(left_frame, bg=BG_DARK, highlightthickness=0)
        sb = ttk.Scrollbar(left_frame, orient='vertical', command=self.main_canvas.yview)
        self.scroll_frame = ttk.Frame(self.main_canvas, style='Dark.TFrame')

        self.scroll_frame.bind("<Configure>", lambda e: self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all")))
        self.main_canvas.create_window((0, 0), window=self.scroll_frame, anchor='nw')
        self.main_canvas.configure(yscrollcommand=sb.set)

        self.main_canvas.pack(side='left', fill='both', expand=True, padx=(25, 0))
        sb.pack(side='right', fill='y')

        self.main_canvas.bind_all("<Button-4>", lambda e: self.main_canvas.yview_scroll(-1, "units"))
        self.main_canvas.bind_all("<Button-5>", lambda e: self.main_canvas.yview_scroll(1, "units"))

        right_frame = tk.Frame(paned, bg=BG_DARK)
        paned.add(right_frame, minsize=280)
        self._build_log_panel(right_frame)

        self._build_pv_section()
        self.examen_section  = ttk.Frame(self.scroll_frame, style='Dark.TFrame')
        self.history_section = ttk.Frame(self.scroll_frame, style='Dark.TFrame')

    def _build_log_panel(self, parent):
        header = tk.Frame(parent, bg=BG_CARD)
        header.pack(fill='x', padx=(4, 20), pady=(6, 0))

        tk.Label(header, text="🖥  Console", bg=BG_CARD, fg=TEXT_LIGHT, font=('Segoe UI', 10, 'bold')).pack(side='left', padx=8, pady=6)

        btn_clear = tk.Button(header, text="Effacer", bg=BORDER, fg=TEXT_DIM, relief='flat', font=('Segoe UI', 8), cursor='hand2', command=self._clear_log)
        btn_clear.pack(side='right', padx=8, pady=4)

        self.log_text = scrolledtext.ScrolledText(parent, bg=LOG_BG, fg='#c9d1d9', font=('Courier New', 9), relief='flat', bd=0, wrap='word', state='disabled')
        self.log_text.pack(fill='both', expand=True, padx=(4, 20), pady=(2, 20))

        self.log_text.tag_configure('info',  foreground=LOG_INFO)
        self.log_text.tag_configure('ok',    foreground=LOG_OK)
        self.log_text.tag_configure('warn',  foreground=LOG_WARN)
        self.log_text.tag_configure('err',   foreground=LOG_ERR)
        self.log_text.tag_configure('data',  foreground=LOG_DATA)
        self.log_text.tag_configure('dim',   foreground='#484f58')

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

        btn_validate = ttk.Button(self.pv_matricule_frame, text="✅ Valider", style='Success.TButton', command=self._validate_pv)
        btn_validate.pack(anchor='e')

        self.pv_info_label = ttk.Label(card, text="", style='Info.TLabel')
        self.pv_info_label.pack(anchor='w', pady=(5, 0))

    def _build_examen_section(self):
        for w in self.examen_section.winfo_children():
            w.destroy()
        self.examen_section.pack(fill='x', pady=(12, 0))

        card = self._create_card(self.examen_section, "2️⃣ Fichier Examen (Réception)")
        self.examen_file_label = ttk.Label(card, text="Aucun examen chargé.", style='CardText.TLabel')
        self.examen_file_label.pack(anchor='w', pady=(0, 5))

        self.examen_dropzone = DropZone(card, text="📥 Examen : Glissez le fichier ici (ou cliquez)", command=self._load_examen)
        self.examen_dropzone.pack(fill='x', pady=(0, 10))

        self.examen_cols_frame = ttk.Frame(card, style='Card.TFrame')

        ttk.Label(self.examen_cols_frame, text="Colonne NOTE dans le PV (source) :", style='CardText.TLabel').pack(anchor='w', pady=(5, 0))
        self.pv_note_combo = ttk.Combobox(self.examen_cols_frame, state='readonly', font=('Segoe UI', 10))
        self.pv_note_combo.pack(fill='x', pady=(3, 8))

        ttk.Label(self.examen_cols_frame, text="Colonne MATRICULE Examen :", style='CardText.TLabel').pack(anchor='w')
        self.examen_matricule_combo = ttk.Combobox(self.examen_cols_frame, state='readonly', font=('Segoe UI', 10))
        self.examen_matricule_combo.pack(fill='x', pady=(3, 8))

        ttk.Label(self.examen_cols_frame, text="Colonne NOTE Examen (destination) :", style='CardText.TLabel').pack(anchor='w')
        self.examen_note_combo = ttk.Combobox(self.examen_cols_frame, state='readonly', font=('Segoe UI', 10))
        self.examen_note_combo.pack(fill='x', pady=(3, 8))

        btn_transfer = ttk.Button(self.examen_cols_frame, text="🚀 Valider et Sécuriser", style='Success.TButton', command=self._execute_transfer)
        btn_transfer.pack(anchor='e', pady=(5, 0))

        self.transfer_result_label = ttk.Label(card, text="", style='Info.TLabel')
        self.transfer_result_label.pack(anchor='w', pady=(5, 0))

    def _build_history_section(self):
        for w in self.history_section.winfo_children():
            w.destroy()
        if not self.history:
            return

        self.history_section.pack(fill='x', pady=(12, 20))
        card = self._create_card(self.history_section, "📜 Historique")

        for i, e in enumerate(reversed(self.history), 1):
            text = f"  {i}. {e['examen_file']} → {e['matched']}/{e['total']} notes"
            lbl = ttk.Label(card, text=text, style='History.TLabel')
            lbl.pack(anchor='w', pady=1)

    def _create_card(self, parent, title):
        card = tk.Frame(parent, bg=BG_CARD, bd=0, highlightthickness=1, highlightbackground=BORDER)
        card.pack(fill='x', pady=(8, 0))
        inner = ttk.Frame(card, style='Card.TFrame')
        inner.pack(fill='x', padx=18, pady=14)
        ttk.Label(inner, text=title, style='CardTitle.TLabel').pack(anchor='w', pady=(0, 10))
        return inner

    # ─── Actions ─────────────────────────────────────────────────────────────

    def _load_pv(self, filepath=None):
        if not filepath:
            filepath = filedialog.askopenfilename(title="Sél. PV", filetypes=[("CSV/Excel", "*.csv *.xlsx *.xls")])
            if not filepath: return

        self._log('info', f"Chargement PV : {os.path.basename(filepath)}")
        try:
            self.pv_sep = detect_separator(filepath) if filepath.lower().endswith('.csv') else ','
            self.pv_df = load_file(filepath)
            self.pv_filepath = filepath
            columns = list(self.pv_df.columns)

            self.pv_file_label.configure(text=f"✅ {os.path.basename(filepath)} ({len(self.pv_df)} l.)", foreground=SUCCESS)
            self.pv_dropzone.label.configure(text=f"Fichier chargé: {os.path.basename(filepath)}")
            self.pv_matricule_combo['values'] = columns

            for i, col in enumerate(columns):
                if any(k in col.lower() for k in ('matricule', 'matric', 'num', 'immat', 'etud')):
                    self.pv_matricule_combo.current(i)
                    break
            else:
                if columns: self.pv_matricule_combo.current(0)

            self.pv_matricule_frame.pack(fill='x', pady=(10, 0))
            self.examen_section.pack_forget()
            self.history_section.pack_forget()

        except Exception as e:
            self._log('err', f"Err: {e}")
            messagebox.showerror("Error", f"Impossible:{e}")

    def _validate_pv(self):
        col = self.pv_matricule_combo.get()
        if not col: return
        self.pv_matricule_col = col
        self.pv_info_label.configure(text=f"✅ PV validé")
        self._build_examen_section()
        self._build_history_section()

    def _load_examen(self, filepath=None):
        if not filepath:
            filepath = filedialog.askopenfilename(title="Sél. Examen", filetypes=[("CSV/Excel", "*.csv *.xlsx *.xls")])
            if not filepath: return
        self._log('info', f"Ch. Examen : {os.path.basename(filepath)}")
        try:
            self.examen_sep = detect_separator(filepath) if filepath.lower().endswith('.csv') else ','
            self.examen_df = load_file(filepath)
            self.examen_filepath = filepath
            columns = list(self.examen_df.columns)

            self.examen_file_label.configure(text=f"✅ {os.path.basename(filepath)} ({len(self.examen_df)} l.)", foreground=SUCCESS)
            self.examen_dropzone.label.configure(text=f"Fichier chargé: {os.path.basename(filepath)}")

            self.pv_note_combo['values'] = list(self.pv_df.columns)
            self.examen_matricule_combo['values'] = columns
            self.examen_note_combo['values'] = columns

            if self.last_pv_note_col in self.pv_df.columns:
                self.pv_note_combo.set(self.last_pv_note_col)
            if self.last_examen_matricule in columns:
                self.examen_matricule_combo.set(self.last_examen_matricule)
            if self.last_examen_note_col in columns:
                self.examen_note_combo.set(self.last_examen_note_col)

            self.examen_cols_frame.pack(fill='x', pady=(10, 0))
        except Exception as e:
            messagebox.showerror("Erreur", f"{e}")

    def _execute_transfer(self):
        pv_note_col = self.pv_note_combo.get()
        ex_mat_col  = self.examen_matricule_combo.get()
        ex_not_col  = self.examen_note_combo.get()

        if not pv_note_col or not ex_mat_col or not ex_not_col:
            messagebox.showwarning("Attention", "Toutes les colonnes n'ont pas été sélectionnées.")
            return

        try:
            # PRÉPARATION et ANALYSE AVANT MODIFICATION (DRY RUN)
            pv_notes = {}
            for _, row in self.pv_df.iterrows():
                mat = str(row[self.pv_matricule_col]).strip()
                if mat and str(mat).lower() not in ('nan', 'none'):
                    pv_notes[mat.lower()] = row.get(pv_note_col, '')

            matched = 0
            not_found = 0
            overwritten = 0
            aberrants = 0
            
            # Rapport d'audit interne (en mémoire)
            audit_lines = [
                f"=== RAPPORT D'AUDIT DE TRANSFERT ===",
                f"Date : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"Fichier PV : {self.pv_filepath} (col note: {pv_note_col})",
                f"Fichier Examen : {self.examen_filepath} (col. Dest: {ex_not_col})",
                "-------------------------------------"
            ]
            
            preview_df = self.examen_df.copy()

            for idx in preview_df.index:
                raw_mat = str(preview_df.at[idx, ex_mat_col]).strip()
                key = raw_mat.lower()
                old_note = str(preview_df.at[idx, ex_not_col]).strip()

                if key in pv_notes:
                    note_str, is_aberr = normalize_note(pv_notes[key])
                    preview_df.at[idx, ex_not_col] = note_str
                    matched += 1
                    
                    if old_note not in ('', '0', 'nan', 'NaN') and old_note != note_str:
                        overwritten += 1
                        audit_lines.append(f"[ÉCRASEMENT] {raw_mat} : {old_note} -> {note_str}")
                    else:
                        audit_lines.append(f"[TRANSFÉRÉ] {raw_mat} : -> {note_str}")
                        
                    if is_aberr:
                        aberrants += 1
                        audit_lines.append(f"[! ABERRANT !] {raw_mat} valeur étrange : {note_str}")
                else:
                    preview_df.at[idx, ex_not_col] = '0'
                    not_found += 1
                    audit_lines.append(f"[NON TROUVÉ] {raw_mat} : Forcé à 0")

            preview_df[ex_not_col] = preview_df[ex_not_col].apply(
                lambda x: '0' if str(x).strip() in ('', 'nan', 'NaN') else str(x)
            )

            # ÉCRAN DE PRÉVISUALISATION
            msg = (
                f"⚠️ OPÉRATION CRITIQUE : Prévisualisation\n\n"
                f"Total : {len(preview_df)} notes\n"
                f"▶ Notes trouvées : {matched}\n"
                f"▶ Non trouvées (forcé 0) : {not_found}\n\n"
                f"!!! Avertissements !!!\n"
                f"• {overwritten} notes vont être ÉCRASÉES.\n"
                f"• {aberrants} valeurs semblent aberrantes (ex: texte, >20).\n\n"
                f"Un backup automatique va être généré avant la sauvegarde.\n"
                f"Souhaitez-vous continuer l'opération in-place ?"
            )
            
            if not messagebox.askyesno("Confirmation de sécurité", msg, icon='warning'):
                self._log('warn', "Transfert annulé par l'utilisateur après prévisualisation.")
                return

            # BACKUP AUTOMATIQUE
            backup_tag = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            base_name, ext = os.path.splitext(self.examen_filepath)
            backup_path = f"{base_name}_backup_{backup_tag}{ext}"
            shutil.copyfile(self.examen_filepath, backup_path)
            self._log('ok', f"Backup sécurité généré : {os.path.basename(backup_path)}")

            # SAUVEGARDE IN-PLACE
            save_file(preview_df, self.examen_filepath, sep=self.examen_sep)
            
            # SAUVEGARDE DU RAPPORT D'AUDIT
            audit_path = f"{base_name}_audit_{backup_tag}.txt"
            with open(audit_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(audit_lines))
            self._log('info', f"Rapport d'audit généré : {os.path.basename(audit_path)}")

            self.last_pv_note_col = pv_note_col
            self.last_examen_matricule = ex_mat_col
            self.last_examen_note_col = ex_not_col

            self.history.append({
                'examen_file': os.path.basename(self.examen_filepath),
                'pv_col'     : pv_note_col,
                'examen_col' : ex_not_col,
                'matched'    : matched,
                'total'      : len(preview_df)
            })

            messagebox.showinfo("Succès Sécurisé", 
                                f"L'opération s'est terminée avec succès !\n\n"
                                f"• {matched} notes écrites, {not_found} matricules ignorés (0).\n"
                                f"• Un backup & le rapport d'audit sont dans le même dossier.")
            
            # Recharger
            self._load_examen(self.examen_filepath)
            self._build_history_section()

        except Exception as e:
            self._log('err', f"Erreur critique: {e}")
            messagebox.showerror("Erreur Erreur Critique", f"{e}")


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
