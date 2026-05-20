const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const fs = require('fs');
const XLSX = require('xlsx');

function createWindow() {
  const win = new BrowserWindow({
    width: 960,
    height: 880,
    minWidth: 720,
    minHeight: 620,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
    backgroundColor: '#1a1a2e',
    title: 'T.Notes — Transfert Sécurisé',
    autoHideMenuBar: true,
  });
  win.loadFile(path.join(__dirname, 'src', 'index.html'));
}

app.whenReady().then(createWindow);
app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit(); });
app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });

// ─── Utilitaires fichiers ──────────────────────────────────────────────────────

function detectSeparator(filepath) {
  try {
    const buf = fs.readFileSync(filepath);
    const content = buf.toString('utf-8');
    const lines = content.split('\n').filter(l => l.trim()).slice(0, 10);
    const sc = lines.reduce((a, l) => a + (l.match(/;/g) || []).length, 0);
    const co = lines.reduce((a, l) => a + (l.match(/,/g) || []).length, 0);
    return sc >= co ? ';' : ',';
  } catch { return ','; }
}

function loadFile(filepath) {
  const ext = path.extname(filepath).toLowerCase();
  let wb, sep = ',';

  if (ext === '.csv') {
    sep = detectSeparator(filepath);
    const content = fs.readFileSync(filepath, 'utf-8');
    wb = XLSX.read(content, { type: 'string', FS: sep });
  } else {
    wb = XLSX.readFile(filepath, { cellText: true, raw: false });
  }

  const ws = wb.Sheets[wb.SheetNames[0]];
  const raw = XLSX.utils.sheet_to_json(ws, { defval: '', raw: false });

  if (!raw.length) return { columns: [], rows: [], sep };

  // Nettoyage colonnes : trim + suppression BOM
  const rows = raw.map(row => {
    const clean = {};
    for (const [k, v] of Object.entries(row)) {
      clean[k.trim().replace(/^﻿/, '')] = String(v ?? '');
    }
    return clean;
  });

  const columns = Object.keys(rows[0]);
  return { columns, rows, sep };
}

function normalizeNote(value) {
  if (value === null || value === undefined) return ['0', false];
  const s = String(value).trim();
  if (['', 'nan', 'NaN', 'None'].includes(s)) return ['0', false];
  const num = parseFloat(s.replace(',', '.'));
  if (isNaN(num)) return [s, true];
  const isAberrant = num < 0.0 || num > 20.0;
  const formatted = (num === Math.floor(num))
    ? String(Math.floor(num))
    : String(Math.round(num * 10000) / 10000);
  return [formatted, isAberrant];
}

function saveFile(rows, columns, filepath, sep) {
  const ext = path.extname(filepath).toLowerCase();

  // Reconstruction ordonnée
  const ordered = rows.map(row => {
    const r = {};
    for (const col of columns) r[col] = row[col] ?? '';
    return r;
  });

  const ws = XLSX.utils.json_to_sheet(ordered, { header: columns });
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, 'Sheet1');

  if (ext === '.csv') {
    const csv = XLSX.utils.sheet_to_csv(ws, { FS: sep });
    fs.writeFileSync(filepath, '﻿' + csv, 'utf-8'); // BOM pour compatibilité Excel
  } else {
    XLSX.writeFile(wb, filepath);
  }
}

// ─── IPC Handlers ─────────────────────────────────────────────────────────────

ipcMain.handle('file:open', async () => {
  const result = await dialog.showOpenDialog({
    title: 'Sélectionner le fichier PV',
    filters: [{ name: 'CSV / Excel', extensions: ['csv', 'xlsx', 'xls'] }],
    properties: ['openFile'],
  });
  return result.canceled ? null : result.filePaths[0];
});

ipcMain.handle('file:openMultiple', async () => {
  const result = await dialog.showOpenDialog({
    title: 'Sélectionner les fichiers Examen',
    filters: [{ name: 'CSV / Excel', extensions: ['csv', 'xlsx', 'xls'] }],
    properties: ['openFile', 'multiSelections'],
  });
  return result.canceled ? [] : result.filePaths;
});

ipcMain.handle('file:load', async (_, filepath) => {
  return loadFile(filepath);
});

ipcMain.handle('file:basename', (_, fp) => path.basename(fp));

