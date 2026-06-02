'use strict';

// ─── État global ──────────────────────────────────────────────────────────────
const state = {
  pv: { filepath: null, data: null, matriculeCol: null },
  examens: [],    // [{ filepath, fname, data, matCol, noteCol, rowEl }]
  history: [],
  pendingResults: null,
  pvMatSelect: null,
  pvNoteSelect: null,
};

// ─── Helpers log ──────────────────────────────────────────────────────────────
const ICONS = { info: 'i', ok: '+', warn: '!', err: 'x', data: '>' };

function log(level, msg) {
  const el = document.getElementById('console-log');
  const ts = new Date().toLocaleTimeString('fr-FR', { hour12: false });
  const line = document.createElement('div');
  line.className = 'log-line';
  line.innerHTML =
    `<span class="log-ts">[${ts}]</span>` +
    `<span class="log-${level}">${ICONS[level] || '·'} ${escHtml(msg)}</span>`;
  el.appendChild(line);
  el.scrollTop = el.scrollHeight;
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

// ─── Helpers UI ───────────────────────────────────────────────────────────────
function show(id)  { document.getElementById(id)?.classList.remove('hidden'); }
function hide(id)  { document.getElementById(id)?.classList.add('hidden'); }
function get(id)   { return document.getElementById(id); }

// ─── Drag & Drop helpers ──────────────────────────────────────────────────────
function setupDrop(el, onFiles) {
  el.addEventListener('dragover', e => {
    e.preventDefault();
    el.classList.add('drag-over');
  });
  el.addEventListener('dragleave', () => el.classList.remove('drag-over'));
  el.addEventListener('drop', e => {
    e.preventDefault();
    el.classList.remove('drag-over');
    const files = Array.from(e.dataTransfer.files);
    const paths = files.map(f => window.api.getPathForFile(f)).filter(Boolean);
    if (paths.length) onFiles(paths);
  });
}

// ─── Modal ────────────────────────────────────────────────────────────────────
function showModal(bodyText) {
  return new Promise(resolve => {
    get('modal-body').textContent = bodyText;
    show('modal-overlay');

    const onConfirm = () => { hide('modal-overlay'); cleanup(); resolve(true); };
    const onCancel  = () => { hide('modal-overlay'); cleanup(); resolve(false); };

    get('modal-confirm').addEventListener('click', onConfirm, { once: true });
    get('modal-cancel').addEventListener('click', onCancel, { once: true });

    function cleanup() {
      get('modal-confirm').removeEventListener('click', onConfirm);
      get('modal-cancel').removeEventListener('click', onCancel);
    }
  });
}

// ─── Section PV ───────────────────────────────────────────────────────────────
async function loadPV(filepath) {
  log('info', `Chargement PV : ${await window.api.basename(filepath)}`);
  try {
    const data = await window.api.loadFile(filepath);
    state.pv.filepath = filepath;
    state.pv.data = data;

    const fname = await window.api.basename(filepath);
    get('pv-meta').textContent = `${fname}  (${data.rows.length} lignes, ${data.columns.length} colonnes)`;
    get('pv-meta').style.color = 'var(--success)';

    const drop = get('pv-drop');
    drop.classList.add('loaded');
    drop.textContent = `Chargé : ${fname}`;

    fillSelect(state.pvMatSelect, data.columns,
      ['matricule', 'matric', 'num', 'immat', 'etud']);
    show('pv-col-section');

    // Reset examens si PV change
    hide('card-examens');
    hide('card-history');
    state.examens = [];
    get('examen-files-list').innerHTML = '';
    state.pv.matriculeCol = null;

    log('ok', `PV chargé — ${data.rows.length} lignes | Colonnes : ${data.columns.join(', ')}`);
  } catch (err) {
    log('err', `Erreur PV : ${err.message || err}`);
  }
}

function validatePV() {
  const col = state.pvMatSelect.value;
  if (!col) return;
  state.pv.matriculeCol = col;

  const unique = new Set(state.pv.data.rows.map(r => String(r[col] || '').trim().toLowerCase())).size;
  const infoEl = get('pv-info');
  infoEl.textContent = `PV validé — ${unique} matricules uniques dans « ${col} »`;
  infoEl.classList.remove('hidden');

  log('ok', `PV validé | Col. matricule : « ${col} » | ${unique} entrées uniques`);

  // Pré-remplir note select avec les colonnes du PV
  fillSelect(state.pvNoteSelect, state.pv.data.columns,
    ['note', 'score', 'résultat', 'resultat', 'moy']);
  show('card-examens');
}

// Mémorisation des colonnes
const columnMemory = {
  get: (filename) => JSON.parse(localStorage.getItem(`cols_${filename}`)),
  set: (filename, mat, note) => localStorage.setItem(`cols_${filename}`, JSON.stringify({ mat, note }))
};

function fillSelect(selectEl, columns, prefer, saved = null) {
  selectEl.setOptions(columns);
  if (saved) {
    selectEl.value = saved;
  } else if (prefer) {
    const lower = prefer.map(k => k.toLowerCase());
    for (const col of columns) {
      if (lower.some(k => col.toLowerCase().includes(k))) {
        selectEl.value = col;
        return;
      }
    }
  }
}

// ─── Section Examens ──────────────────────────────────────────────────────────
async function addExamenFiles(filepaths) {
  for (const fp of filepaths) {
    await addSingleExamen(fp);
  }
}

async function addSingleExamen(filepath) {
  const fname = await window.api.basename(filepath);
  log('info', `Chargement examen : ${fname}`);
  try {
    const data = await window.api.loadFile(filepath);

    if (state.examens.find(e => e.filepath === filepath)) {
      log('warn', `Déjà chargé : ${fname}`);
      return;
    }

    const saved = columnMemory.get(fname);
    const entry = { filepath, fname, data, rowEl: null };

    const row = document.createElement('div');
    row.className = 'examen-file-row';

    const header = document.createElement('div');
    header.className = 'examen-file-header';

    const nameSpan = document.createElement('div');
    nameSpan.innerHTML =
      `<span class="examen-file-name">${escHtml(fname)}</span>` +
      `<span class="examen-file-meta">${data.rows.length} lignes · ${data.columns.length} col.</span>`;

    const removeBtn = document.createElement('button');
    removeBtn.className = 'btn btn-danger';
    removeBtn.textContent = '✕';
    removeBtn.addEventListener('click', () => {
      matSelect.destroy();
      noteSelect.destroy();
      row.remove();
      state.examens = state.examens.filter(e => e !== entry);
      refreshTransferBtn();
    });

    header.appendChild(nameSpan);
    header.appendChild(removeBtn);
    row.appendChild(header);

    const formRow = document.createElement('div');
    formRow.className = 'form-row';

    const matGroup = document.createElement('div');
    matGroup.className = 'form-group';
    const matLabel = document.createElement('label');
    matLabel.textContent = 'Colonne Matricule';
    matGroup.appendChild(matLabel);
    const matSelect = new CustomSelect(matGroup);
    fillSelect(matSelect, data.columns, ['matricule', 'matric', 'num', 'immat', 'etud'], saved?.mat);

    const noteGroup = document.createElement('div');
    noteGroup.className = 'form-group';
    const noteLabel = document.createElement('label');
    noteLabel.textContent = 'Colonne Note (destination)';
    noteGroup.appendChild(noteLabel);
    const noteSelect = new CustomSelect(noteGroup);
    fillSelect(noteSelect, data.columns, ['note', 'score', 'résultat', 'resultat', 'moy'], saved?.note);

    formRow.appendChild(matGroup);
    formRow.appendChild(noteGroup);
    row.appendChild(formRow);

    get('examen-files-list').appendChild(row);

    entry.rowEl = row;
    entry.getMatCol  = () => matSelect.value;
    entry.getNoteCol = () => noteSelect.value;

    state.examens.push(entry);
    refreshTransferBtn();

  } catch (err) {
    log('err', `Erreur chargement ${fname} : ${err.message || err}`);
  }
}

function refreshTransferBtn() {
  const area = get('transfer-area');
  if (state.examens.length > 0) {
    show('transfer-area');
    const n = state.examens.length;
    get('transfer-btn').textContent =
      `Transférer vers ${n} fichier${n > 1 ? 's' : ''}`;
  } else {
    hide('transfer-area');
  }
}

// ─── Transfert ────────────────────────────────────────────────────────────────
async function executeTransfer() {
  const pvNoteCol = state.pvNoteSelect.value;
  if (!pvNoteCol) { log('err', 'Sélectionnez la colonne NOTE du PV.'); return; }
  if (!state.examens.length) { log('err', 'Ajoutez au moins un fichier examen.'); return; }

  for (const ex of state.examens) {
    if (!ex.getMatCol() || !ex.getNoteCol()) {
      log('err', `Colonnes manquantes pour : ${ex.fname}`);
      return;
    }
  }

  // Enregistrer les choix
  for (const ex of state.examens) {
    columnMemory.set(ex.fname, ex.getMatCol(), ex.getNoteCol());
  }

  log('info', `━━━ DÉBUT TRANSFERT — ${state.examens.length} fichier(s) | Col. PV : « ${pvNoteCol} » ━━━`);

  const payload = {
    pvData: state.pv.data,
    pvMatriculeCol: state.pv.matriculeCol,
    pvNoteCol,
    examens: state.examens.map(ex => ({
      filepath: ex.filepath,
      data: ex.data,
      matCol: ex.getMatCol(),
      noteCol: ex.getNoteCol(),
    })),
  };

  let results;
  try {
    results = await window.api.dryRun(payload);
  } catch (err) {
    log('err', `Erreur analyse : ${err.message || err}`);
    return;
  }

  const totalMatched    = results.reduce((a, r) => a + r.matched, 0);
  const totalNotFound   = results.reduce((a, r) => a + r.notFound, 0);
  const totalOverwrite  = results.reduce((a, r) => a + r.overwritten, 0);
  const totalAberrants  = results.reduce((a, r) => a + r.aberrants, 0);

  const filesSummary = results.map(r =>
    `  • ${r.fname} : ${r.matched} trouvés, ${r.notFound} manquants`
  ).join('\n');

  const confirmText =
    `PRÉVISUALISATION — ${results.length} fichier(s)\n\n` +
    `${filesSummary}\n\n` +
    `Totaux :\n` +
    `▶ Notes trouvées         : ${totalMatched}\n` +
    `▶ Non trouvées (→ 0)     : ${totalNotFound}\n` +
    `▶ Notes écrasées         : ${totalOverwrite}\n` +
    `▶ Valeurs aberrantes     : ${totalAberrants}\n\n` +
    `Un backup automatique sera créé avant chaque sauvegarde.\n` +
    `Souhaitez-vous continuer ?`;

  const confirmed = await showModal(confirmText);
  if (!confirmed) {
    log('warn', 'Transfert annulé par l\'utilisateur.');
    return;
  }

  // Commit
  let commitLog;
  try {
    commitLog = await window.api.commit(results);
  } catch (err) {
    log('err', `Erreur écriture : ${err.message || err}`);
    return;
  }

  for (const entry of commitLog) {
    log(entry.level, entry.msg);
  }

  log('ok', `━━━ TRANSFERT TERMINÉ — ${results.length} fichier(s) | ${totalMatched} notes écrites ━━━`);

  get('transfer-result').textContent =
    `${totalMatched} notes → ${results.length} fichier${results.length > 1 ? 's' : ''}`;

  // Historique
  for (const r of results) {
    state.history.push({
      fname: r.fname,
      matched: r.matched,
      total: r.data.rows.length,
    });
  }
  buildHistory();

  // Mettre à jour les data des examens (post-transfert)
  for (const r of results) {
    const ex = state.examens.find(e => e.filepath === r.filepath);
    if (ex) ex.data = r.data;
  }
}

// ─── Historique ───────────────────────────────────────────────────────────────
function buildHistory() {
  if (!state.history.length) return;
  show('card-history');
  const list = get('history-list');
  list.innerHTML = '';
  [...state.history].reverse().forEach((h, i) => {
    const el = document.createElement('div');
    el.className = 'history-item';
    el.textContent = `${i + 1}. ${h.fname} → ${h.matched}/${h.total} notes`;
    list.appendChild(el);
  });
}

// ─── Init ─────────────────────────────────────────────────────────────────────
function init() {
  state.pvMatSelect = new CustomSelect(get('pv-matricule-select'));
  state.pvNoteSelect = new CustomSelect(get('pv-note-select'));

  log('info', 'Application démarrée en mode sécurisé.');
  log('info', 'Séparateur décimal : « . » | Détection CSV : automatique');

  // PV drop
  const pvDrop = get('pv-drop');
  pvDrop.addEventListener('click', async () => {
    const fp = await window.api.openFile();
    if (fp) loadPV(fp);
  });
  setupDrop(pvDrop, paths => loadPV(paths[0]));

  // PV validate
  get('pv-validate-btn').addEventListener('click', validatePV);

  // Examens drop
  const exDrop = get('examens-drop');
  exDrop.addEventListener('click', async () => {
    const fps = await window.api.openMultiple();
    if (fps.length) addExamenFiles(fps);
  });
  setupDrop(exDrop, addExamenFiles);

  // Transfer
  get('transfer-btn').addEventListener('click', executeTransfer);

  // Console clear
  get('console-clear').addEventListener('click', () => {
    get('console-log').innerHTML = '';
  });

  // Console resize
  const resizeHandle = get('console-resize');
  const consoleLog = get('console-log');
  let resizing = false;
  let startY = 0;
  let startHeight = 0;

  resizeHandle.addEventListener('mousedown', e => {
    resizing = true;
    startY = e.clientY;
    startHeight = consoleLog.offsetHeight;
    resizeHandle.classList.add('dragging');
    document.body.style.cursor = 'row-resize';
    document.body.style.userSelect = 'none';
  });

  document.addEventListener('mousemove', e => {
    if (!resizing) return;
    const delta = startY - e.clientY;
    const newHeight = Math.max(60, Math.min(startHeight + delta, window.innerHeight * 0.6));
    consoleLog.style.setProperty('--console-height', newHeight + 'px');
    consoleLog.style.height = newHeight + 'px';
  });

  document.addEventListener('mouseup', () => {
    if (!resizing) return;
    resizing = false;
    resizeHandle.classList.remove('dragging');
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
  });
}

document.addEventListener('DOMContentLoaded', init);
