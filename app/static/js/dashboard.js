/**
 * AI Product Guardian — Interactive Client Dashboard Logic
 */

document.addEventListener('DOMContentLoaded', () => {
  initTabs();
  loadSampleAssets();
  initDocumentStudio();
  initConflictRadar();
  initApplianceVision();
  initPassportVault();
});

// State Store
const state = {
  currentDppFile: null,
  currentDppSamplePath: null,
  currentYoloFile: null,
  currentYoloSamplePath: null,
  activePassportData: null,
  samples: {}
};

/* ============================================================
   1. NAVIGATION & TAB SWITCHING
   ============================================================ */
function initTabs() {
  const tabs = document.querySelectorAll('.nav-tab');
  const contents = document.querySelectorAll('.tab-content');

  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const targetId = tab.dataset.tab;
      tabs.forEach(t => t.classList.remove('active'));
      contents.forEach(c => c.classList.remove('active'));

      tab.classList.add('active');
      const targetContent = document.getElementById(targetId);
      if (targetContent) targetContent.classList.add('active');

      if (targetId === 'tab-passport-vault') {
        fetchVaultPassports();
      }
    });
  });
}

/* ============================================================
   2. SAMPLE ASSETS LOADER (1-Click Demos)
   ============================================================ */
async function loadSampleAssets() {
  try {
    const res = await fetch('/api/samples');
    const data = await res.json();
    state.samples = data.samples || {};

    renderSampleChips('dpp-sample-chips', [
      ...(state.samples.warranty_cards || []),
      ...(state.samples.invoices_receipts || [])
    ], selectDppSample);

    renderSampleChips('yolo-sample-chips', state.samples.appliance_photos || [], selectYoloSample);
  } catch (err) {
    console.error('Failed to load sample test assets:', err);
  }
}

function renderSampleChips(containerId, items, clickHandler) {
  const container = document.getElementById(containerId);
  if (!container) return;
  container.innerHTML = '';

  if (!items.length) {
    container.innerHTML = '<span class="text-muted" style="font-size:0.8rem;">No samples found.</span>';
    return;
  }

  items.forEach(item => {
    const chip = document.createElement('button');
    chip.className = 'sample-chip';
    chip.innerHTML = `<span>📄</span> ${item.title}`;
    chip.addEventListener('click', () => {
      container.querySelectorAll('.sample-chip').forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      clickHandler(item);
    });
    container.appendChild(chip);
  });
}

/* ============================================================
   3. DOCUMENT STUDIO (OCR & DPP Extraction)
   ============================================================ */
