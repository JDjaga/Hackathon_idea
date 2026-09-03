/**
 * HomeMind — Interactive Household Intelligence Dashboard Logic
 * "Your phone remembers everything you own."
 */

document.addEventListener('DOMContentLoaded', () => {
  initTabs();
  initHouseholdHealth();
  initAskMyHouse();
  loadSampleAssets();
  initDocumentStudio();
  initConflictRadar();
  initApplianceVision();
  initPassportVault();
  initOfflineDetector();
});

// Global State Store
const state = {
  currentDppFile: null,
  currentDppSamplePath: null,
  currentYoloFile: null,
  currentYoloSamplePath: null,
  activePassportData: null,
  samples: {},
  recognition: null
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

      if (targetId === 'tab-household-health') {
        fetchHouseholdHealth();
      } else if (targetId === 'tab-passport-vault') {
        fetchVaultPassports();
      }
    });
  });
}

function switchToTab(tabId) {
  const targetTab = document.querySelector(`.nav-tab[data-tab="${tabId}"]`);
  if (targetTab) targetTab.click();
}

/* ============================================================
   2. HOUSEHOLD HEALTH & ATTENTION DASHBOARD
   ============================================================ */
function initHouseholdHealth() {
  fetchHouseholdHealth();
}

async function fetchHouseholdHealth() {
  try {
    const res = await fetch('/api/household/health');
    if (!res.ok) return;
    const data = await res.json();

    // Metrics Bar
    document.getElementById('stat-total').textContent = data.total_products || 0;
    document.getElementById('stat-attention').textContent = data.needs_attention + data.upcoming_issues || 0;
    document.getElementById('stat-rooms').textContent = data.room_count || 0;
    
    // Overview Cards
    document.getElementById('card-urgent-count').textContent = data.needs_attention || 0;
    document.getElementById('card-upcoming-count').textContent = data.upcoming_issues || 0;
    document.getElementById('card-healthy-count').textContent = data.healthy || 0;

    // Render Attention List & Room Grid & Timeline
    renderAttentionItems();
    renderRoomGrid();
    renderTimeline();

  } catch (err) {
    console.error('Failed to fetch household health:', err);
  }
}

async function renderAttentionItems() {
  const container = document.getElementById('attention-items-container');
  if (!container) return;

  try {
    const res = await fetch('/api/household/attention');
    const data = await res.json();
    const items = data.items || [];

    container.innerHTML = '';

    if (!items.length) {
      container.innerHTML = `
        <div class="empty-state">
          <span class="empty-icon">🟢</span>
          <p><strong>All clear!</strong> All registered appliances have active warranties and clean maintenance schedules.</p>
        </div>
      `;
      return;
    }

    items.forEach(item => {
      const alert = item.alerts[0] || { icon: '⚠️', message: 'Attention required', action: 'Review product' };
      const card = document.createElement('div');
      card.className = `attention-item-card ${item.health_status}`;
      
      card.innerHTML = `
        <div class="attention-item-header">
          <span class="item-icon">${alert.icon}</span>
          <div class="item-title-group">
            <h4 class="item-title">${item.brand} ${item.product}</h4>
            <span class="item-room-badge">${item.room}</span>
          </div>
        </div>
        <p class="attention-message">${alert.message}</p>
        <p class="attention-action">👉 <em>${alert.action}</em></p>
        <div class="attention-card-actions">
          <button class="btn btn-primary" style="padding:0.35rem 0.75rem; font-size:0.8rem;" onclick="downloadClaimPack('${item.passport_id}')">
            <span>🛡️</span> Claim Pack
          </button>
          <button class="btn btn-secondary" style="padding:0.35rem 0.75rem; font-size:0.8rem;" onclick="viewPassportModal('${item.passport_id}')">
            View Product
          </button>
        </div>
      `;
      container.appendChild(card);
    });

  } catch (err) {
    container.innerHTML = '<div class="empty-state">Failed to load attention items.</div>';
  }
}