ipcMain.handle('transfer:dryRun', async (_, { pvData, pvMatriculeCol, pvNoteCol, examens }) => {
  // Index PV matricule → note
  const pvNotes = {};
  for (const row of pvData.rows) {
    const mat = String(row[pvMatriculeCol] || '').trim();
    if (mat && !['nan', 'none', ''].includes(mat.toLowerCase())) {
      pvNotes[mat.toLowerCase()] = row[pvNoteCol] ?? '';
    }
  }

  const results = [];

  for (const ex of examens) {
    const { filepath, data, matCol, noteCol } = ex;
    let matched = 0, notFound = 0, overwritten = 0, aberrants = 0;

    const auditLines = [
      "=== RAPPORT D'AUDIT DE TRANSFERT ===",
      `Date        : ${new Date().toLocaleString('fr-FR')}`,
      `Fichier PV  : (col. note: ${pvNoteCol})`,
      `Fichier Exam: ${filepath} (col. dest: ${noteCol})`,
      '─────────────────────────────────────',
    ];

    const previewRows = data.rows.map(row => {
      const newRow = { ...row };
      const rawMat = String(row[matCol] || '').trim();
      const key = rawMat.toLowerCase();
      const oldNote = String(row[noteCol] || '').trim();

      if (key in pvNotes) {
        const [noteStr, isAberr] = normalizeNote(pvNotes[key]);
        newRow[noteCol] = noteStr;
        matched++;
        if (oldNote && !['', '0', 'nan', 'NaN'].includes(oldNote) && oldNote !== noteStr) {
          overwritten++;
          auditLines.push(`[ÉCRASEMENT]  ${rawMat} : ${oldNote} → ${noteStr}`);
        } else {
          auditLines.push(`[TRANSFÉRÉ]   ${rawMat} : → ${noteStr}`);
        }
        if (isAberr) {
          aberrants++;
          auditLines.push(`[! ABERRANT!] ${rawMat} : ${noteStr}`);
        }
      } else {
        newRow[noteCol] = '0';
        notFound++;
        auditLines.push(`[NON TROUVÉ]  ${rawMat} → forcé à 0`);
      }

      if (['', 'nan', 'NaN'].includes(String(newRow[noteCol]).trim())) {
        newRow[noteCol] = '0';
      }

      return newRow;
    });

    results.push({
      filepath,
      fname: path.basename(filepath),
      data: { ...data, rows: previewRows },
      matCol,
      noteCol,
      matched,
      notFound,
      overwritten,
      aberrants,
      auditLines,
    });
  }

  return results;
});

ipcMain.handle('transfer:commit', async (_, results) => {
  const tag = new Date().toISOString().replace(/[-:T.Z]/g, '').slice(0, 15);
  const log = [];

  for (const res of results) {
    const { filepath, data, auditLines } = res;
    const ext = path.extname(filepath).toLowerCase();
    const dir = path.dirname(filepath);
    const filename = path.basename(filepath, ext);
    const logDir = path.join(dir, 'log');

    if (!fs.existsSync(logDir)) fs.mkdirSync(logDir);

    const backupPath = path.join(logDir, `${filename}_backup_${tag}${ext}`);
    fs.copyFileSync(filepath, backupPath);
    log.push({ level: 'ok', msg: `[${res.fname}] Backup → ${path.basename(backupPath)}` });

    saveFile(data.rows, data.columns, filepath, data.sep);
    log.push({ level: 'ok', msg: `[${res.fname}] Sauvegardé — ${res.matched} notes, ${res.notFound} → 0` });

    if (res.overwritten) log.push({ level: 'warn', msg: `[${res.fname}] ${res.overwritten} note(s) écrasée(s)` });
    if (res.aberrants)   log.push({ level: 'warn', msg: `[${res.fname}] ${res.aberrants} valeur(s) aberrante(s)` });

    const auditPath = path.join(logDir, `${filename}_audit_${tag}.txt`);
    fs.writeFileSync(auditPath, auditLines.join('\n'), 'utf-8');
    log.push({ level: 'info', msg: `[${res.fname}] Audit → ${path.basename(auditPath)}` });

    // Log détaillé
    for (const line of auditLines) {
      if (line.startsWith('[TRANSFÉRÉ]'))   log.push({ level: 'data', msg: line });
      else if (line.startsWith('[ÉCRASEMENT]')) log.push({ level: 'warn', msg: line });
      else if (line.startsWith('[NON TROUVÉ]')) log.push({ level: 'warn', msg: line });
      else if (line.startsWith('[! ABERRANT')) log.push({ level: 'err',  msg: line });
    }
  }

  return log;
});