function initDocumentStudio() {
  const dropzone = document.getElementById('dpp-dropzone');
  const fileInput = document.getElementById('dpp-file-input');
  const btnExtract = document.getElementById('btn-run-extraction');
  const btnClear = document.getElementById('btn-clear-dpp');
  const btnRemovePreview = document.getElementById('btn-dpp-remove-preview');
  const btnExport = document.getElementById('btn-export-dpp-json');
  const btnJumpMatcher = document.getElementById('btn-jump-to-matcher');

  dropzone.addEventListener('click', (e) => {
    if (e.target !== btnRemovePreview) fileInput.click();
  });

  dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.classList.add('dragover');
  });

  dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));

  dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('dragover');
    if (e.dataTransfer.files.length) {
      handleDppFileUpload(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener('change', (e) => {
    if (e.target.files.length) {
      handleDppFileUpload(e.target.files[0]);
    }
  });

  btnRemovePreview.addEventListener('click', (e) => {
    e.stopPropagation();
    clearDppInput();
  });

  btnClear.addEventListener('click', clearDppInput);

  btnExtract.addEventListener('click', executeDppExtraction);

  btnExport.addEventListener('click', () => {
    if (!state.activePassportData) return;
    const blob = new Blob([JSON.stringify(state.activePassportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${state.activePassportData.passport_id || 'passport'}.json`;
    a.click();
    URL.revokeObjectURL(url);
    showToast('Passport JSON exported successfully!');
  });

  btnJumpMatcher.addEventListener('click', () => {
    if (!state.activePassportData) return;
    populateMatcherDocA(state.activePassportData);
    document.querySelector('[data-tab="tab-conflict-radar"]').click();
    showToast('Loaded active passport into Document A of Conflict Radar!');
  });
}

function handleDppFileUpload(file) {
  state.currentDppFile = file;
  state.currentDppSamplePath = null;
  const reader = new FileReader();
  reader.onload = (e) => {
    showDppPreview(e.target.result);
  };
  reader.readAsDataURL(file);
}

function selectDppSample(item) {
  state.currentDppFile = null;
  state.currentDppSamplePath = item.path;
  if (item.thumbnail_base64) {
    showDppPreview(`data:image/jpeg;base64,${item.thumbnail_base64}`);
  } else {
    showDppPreview('/static/images/icon.png');
  }
}

function showDppPreview(src) {
  const previewWrapper = document.getElementById('dpp-preview-wrapper');
  const previewImg = document.getElementById('dpp-image-preview');
  const dropzoneContent = document.querySelector('#dpp-dropzone .dropzone-content');
  const btnExtract = document.getElementById('btn-run-extraction');

  previewImg.src = src;
  previewWrapper.classList.remove('hidden');
  dropzoneContent.classList.add('hidden');
  btnExtract.disabled = false;
}

function clearDppInput() {
  state.currentDppFile = null;
  state.currentDppSamplePath = null;
  document.getElementById('dpp-file-input').value = '';
  document.getElementById('dpp-preview-wrapper').classList.add('hidden');
  document.querySelector('#dpp-dropzone .dropzone-content').classList.remove('hidden');
  document.getElementById('btn-run-extraction').disabled = true;
  document.querySelectorAll('#dpp-sample-chips .sample-chip').forEach(c => c.classList.remove('active'));
}

async function executeDppExtraction() {
  const loading = document.getElementById('dpp-loading-state');
  const outputContainer = document.getElementById('dpp-output-container');
  const emptyState = document.getElementById('dpp-empty-state');
  const resultWrapper = document.getElementById('passport-result-wrapper');
  const statusBadge = document.getElementById('extraction-status-badge');

  loading.classList.remove('hidden');
  emptyState.classList.add('hidden');
  resultWrapper.classList.add('hidden');
  statusBadge.textContent = 'Processing...';

  try {
    const formData = new FormData();
    if (state.currentDppFile) {
      formData.append('file', state.currentDppFile);
    } else if (state.currentDppSamplePath) {
      formData.append('sample_path', state.currentDppSamplePath);
    }

    const res = await fetch('/api/dpp/extract', {
      method: 'POST',
      body: formData
    });

    if (!res.ok) throw new Error(`Server returned status ${res.status}`);
    const data = await res.json();

    if (data.results && data.results.length > 0) {
      const first = data.results[0];
      state.activePassportData = first.passport;
      renderCertificate(first.passport, first.identity_match);
      statusBadge.textContent = `${data.passport_count} Passport(s) Extracted`;
      showToast(`Successfully extracted ${data.passport_count} Digital Passport(s)!`);
      refreshGlobalStats();
    } else {
      throw new Error('No product passports detected in document');
    }
  } catch (err) {
    showToast(`Extraction error: ${err.message}`);
    emptyState.classList.remove('hidden');
    statusBadge.textContent = 'Extraction Failed';
  } finally {
    loading.classList.add('hidden');
  }
}

function renderCertificate(p, matchInfo = {}) {
  const resultWrapper = document.getElementById('passport-result-wrapper');
  resultWrapper.classList.remove('hidden');

  document.getElementById('cert-product').textContent = p.product || 'Consumer Product';
  document.getElementById('cert-brand').textContent = p.brand ? `${p.brand} Registered DPP` : 'Generic Brand';
  document.getElementById('cert-id').textContent = p.passport_id || 'PP-PENDING';
  document.getElementById('cert-model').textContent = p.model || 'N/A';
  document.getElementById('cert-serial').textContent = p.serial_number || 'N/A';
  document.getElementById('cert-date').textContent = p.purchase_date || 'N/A';
  document.getElementById('cert-warranty').textContent = p.warranty || 'Standard Manufacturer Warranty';
  document.getElementById('cert-price').textContent = p.purchase_price ? `${p.currency || 'INR'} ${Number(p.purchase_price).toLocaleString('en-US', { minimumFractionDigits: 2 })}` : 'N/A';
  document.getElementById('cert-seller').textContent = p.seller || 'Authorized Retailer';
  document.getElementById('cert-customer').textContent = p.customer_name || 'Registered Owner';
  document.getElementById('cert-doc-type').textContent = (p.document_type || 'Warranty Registration Card').replace('_', ' ').toUpperCase();

  // Checkbox Reasoning Quote
  const evidenceBox = document.getElementById('cert-evidence-box');
  const evidenceText = document.getElementById('cert-evidence-text');
  if (p.selection_evidence) {
    evidenceText.textContent = p.selection_evidence;
    evidenceBox.classList.remove('hidden');
  } else {
    evidenceBox.classList.add('hidden');
  }

  // Verification Banner
  const banner = document.getElementById('cert-match-banner');
  const bannerIcon = document.getElementById('banner-icon');
  const bannerTitle = document.getElementById('banner-title');
  const bannerDesc = document.getElementById('banner-desc');

  const status = (matchInfo && matchInfo.status) || (p.identity_match && p.identity_match.status) || 'new_product';

  banner.className = `cert-verification-banner ${status}`;
  if (status === 'verified') {
    bannerIcon.textContent = '✓';
    bannerTitle.textContent = 'Identity Status: Verified Authentic';
    bannerDesc.textContent = `Matched against passport ${matchInfo.matched_passport_id || ''}. All serials, dates, and models align.`;
  } else if (status === 'conflict') {
    bannerIcon.textContent = '⚠️';
    bannerTitle.textContent = 'Identity Status: Conflict Flagged!';
    const conflicts = (matchInfo.conflicting_fields || []).map(c => c.field).join(', ');
    bannerDesc.textContent = `Discrepancy detected with existing records on: ${conflicts || 'serial numbers'}.`;
  } else {
    bannerIcon.textContent = '✨';
    bannerTitle.textContent = 'Identity Status: New Product Registration';
    bannerDesc.textContent = 'No conflicting prior passports found. Minted as canonical original.';
  }
}

/* ============================================================
   4. IDENTITY MATCHER & CONFLICT RADAR
   ============================================================ */
function initConflictRadar() {
  const btnCompare = document.getElementById('btn-run-comparison');
  const btnPresetVerified = document.getElementById('btn-preset-verified');
  const btnPresetConflict = document.getElementById('btn-preset-conflict');

  btnCompare.addEventListener('click', executeRadarComparison);

  btnPresetVerified.addEventListener('click', () => {
    document.getElementById('docA-product').value = 'Washing Machine';
    document.getElementById('docA-brand').value = 'LG';
    document.getElementById('docA-model').value = 'T75-SKSF1Z';
    document.getElementById('docA-serial').value = 'LG123456789';
    document.getElementById('docA-date').value = '2026-08-12';
    document.getElementById('docA-seller').value = 'Best Electrical Store';

    document.getElementById('docB-product').value = 'Washing Machine';
    document.getElementById('docB-brand').value = 'LG';
    document.getElementById('docB-model').value = 'T75SKSF1Z';
    document.getElementById('docB-serial').value = 'LG123456789';
    document.getElementById('docB-date').value = '12/08/2026';
    document.getElementById('docB-seller').value = 'Best Electrical Store Sdn Bhd';
    executeRadarComparison();
  });

  btnPresetConflict.addEventListener('click', () => {
    document.getElementById('docA-product').value = 'Washing Machine';
    document.getElementById('docA-brand').value = 'LG';
    document.getElementById('docA-model').value = 'T75-SKSF1Z';
    document.getElementById('docA-serial').value = 'LG123456789';
    document.getElementById('docA-date').value = '2026-08-12';
    document.getElementById('docA-seller').value = 'Best Electrical Store';

    document.getElementById('docB-product').value = 'Washing Machine';
    document.getElementById('docB-brand').value = 'LG';
    document.getElementById('docB-model').value = 'T75SKSF1Z';
    document.getElementById('docB-serial').value = 'LG999999999'; // Conflicting serial
    document.getElementById('docB-date').value = '2026-08-12';
    document.getElementById('docB-seller').value = 'Best Electrical Store';
    executeRadarComparison();
  });
}

function populateMatcherDocA(p) {
  if (p.product) document.getElementById('docA-product').value = p.product;
  if (p.brand) document.getElementById('docA-brand').value = p.brand;
  if (p.model) document.getElementById('docA-model').value = p.model;
  if (p.serial_number) document.getElementById('docA-serial').value = p.serial_number;
  if (p.purchase_date) document.getElementById('docA-date').value = p.purchase_date;
  if (p.seller) document.getElementById('docA-seller').value = p.seller;
}

async function executeRadarComparison() {
  const docA = {
    product: document.getElementById('docA-product').value,
    brand: document.getElementById('docA-brand').value,
    model: document.getElementById('docA-model').value,
    serial_number: document.getElementById('docA-serial').value,
    purchase_date: document.getElementById('docA-date').value,
    seller: document.getElementById('docA-seller').value
  };

  const docB = {
    product: document.getElementById('docB-product').value,
    brand: document.getElementById('docB-brand').value,
    model: document.getElementById('docB-model').value,
    serial_number: document.getElementById('docB-serial').value,
    purchase_date: document.getElementById('docB-date').value,
    seller: document.getElementById('docB-seller').value
  };

  try {
    const res = await fetch('/api/matcher/compare', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ document_a: docA, document_b: docB })
    });

    const data = await res.json();
    renderDiffTable(data);
  } catch (err) {
    showToast(`Comparison error: ${err.message}`);
  }
}

function renderDiffTable(result) {
  const tbody = document.getElementById('diff-table-body');
  const overallBadge = document.getElementById('radar-overall-status');
  tbody.innerHTML = '';

  overallBadge.className = `radar-status-badge ${result.status}`;
  overallBadge.textContent = result.status === 'verified' ? '✓ Identity Verified' : (result.status === 'conflict' ? '⚠️ Conflict Detected!' : 'Inconclusive');

  const fields = [
    { key: 'model', name: 'Model Number', strategy: 'Exact Normalization (Ignore hyphens/dots)' },
    { key: 'serial_number', name: 'Serial Number', strategy: 'Fuzzy Levenshtein Edit Distance (≤2 chars)' },
    { key: 'purchase_date', name: 'Purchase Date', strategy: 'ISO Date Parsing (YYYY-MM-DD)' },
    { key: 'seller', name: 'Seller Name', strategy: 'Token Overlap & Corporate Suffix Stripping' },
    { key: 'brand', name: 'Brand', strategy: 'Case-Insensitive Match' },
    { key: 'product', name: 'Product Category', strategy: 'Subcategory Matching' }
  ];

  fields.forEach(f => {
    const valA = result.document_a[f.key] || '—';
    const valB = result.document_b[f.key] || '—';
    const isConflict = (result.conflicting_fields || []).some(c => c.field === f.key);
    const isMatch = (result.matched_fields || []).includes(f.key);

    const tr = document.createElement('tr');
    tr.className = isConflict ? 'diff-row-conflict' : (isMatch ? 'diff-row-match' : '');

    let badgeHtml = '<span class="text-muted">—</span>';
    if (isConflict) {
      badgeHtml = '<span class="badge-diff-conflict">⚠️ CONFLICT</span>';
    } else if (isMatch) {
      badgeHtml = '<span class="badge-diff-match">✓ MATCH</span>';
    }

    tr.innerHTML = `
      <td><strong>${f.name}</strong></td>
      <td class="font-mono">${valA}</td>
      <td class="font-mono">${valB}</td>
      <td><span class="text-muted" style="font-size:0.8rem;">${f.strategy}</span></td>
      <td>${badgeHtml}</td>
    `;
    tbody.appendChild(tr);
  });
}

/* ============================================================
   5. APPLIANCE OBJECT VISION (YOLO)
   ============================================================ */
function initApplianceVision() {
  const dropzone = document.getElementById('yolo-dropzone');
  const fileInput = document.getElementById('yolo-file-input');
  const btnDetect = document.getElementById('btn-run-detection');
  const btnClear = document.getElementById('btn-clear-yolo');
  const btnRemovePreview = document.getElementById('btn-yolo-remove-preview');

  dropzone.addEventListener('click', (e) => {
    if (e.target !== btnRemovePreview) fileInput.click();
  });

  dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.classList.add('dragover');
  });

  dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));

  dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('dragover');
    if (e.dataTransfer.files.length) {
      handleYoloFileUpload(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener('change', (e) => {
    if (e.target.files.length) {
      handleYoloFileUpload(e.target.files[0]);
    }
  });

  btnRemovePreview.addEventListener('click', (e) => {
    e.stopPropagation();
    clearYoloInput();
  });

  btnClear.addEventListener('click', clearYoloInput);

  btnDetect.addEventListener('click', executeApplianceDetection);
}

function handleYoloFileUpload(file) {
  state.currentYoloFile = file;
  state.currentYoloSamplePath = null;
  const reader = new FileReader();
  reader.onload = (e) => {
    showYoloPreview(e.target.result);
  };
  reader.readAsDataURL(file);
}

function selectYoloSample(item) {
  state.currentYoloFile = null;
  state.currentYoloSamplePath = item.path;
  if (item.thumbnail_base64) {
    showYoloPreview(`data:image/jpeg;base64,${item.thumbnail_base64}`);
  } else {
    showYoloPreview('/static/images/icon.png');
  }
}

function showYoloPreview(src) {
  const previewWrapper = document.getElementById('yolo-preview-wrapper');
  const previewImg = document.getElementById('yolo-image-preview');
  const dropzoneContent = document.querySelector('#yolo-dropzone .dropzone-content');
  const btnDetect = document.getElementById('btn-run-detection');

  previewImg.src = src;
  previewWrapper.classList.remove('hidden');
  dropzoneContent.classList.add('hidden');
  btnDetect.disabled = false;
}

function clearYoloInput() {
  state.currentYoloFile = null;
  state.currentYoloSamplePath = null;
  document.getElementById('yolo-file-input').value = '';
  document.getElementById('yolo-preview-wrapper').classList.add('hidden');
  document.querySelector('#yolo-dropzone .dropzone-content').classList.remove('hidden');
  document.getElementById('btn-run-detection').disabled = true;
  document.querySelectorAll('#yolo-sample-chips .sample-chip').forEach(c => c.classList.remove('active'));
}

async function executeApplianceDetection() {
  const loading = document.getElementById('yolo-loading-state');
  const emptyState = document.getElementById('yolo-empty-state');
  const resultWrapper = document.getElementById('annotated-image-wrapper');
  const resultImg = document.getElementById('annotated-result-img');
  const countBadge = document.getElementById('yolo-count-badge');
  const detectionsList = document.getElementById('detections-list-container');

  loading.classList.remove('hidden');
  emptyState.classList.add('hidden');
  resultWrapper.classList.add('hidden');

  try {
    const formData = new FormData();
    if (state.currentYoloFile) {
      formData.append('file', state.currentYoloFile);
    } else if (state.currentYoloSamplePath) {
      formData.append('sample_path', state.currentYoloSamplePath);
    }
    formData.append('annotate', 'true');

    const res = await fetch('/api/detector/detect', {
      method: 'POST',
      body: formData
    });

    if (!res.ok) throw new Error(`Detection server returned ${res.status}`);
    const data = await res.json();

    countBadge.textContent = `${data.count || 0} Detected`;

    if (data.annotated_image_base64) {
      resultImg.src = `data:image/jpeg;base64,${data.annotated_image_base64}`;
    }

    detectionsList.innerHTML = '';
    (data.detections || []).forEach(d => {
      const pill = document.createElement('div');
      pill.className = 'detection-pill';
      pill.innerHTML = `<span>🎯</span> ${d.label} (${Math.round((d.confidence || 0) * 100)}%) <small style="color:var(--text-muted);">[${d.source || 'yolo'}]</small>`;
      detectionsList.appendChild(pill);
    });

    resultWrapper.classList.remove('hidden');
    showToast(`Detected ${data.count} appliance(s) via YOLOv8!`);
  } catch (err) {
    showToast(`Detection error: ${err.message}`);
    emptyState.classList.remove('hidden');
  } finally {
    loading.classList.add('hidden');
  }
}

/* ============================================================
   6. PASSPORT VAULT & MODAL
   ============================================================ */
function initPassportVault() {
  const searchInput = document.getElementById('vault-search-input');
  const statusFilter = document.getElementById('vault-status-filter');
  const btnRefresh = document.getElementById('btn-refresh-vault');
  const modal = document.getElementById('passport-modal');
  const btnCloseModal = document.getElementById('btn-close-modal');

  searchInput.addEventListener('input', debounce(fetchVaultPassports, 300));
  statusFilter.addEventListener('change', fetchVaultPassports);
  btnRefresh.addEventListener('click', fetchVaultPassports);
  btnCloseModal.addEventListener('click', () => modal.classList.add('hidden'));

  modal.addEventListener('click', (e) => {
    if (e.target === modal) modal.classList.add('hidden');
  });
}

async function fetchVaultPassports() {
  const q = document.getElementById('vault-search-input').value;
  const status = document.getElementById('vault-status-filter').value;
  const tbody = document.getElementById('vault-table-body');

  try {
    const params = new URLSearchParams();
    if (q) params.append('q', q);
    if (status) params.append('status', status);

    const res = await fetch(`/api/dpp/passports?${params.toString()}`);
    const data = await res.json();
    renderVaultTable(data.passports || []);
  } catch (err) {
    console.error('Failed to fetch vault passports:', err);
  }
}

function renderVaultTable(passports) {
  const tbody = document.getElementById('vault-table-body');
  tbody.innerHTML = '';

  if (!passports.length) {
    tbody.innerHTML = '<tr><td colspan="9" class="text-muted" style="text-align:center; padding:2rem;">No passports match the current search criteria.</td></tr>';
    return;
  }

  passports.forEach(p => {
    const tr = document.createElement('tr');
    const status = (p.identity_match && p.identity_match.status) || 'new_product';

    let statusBadge = '<span class="status-pill online"><span class="status-dot"></span> Verified</span>';
    if (status === 'conflict') {
      statusBadge = '<span class="status-pill offline" style="border-color:var(--crimson-border); color:var(--crimson-primary);"><span class="status-dot" style="background:var(--crimson-primary);"></span> Conflict</span>';
    } else if (status === 'new_product') {
      statusBadge = '<span class="status-pill" style="border-color:var(--border-color); color:var(--gold-light);"><span class="status-dot" style="background:var(--gold-primary);"></span> New</span>';
    }

    tr.innerHTML = `
      <td class="font-mono"><strong>${p.passport_id || '—'}</strong></td>
      <td><strong>${p.product || '—'}</strong><br><small class="text-muted">${p.brand || '—'}</small></td>
      <td class="font-mono">${p.model || '—'}</td>
      <td class="font-mono">${p.serial_number || '—'}</td>
      <td class="font-mono">${p.purchase_date || '—'}</td>
      <td>${p.purchase_price ? `${p.currency || 'INR'} ${Number(p.purchase_price).toLocaleString('en-US', { minimumFractionDigits: 2 })}` : '—'}</td>
      <td>${p.seller || '—'}</td>
      <td>${statusBadge}</td>
      <td style="white-space:nowrap;">
        <button class="btn btn-secondary" style="padding:0.3rem 0.6rem; font-size:0.75rem;" onclick="viewPassportModal('${p.passport_id}')">View</button>
        <button class="btn btn-secondary" style="padding:0.3rem 0.6rem; font-size:0.75rem; color:var(--crimson-primary); border-color:var(--crimson-border); margin-left:4px;" onclick="deletePassport('${p.passport_id}')">Delete</button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

window.deletePassport = async function(passportId) {
  if (!confirm(`Are you sure you want to delete passport ${passportId}?`)) return;

  try {
    const res = await fetch(`/api/dpp/passports/${passportId}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Failed to delete passport');
    showToast(`Passport ${passportId} removed from vault.`);
    fetchVaultPassports();
    refreshGlobalStats();
  } catch (err) {
    showToast(`Delete error: ${err.message}`);
  }
};

window.viewPassportModal = async function(passportId) {
  try {
    const res = await fetch(`/api/dpp/passports/${passportId}`);
    if (!res.ok) throw new Error('Passport not found');
    const p = await res.json();

    const status = (p.identity_match && p.identity_match.status) || 'new_product';
    let bannerHtml = '';
    if (status === 'verified') {
      bannerHtml = '<div class="cert-verification-banner verified"><div class="banner-icon">✓</div><div><span class="banner-title">Identity Verified</span><span class="banner-desc">Matched canonical product records.</span></div></div>';
    } else if (status === 'conflict') {
      bannerHtml = '<div class="cert-verification-banner conflict"><div class="banner-icon">⚠️</div><div><span class="banner-title">Conflict Flagged</span><span class="banner-desc">Discrepancy with existing records.</span></div></div>';
    } else {
      bannerHtml = '<div class="cert-verification-banner new_product"><div class="banner-icon">✨</div><div><span class="banner-title">Original Registration</span><span class="banner-desc">First canonical mint for this serial.</span></div></div>';
    }

    const target = document.getElementById('modal-certificate-target');
    target.innerHTML = `
      <div class="certificate-card" style="margin:0;">
        <div class="cert-header">
          <div class="cert-seal"><span class="seal-icon">🏆</span><span class="seal-text">DPP</span></div>
          <div class="cert-title-group">
            <h3 class="cert-product-title">${p.product || 'Product'}</h3>
            <p class="cert-brand-subtitle">${p.brand || 'Brand'}</p>
          </div>
          <div class="cert-id-box"><span class="id-label">ID</span><span class="id-value">${p.passport_id}</span></div>
        </div>
        ${bannerHtml}
        <div class="cert-body-grid">
          <div class="cert-field"><span class="field-label">Model</span><span class="field-value font-mono">${p.model || '—'}</span></div>
          <div class="cert-field"><span class="field-label">Serial</span><span class="field-value font-mono gold-highlight">${p.serial_number || '—'}</span></div>
          <div class="cert-field"><span class="field-label">Date</span><span class="field-value font-mono">${p.purchase_date || '—'}</span></div>
          <div class="cert-field"><span class="field-label">Price</span><span class="field-value">${p.purchase_price ? `${p.currency || 'INR'} ${Number(p.purchase_price).toLocaleString('en-US', { minimumFractionDigits: 2 })}` : '—'}</span></div>
          <div class="cert-field"><span class="field-label">Seller</span><span class="field-value">${p.seller || '—'}</span></div>
          <div class="cert-field"><span class="field-label">Customer</span><span class="field-value">${p.customer_name || '—'}</span></div>
          <div class="cert-field"><span class="field-label">Warranty</span><span class="field-value">${p.warranty || 'Standard'}</span></div>
          <div class="cert-field"><span class="field-label">Category</span><span class="field-value">${p.category || 'Appliance'}</span></div>
        </div>
        <div class="cert-actions" style="margin-top:1.5rem;">
          <button class="btn btn-primary" onclick="exportSinglePassportJson('${p.passport_id}')">
            <span>📥</span> Export JSON
          </button>
        </div>
      </div>
    `;

    document.getElementById('passport-modal').classList.remove('hidden');
  } catch (err) {
    showToast(`Failed to view passport: ${err.message}`);
  }
};

window.exportSinglePassportJson = async function(passportId) {
  try {
    const res = await fetch(`/api/dpp/passports/${passportId}`);
    const p = await res.json();
    const blob = new Blob([JSON.stringify(p, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${passportId}.json`;
    a.click();
    URL.revokeObjectURL(url);
    showToast(`Passport ${passportId} JSON exported!`);
  } catch (e) {
    showToast('Failed to export passport');
  }
};

/* ============================================================
   7. STATS & UTILS
   ============================================================ */
async function refreshGlobalStats() {
  try {
    const res = await fetch('/api/dpp/stats');
    const stats = await res.json();
    document.getElementById('stat-total').textContent = stats.total_passports || 0;
    document.getElementById('stat-verified').textContent = stats.verified_matches || 0;
    document.getElementById('stat-conflicts').textContent = stats.conflicts || 0;
    document.getElementById('stat-brands').textContent = stats.unique_brands || 0;
  } catch (err) {
    console.error('Failed to refresh stats:', err);
  }
}

function showToast(message) {
  const toast = document.getElementById('toast');
  const msgEl = document.getElementById('toast-msg');
  msgEl.textContent = message;
  toast.classList.remove('hidden');
  setTimeout(() => toast.classList.add('hidden'), 3500);
}

function debounce(func, wait) {
  let timeout;
  return function(...args) {
    clearTimeout(timeout);
    timeout = setTimeout(() => func.apply(this, args), wait);
  };
}