async function renderRoomGrid() {
  const container = document.getElementById('room-grid-container');
  if (!container) return;

  try {
    const res = await fetch('/api/household/rooms');
    const data = await res.json();
    const rooms = data.rooms || {};

    container.innerHTML = '';

    const roomIcons = {
      'Kitchen': '🍳',
      'Living Room': '🛋️',
      'Bedroom': '🛏️',
      'Bathroom': '🚿',
      'Utility': '🧺',
      'Garage': '🚗',
      'Office': '💻',
      'Balcony': '🪴'
    };

    Object.keys(rooms).forEach(roomName => {
      const products = rooms[roomName];
      const icon = roomIcons[roomName] || '🏠';
      const card = document.createElement('div');
      card.className = 'room-tile-card';
      card.onclick = () => filterVaultByRoom(roomName);

      card.innerHTML = `
        <span class="room-tile-icon">${icon}</span>
        <h4 class="room-tile-name">${roomName}</h4>
        <span class="room-tile-count">${products.length} product(s)</span>
      `;
      container.appendChild(card);
    });

  } catch (err) {
    container.innerHTML = '<div class="empty-state">Failed to load room grid.</div>';
  }
}

async function renderTimeline() {
  const container = document.getElementById('timeline-container');
  if (!container) return;

  try {
    const res = await fetch('/api/household/timeline?days=90');
    const data = await res.json();
    const timeline = data.timeline || [];

    container.innerHTML = '';

    if (!timeline.length) {
      container.innerHTML = '<div class="empty-state">No upcoming events in the next 90 days.</div>';
      return;
    }

    timeline.forEach(event => {
      const item = document.createElement('div');
      item.className = `timeline-item ${event.severity}`;
      item.innerHTML = `
        <span class="timeline-date font-mono">${event.date}</span>
        <span class="timeline-icon">${event.icon}</span>
        <div class="timeline-content">
          <strong>${event.title}</strong>
        </div>
      `;
      container.appendChild(item);
    });

  } catch (err) {
    container.innerHTML = '<div class="empty-state">Failed to load timeline.</div>';
  }
}

function filterVaultByRoom(roomName) {
  switchToTab('tab-passport-vault');
  const roomSelect = document.getElementById('vault-room-filter');
  if (roomSelect) {
    roomSelect.value = roomName;
    fetchVaultPassports();
  }
}

/* ============================================================
   3. ASK MY HOUSE (Grounded RAG Chat & Voice)
   ============================================================ */
function initAskMyHouse() {
  const btnSend = document.getElementById('btn-send-ask');
  const askInput = document.getElementById('ask-input');
  const btnVoice = document.getElementById('btn-voice-mic');

  if (btnSend) {
    btnSend.addEventListener('click', () => {
      const q = askInput.value.trim();
      if (q) sendAskQuery(q);
    });
  }

  if (askInput) {
    askInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') {
        const q = askInput.value.trim();
        if (q) sendAskQuery(q);
      }
    });
  }

  // Voice Input Setup (Web Speech API)
  if (btnVoice) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      state.recognition = new SpeechRecognition();
      state.recognition.continuous = false;
      state.recognition.interimResults = false;
      state.recognition.lang = 'en-US';

      state.recognition.onstart = () => {
        btnVoice.classList.add('recording');
        showToast('🎤 Listening... speak your question now.');
      };

      state.recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        askInput.value = transcript;
        sendAskQuery(transcript);
      };

      state.recognition.onerror = (e) => {
        console.error('Speech recognition error:', e.error);
        showToast(`Voice error: ${e.error}`);
        btnVoice.classList.remove('recording');
      };

      state.recognition.onend = () => {
        btnVoice.classList.remove('recording');
      };

      btnVoice.addEventListener('click', () => {
        if (btnVoice.classList.contains('recording')) {
          state.recognition.stop();
        } else {
          state.recognition.start();
        }
      });
    } else {
      btnVoice.title = 'Voice recognition not supported in this browser';
      btnVoice.style.opacity = '0.5';
    }
  }
}

window.askPreset = function(query) {
  switchToTab('tab-ask-house');
  const input = document.getElementById('ask-input');
  if (input) input.value = query;
  sendAskQuery(query);
};

async function sendAskQuery(query) {
  const container = document.getElementById('chat-messages-container');
  const input = document.getElementById('ask-input');
  if (!container || !query) return;

  // Append User Message
  appendChatMessage(container, 'user', query);
  input.value = '';

  // Append Loading Indicator
  const loadingId = 'chat-loading-' + Date.now();
  const loadingDiv = document.createElement('div');
  loadingDiv.className = 'chat-message ai-message loading';
  loadingDiv.id = loadingId;
  loadingDiv.innerHTML = `
    <div class="message-avatar">🏠</div>
    <div class="message-content"><div class="spinner-small"></div> Searching household memory...</div>
  `;
  container.appendChild(loadingDiv);
  container.scrollTop = container.scrollHeight;

  try {
    const res = await fetch('/api/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query })
    });

    const data = await res.json();
    document.getElementById(loadingId)?.remove();

    // Render AI Response
    let formattedAnswer = data.answer || 'No answer generated.';
    formattedAnswer = formattedAnswer.replace(/\n/g, '<br>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    let sourcesHtml = '';
    if (data.sources && data.sources.length) {
      sourcesHtml = '<div class="message-sources"><span class="sources-title">🛡️ Grounded Sources:</span><ul>';
      data.sources.forEach(s => {
        sourcesHtml += `<li><strong>${s.title}</strong> ${s.field ? `(${s.field})` : ''}</li>`;
      });
      sourcesHtml += '</ul></div>';
    }

    let suggestionsHtml = '';
    if (data.suggestions && data.suggestions.length) {
      suggestionsHtml = '<div class="message-suggestions"><span class="suggestions-label">Suggested follow-ups:</span><div class="chips-row">';
      data.suggestions.forEach(s => {
        suggestionsHtml += `<button class="sample-chip" onclick="askPreset('${s.replace(/'/g, "\\'")}')">${s}</button>`;
      });
      suggestionsHtml += '</div></div>';
    }

    const aiMsg = document.createElement('div');
    aiMsg.className = 'chat-message ai-message';
    aiMsg.innerHTML = `
      <div class="message-avatar">🏠</div>
      <div class="message-content">
        <p>${formattedAnswer}</p>
        ${sourcesHtml}
        ${suggestionsHtml}
      </div>
    `;
    container.appendChild(aiMsg);
    container.scrollTop = container.scrollHeight;

  } catch (err) {
    document.getElementById(loadingId)?.remove();
    appendChatMessage(container, 'ai', `⚠️ Failed to execute household search: ${err.message}`);
  }
}

function appendChatMessage(container, sender, text) {
  const msg = document.createElement('div');
  msg.className = `chat-message ${sender}-message`;
  const avatar = sender === 'user' ? '👤' : '🏠';
  msg.innerHTML = `
    <div class="message-avatar">${avatar}</div>
    <div class="message-content"><p>${text}</p></div>
  `;
  container.appendChild(msg);
  container.scrollTop = container.scrollHeight;
}

/* ============================================================
   4. SAMPLE ASSETS LOADER (1-Click Demos)
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

    renderSampleChips('yolo-sample-chips', [
      ...(state.samples.appliance_photos || [])
    ], selectYoloSample);

  } catch (err) {
    console.error('Failed to load sample assets:', err);
  }
}

function renderSampleChips(targetId, items, onClickHandler) {
  const container = document.getElementById(targetId);
  if (!container) return;

  container.innerHTML = '';
  if (!items.length) {
    container.innerHTML = '<span class="text-muted" style="font-size:0.85rem;">No samples found.</span>';
    return;
  }

  items.forEach(item => {
    const chip = document.createElement('button');
    chip.className = 'sample-chip';
    chip.innerHTML = `<span class="chip-icon">📄</span> ${item.name}`;
    chip.addEventListener('click', (e) => {
      e.preventDefault();
      document.querySelectorAll(`#${targetId} .sample-chip`).forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      onClickHandler(item);
    });
    container.appendChild(chip);
  });
}

/* ============================================================
   5. SMART CAPTURE (DOCUMENT STUDIO)
   ============================================================ */
function initDocumentStudio() {
  const dropzone = document.getElementById('dpp-dropzone');
  const fileInput = document.getElementById('dpp-file-input');
  const btnExtract = document.getElementById('btn-run-extraction');
  const btnClear = document.getElementById('btn-clear-dpp');
  const btnRemovePreview = document.getElementById('btn-dpp-remove-preview');

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
  const emptyState = document.getElementById('dpp-empty-state');
  const certResult = document.getElementById('dpp-certificate-result');
  const btnExtract = document.getElementById('btn-run-extraction');
  const badge = document.getElementById('extraction-status-badge');
  const roomSelect = document.getElementById('dpp-room-select');

  loading.classList.remove('hidden');
  emptyState.classList.add('hidden');
  certResult.classList.add('hidden');
  btnExtract.disabled = true;
  badge.textContent = 'Processing...';

  try {
    const formData = new FormData();
    if (state.currentDppFile) {
      formData.append('file', state.currentDppFile);
    } else if (state.currentDppSamplePath) {
      formData.append('sample_path', state.currentDppSamplePath);
    }

    if (roomSelect && roomSelect.value) {
      formData.append('room', roomSelect.value);
    }

    const res = await fetch('/api/dpp/extract', {
      method: 'POST',
      body: formData
    });

    if (!res.ok) throw new Error('Extraction failed');

    const data = await res.json();
    loading.classList.add('hidden');
    certResult.classList.remove('hidden');
    badge.textContent = 'Extracted';

    if (data.results && data.results.length) {
      const stored = data.results[0];
      const passport = stored.passport;
      const match = stored.identity_match;
      state.activePassportData = passport;

      renderCertificate(passport, match, data.raw_ocr_snippet);
      showToast(`Digital Product Passport created: ${passport.product || 'Product'}`);
      fetchHouseholdHealth();
    }

  } catch (err) {
    loading.classList.add('hidden');
    emptyState.classList.remove('hidden');
    badge.textContent = 'Error';
    showToast(`Extraction error: ${err.message}`);
  } finally {
    btnExtract.disabled = false;
  }
}

function renderCertificate(p, match, ocrSnippet) {
  document.getElementById('cert-product').textContent = p.product || 'Unknown Product';
  document.getElementById('cert-brand').textContent = p.brand || 'Unknown Brand';
  document.getElementById('cert-id').textContent = p.passport_id || 'PP-TEMP';

  document.getElementById('cert-model').textContent = p.model || '—';
  document.getElementById('cert-serial').textContent = p.serial_number || '—';
  document.getElementById('cert-date').textContent = p.purchase_date || '—';

  const priceVal = p.purchase_price ? `${p.currency || 'INR'} ${Number(p.purchase_price).toLocaleString('en-US', { minimumFractionDigits: 2 })}` : '—';
  document.getElementById('cert-price').textContent = priceVal;
  document.getElementById('cert-seller').textContent = p.seller || '—';
  document.getElementById('cert-customer').textContent = p.customer_name || '—';
  document.getElementById('cert-warranty-expiry').textContent = p.warranty_expiry_date || p.warranty || '—';
  document.getElementById('cert-room').textContent = p.room || 'Unassigned';

  document.getElementById('cert-ocr-snippet').textContent = ocrSnippet || 'No OCR text extracted.';

  // Banner status
  const banner = document.getElementById('cert-verification-banner');
  const title = document.getElementById('cert-verification-title');
  const desc = document.getElementById('cert-verification-desc');

  const status = (match && match.status) || 'new_product';
  banner.className = 'cert-verification-banner ' + status;

  if (status === 'verified') {
    title.textContent = 'Identity Verified';
    desc.textContent = `Matched canonical product (${match.matched_passport_id}) with high confidence.`;
  } else if (status === 'conflict') {
    title.textContent = 'Identity Conflict Flagged';
    desc.textContent = `Serial/Model discrepancy with stored product ${match.matched_passport_id}.`;
  } else {
    title.textContent = 'Original Household Registration';
    desc.textContent = 'First canonical mint for this serial number.';
  }

  // Setup buttons
  document.getElementById('btn-save-passport').onclick = () => switchToTab('tab-passport-vault');
  document.getElementById('btn-export-json').onclick = () => downloadSinglePassportJson(p);
}

/* ============================================================
   6. IDENTITY MATCHER & CONFLICT RADAR
   ============================================================ */
function initConflictRadar() {
  const btnRun = document.getElementById('btn-run-match');
  if (btnRun) {
    btnRun.addEventListener('click', executeRadarMatch);
  }
}

async function executeRadarMatch() {
  const docA = {
    model: document.getElementById('doc-a-model').value,
    serial_number: document.getElementById('doc-a-serial').value,
    purchase_date: document.getElementById('doc-a-date').value
  };

  const docB = {
    model: document.getElementById('doc-b-model').value,
    serial_number: document.getElementById('doc-b-serial').value,
    purchase_date: document.getElementById('doc-b-date').value
  };

  const badge = document.getElementById('radar-status-badge');
  const emptyState = document.getElementById('radar-empty-state');
  const resultWrapper = document.getElementById('radar-result-wrapper');

  badge.textContent = 'Analyzing...';
  emptyState.classList.add('hidden');
  resultWrapper.classList.remove('hidden');

  try {
    const res = await fetch('/api/matcher/compare', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ document_a: docA, document_b: docB })
    });

    const data = await res.json();
    badge.textContent = data.status.toUpperCase();

    renderRadarResults(data);
    showToast(`Verification status: ${data.status.toUpperCase()}`);
  } catch (err) {
    badge.textContent = 'Error';
    showToast(`Radar error: ${err.message}`);
  }
}

function renderRadarResults(data) {
  const scoreVal = document.getElementById('radar-score-val');
  const statusTxt = document.getElementById('radar-match-status');
  const summaryTxt = document.getElementById('radar-match-summary');
  const circle = document.getElementById('radar-score-circle');
  const tbody = document.getElementById('diff-table-body');

  scoreVal.textContent = data.score || 0;
  statusTxt.textContent = data.status === 'verified' ? 'IDENTITY VERIFIED' : (data.status === 'conflict' ? 'CONFLICT FLAGGED' : 'INSUFFICIENT MATCH');
  summaryTxt.textContent = `Matched ${data.matched_fields.length} identity attributes. Conflicting fields: ${data.conflicting_fields.length}.`;

  if (data.status === 'verified') {
    circle.style.borderColor = 'var(--emerald-primary)';
    circle.style.color = 'var(--emerald-primary)';
  } else if (data.status === 'conflict') {
    circle.style.borderColor = 'var(--crimson-primary)';
    circle.style.color = 'var(--crimson-primary)';
  } else {
    circle.style.borderColor = 'var(--gold-primary)';
    circle.style.color = 'var(--gold-primary)';
  }

  tbody.innerHTML = '';
  (data.field_results || []).forEach(f => {
    const tr = document.createElement('tr');
    let badgeHtml = '<span class="status-pill online"><span class="status-dot"></span> Match</span>';
    if (f.result === 'conflict') {
      badgeHtml = '<span class="status-pill offline" style="border-color:var(--crimson-border); color:var(--crimson-primary);"><span class="status-dot" style="background:var(--crimson-primary);"></span> Conflict</span>';
    } else if (f.result === 'missing') {
      badgeHtml = '<span class="status-pill" style="border-color:var(--border-color); color:var(--text-muted);"><span class="status-dot" style="background:var(--text-muted);"></span> Missing</span>';
    }

    const valA = f.doc_a_val !== null ? f.doc_a_val : '<em>null</em>';
    const valB = f.doc_b_val !== null ? f.doc_b_val : '<em>null</em>';

    tr.innerHTML = `
      <td><strong>${f.field}</strong></td>
      <td class="font-mono">${valA}</td>
      <td class="font-mono">${valB}</td>
      <td><span class="text-muted" style="font-size:0.8rem;">${f.strategy}</span></td>
      <td>${badgeHtml}</td>
    `;
    tbody.appendChild(tr);
  });
}

/* ============================================================
   7. APPLIANCE OBJECT VISION (YOLO)
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

    const res = await fetch('/api/detector/detect', {
      method: 'POST',
      body: formData
    });

    if (!res.ok) throw new Error('Detection failed');

    const data = await res.json();
    loading.classList.add('hidden');
    resultWrapper.classList.remove('hidden');

    if (data.annotated_image_base64) {
      resultImg.src = `data:image/jpeg;base64,${data.annotated_image_base64}`;
    }
    countBadge.textContent = `${data.count} Detected`;

    renderDetectionCards(data.detections || []);
    showToast(`YOLO detected ${data.count} appliance(s)`);

  } catch (err) {
    loading.classList.add('hidden');
    emptyState.classList.remove('hidden');
    showToast(`Detection error: ${err.message}`);
  }
}

function renderDetectionCards(detections) {
  const container = document.getElementById('detection-boxes-list');
  container.innerHTML = '';

  if (!detections.length) {
    container.innerHTML = '<p class="text-muted">No appliances localized in image.</p>';
    return;
  }

  detections.forEach((d, idx) => {
    const card = document.createElement('div');
    card.className = 'detection-card';
    card.innerHTML = `
      <div class="detection-header">
        <span class="detection-class">#${idx + 1} ${d.label}</span>
        <span class="detection-conf">${intConf(d.confidence)}% Confidence</span>
      </div>
      <div class="detection-box font-mono">BBox: [${d.box.map(n => Math.round(n)).join(', ')}]</div>
    `;
    container.appendChild(card);
  });
}

function intConf(val) {
  return Math.round((val || 0) * 100);
}

/* ============================================================
   8. PRODUCT REGISTRY (PASSPORT VAULT)
   ============================================================ */
function initPassportVault() {
  const searchInput = document.getElementById('vault-search-input');
  const roomFilter = document.getElementById('vault-room-filter');
  const statusFilter = document.getElementById('vault-status-filter');
  const btnRefresh = document.getElementById('btn-refresh-vault');
  const modal = document.getElementById('passport-modal');
  const btnCloseModal = document.getElementById('btn-close-modal');

  if (searchInput) searchInput.addEventListener('input', fetchVaultPassports);
  if (roomFilter) roomFilter.addEventListener('change', fetchVaultPassports);
  if (statusFilter) statusFilter.addEventListener('change', fetchVaultPassports);
  if (btnRefresh) btnRefresh.addEventListener('click', fetchVaultPassports);

  if (btnCloseModal) btnCloseModal.addEventListener('click', () => modal.classList.add('hidden'));
  if (modal) {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) modal.classList.add('hidden');
    });
  }
}

async function fetchVaultPassports() {
  const q = document.getElementById('vault-search-input')?.value || '';
  const room = document.getElementById('vault-room-filter')?.value || '';
  const status = document.getElementById('vault-status-filter')?.value || '';

  try {
    const params = new URLSearchParams();
    if (q) params.append('q', q);
    if (status) params.append('status', status);

    const res = await fetch(`/api/dpp/passports?${params.toString()}`);
    const data = await res.json();
    let passports = data.passports || [];

    // Filter by room if selected
    if (room) {
      passports = passports.filter(p => (p.room || '').toLowerCase() === room.toLowerCase());
    }

    renderVaultTable(passports);
  } catch (err) {
    console.error('Failed to fetch vault passports:', err);
  }
}

function renderVaultTable(passports) {
  const tbody = document.getElementById('vault-table-body');
  if (!tbody) return;
  tbody.innerHTML = '';

  if (!passports.length) {
    tbody.innerHTML = '<tr><td colspan="8" class="text-muted" style="text-align:center; padding:2rem;">No products match the search criteria.</td></tr>';
    return;
  }

  passports.forEach(p => {
    const tr = document.createElement('tr');
    const health = p.health_status || 'good';

    let statusBadge = '<span class="status-pill online"><span class="status-dot"></span> Good</span>';
    if (health === 'urgent' || health === 'expired') {
      statusBadge = `<span class="status-pill offline" style="border-color:var(--crimson-border); color:var(--crimson-primary);"><span class="status-dot" style="background:var(--crimson-primary);"></span> ${health.toUpperCase()}</span>`;
    } else if (health === 'attention') {
      statusBadge = '<span class="status-pill" style="border-color:var(--border-color); color:var(--gold-light);"><span class="status-dot" style="background:var(--gold-primary);"></span> ATTENTION</span>';
    }

    tr.innerHTML = `
      <td class="font-mono"><strong>${p.passport_id || '—'}</strong></td>
      <td><strong>${p.product || '—'}</strong><br><small class="text-muted">${p.brand || '—'}</small></td>
      <td><span class="item-room-badge">${p.room || 'Unassigned'}</span></td>
      <td class="font-mono">${p.model || '—'}</td>
      <td class="font-mono">${p.serial_number || '—'}</td>
      <td class="font-mono">${p.warranty_expiry_date || p.purchase_date || '—'}</td>
      <td>${statusBadge}</td>
      <td style="white-space:nowrap;">
        <button class="btn btn-secondary" style="padding:0.3rem 0.6rem; font-size:0.75rem;" onclick="viewPassportModal('${p.passport_id}')">View</button>
        <button class="btn btn-secondary" style="padding:0.3rem 0.6rem; font-size:0.75rem; margin-left:4px;" onclick="downloadClaimPack('${p.passport_id}')">Claim Pack</button>
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
    showToast(`Passport ${passportId} removed from registry.`);
    fetchVaultPassports();
    fetchHouseholdHealth();
  } catch (err) {
    showToast(`Delete error: ${err.message}`);
  }
};

window.downloadClaimPack = async function(passportId) {
  try {
    const res = await fetch(`/api/household/claim-pack/${passportId}`, { method: 'POST' });
    if (!res.ok) throw new Error('Failed to generate claim pack');
    const pack = await res.json();
    
    const blob = new Blob([JSON.stringify(pack, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `Warranty_Claim_Pack_${passportId}.json`;
    a.click();
    URL.revokeObjectURL(url);
    showToast(`🛡️ Warranty Claim Pack downloaded for ${pack.product.brand} ${pack.product.name}!`);
  } catch (err) {
    showToast(`Claim Pack error: ${err.message}`);
  }
};

window.viewPassportModal = async function(passportId) {
  try {
    const res = await fetch(`/api/dpp/passports/${passportId}`);
    if (!res.ok) throw new Error('Passport not found');
    const p = await res.json();

    const health = p.health_status || 'good';
    let bannerHtml = '';
    if (health === 'good') {
      bannerHtml = '<div class="cert-verification-banner verified"><div class="banner-icon">✓</div><div><span class="banner-title">Active & Healthy</span><span class="banner-desc">Warranty active and maintenance on schedule.</span></div></div>';
    } else if (health === 'attention' || health === 'urgent') {
      bannerHtml = '<div class="cert-verification-banner conflict"><div class="banner-icon">⚠️</div><div><span class="banner-title">Action Required</span><span class="banner-desc">Warranty expiring soon or maintenance due.</span></div></div>';
    } else {
      bannerHtml = '<div class="cert-verification-banner conflict" style="border-color:var(--crimson-border);"><div class="banner-icon">🔴</div><div><span class="banner-title">Warranty Expired</span><span class="banner-desc">Product warranty coverage has ended.</span></div></div>';
    }

    let docsHtml = '';
    if (p.linked_documents && p.linked_documents.length) {
      docsHtml = '<div style="margin-top:1rem;"><strong>Linked Documents:</strong><ul>';
      p.linked_documents.forEach(d => {
        docsHtml += `<li>${d.type.replace('_', ' ').toUpperCase()} (${d.source}) — ${d.snippet || ''}</li>`;
      });
      docsHtml += '</ul></div>';
    }

    const target = document.getElementById('modal-certificate-target');
    target.innerHTML = `
      <div class="certificate-card" style="margin:0;">
        <div class="cert-header">
          <div class="cert-seal"><span class="seal-icon">🏠</span><span class="seal-text">DPP</span></div>
          <div class="cert-title-group">
            <h3 class="cert-product-title">${p.product || 'Product'}</h3>
            <p class="cert-brand-subtitle">${p.brand || 'Brand'}</p>
          </div>
          <div class="cert-id-box"><span class="id-label">PASSPORT ID</span><span class="id-value font-mono">${p.passport_id}</span></div>
        </div>
        ${bannerHtml}
        <div class="cert-body-grid">
          <div class="cert-field"><span class="field-label">Room Location</span><span class="field-value">${p.room || 'Unassigned'}</span></div>
          <div class="cert-field"><span class="field-label">Model Number</span><span class="field-value font-mono">${p.model || '—'}</span></div>
          <div class="cert-field"><span class="field-label">Serial Number</span><span class="field-value font-mono gold-highlight">${p.serial_number || '—'}</span></div>
          <div class="cert-field"><span class="field-label">Purchase Date</span><span class="field-value font-mono">${p.purchase_date || '—'}</span></div>
          <div class="cert-field"><span class="field-label">Warranty Expiry</span><span class="field-value font-mono">${p.warranty_expiry_date || p.warranty || '—'}</span></div>
          <div class="cert-field"><span class="field-label">Next Maintenance</span><span class="field-value font-mono">${p.next_maintenance_date || '—'}</span></div>
          <div class="cert-field"><span class="field-label">Purchase Price</span><span class="field-value">${p.purchase_price ? `${p.currency || 'INR'} ${Number(p.purchase_price).toLocaleString('en-US', { minimumFractionDigits: 2 })}` : '—'}</span></div>
          <div class="cert-field"><span class="field-label">Merchant / Seller</span><span class="field-value">${p.seller || '—'}</span></div>
        </div>
        ${docsHtml}
        <div class="cert-actions" style="margin-top:1.5rem;">
          <button class="btn btn-primary" onclick="downloadClaimPack('${p.passport_id}')">
            <span>🛡️</span> Download Claim Pack
          </button>
          <button class="btn btn-secondary" onclick="downloadSinglePassportJson(state.activePassportData || ${JSON.stringify(p).replace(/"/g, '&quot;')})">
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

function downloadSinglePassportJson(p) {
  const blob = new Blob([JSON.stringify(p, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${p.passport_id || 'passport'}.json`;
  a.click();
  URL.revokeObjectURL(url);
  showToast(`Passport ${p.passport_id} JSON exported!`);
}

/* ============================================================
   9. OFFLINE DETECTOR & TOAST UTILITIES
   ============================================================ */
function initOfflineDetector() {
  const banner = document.getElementById('offline-banner');

  function updateStatus() {
    if (!navigator.onLine) {
      if (banner) banner.classList.remove('hidden');
      showToast('🔒 Offline Mode — Device NPU active');
    } else {
      if (banner) banner.classList.add('hidden');
    }
  }

  window.addEventListener('online', updateStatus);
  window.addEventListener('offline', updateStatus);
  updateStatus();
}

function showToast(message, duration = 3500) {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.innerHTML = `<span class="toast-icon">ℹ️</span> <span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    setTimeout(() => toast.remove(), 300);
  }, duration);
}
