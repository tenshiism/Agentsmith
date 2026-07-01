// --- Font loader: local first, CDN fallback, cache to disk ---
const FONT_DEFS = [
  { family: 'Inter', weight: '400', local: '/assets/fonts/inter-latin.woff2', cdn: 'https://fonts.gstatic.com/s/inter/v20/UcC73FwrK3iLTeHuS_nVMrMxCp50SjIa1ZL7.woff2' },
  { family: 'Inter', weight: '600', local: '/assets/fonts/inter-latin.woff2', cdn: 'https://fonts.gstatic.com/s/inter/v20/UcC73FwrK3iLTeHuS_nVMrMxCp50SjIa1ZL7.woff2' },
  { family: 'Inter', weight: '700', local: '/assets/fonts/inter-latin.woff2', cdn: 'https://fonts.gstatic.com/s/inter/v20/UcC73FwrK3iLTeHuS_nVMrMxCp50SjIa1ZL7.woff2' },
  { family: 'Press Start 2P', weight: '400', local: '/assets/fonts/pressstart2p-latin.woff2', cdn: 'https://fonts.gstatic.com/s/pressstart2p/v15/e3t4euO8T-267oIAQAu6jDQyK3nVivM.woff2' },
];

async function loadFont(def) {
  try {
    const f = new FontFace(def.family, `url(${def.local})`, { weight: def.weight, display: 'swap' });
    await f.load();
    document.fonts.add(f);
    return;
  } catch (_) {}
  try {
    const resp = await fetch(def.cdn);
    if (!resp.ok) throw new Error(resp.status);
    const buf = await resp.arrayBuffer();
    const blob = new Blob([buf], { type: 'font/woff2' });
    const url = URL.createObjectURL(blob);
    const f = new FontFace(def.family, `url(${url})`, { weight: def.weight, display: 'swap' });
    await f.load();
    document.fonts.add(f);
    URL.revokeObjectURL(url);
    fetch('/api/cache-font', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: def.local, data: Array.from(new Uint8Array(buf)) }),
    }).catch(() => {});
  } catch (_) {}
}

(async () => { for (const d of FONT_DEFS) await loadFont(d); })();

let lastCommentary = '';
let commentaryTimeout = null;
let lastStatus = 'idle';
var ws = null;
var wsReconnectDelay = 1000;

document.getElementById('mode-select').addEventListener('change', (e) => {
  const mode = e.target.value;
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'set_mode', mode }));
  }
});

const CHARACTERS = ['neuro', 'energetic', 'chill', 'sarcastic', 'lore_keeper'];
const CHARACTER_LABELS = { neuro: 'Neuro', energetic: 'Energetic', chill: 'Chill', sarcastic: 'Sarcastic', lore_keeper: 'Lore Keeper' };
let charIdx = 0;

const STRATEGIES = ['balanced', 'aggressive', 'cautious', 'explorer'];
const STRATEGY_LABELS = { balanced: 'Balanced', aggressive: 'Aggressive', cautious: 'Cautious', explorer: 'Explorer' };
let stratIdx = 0;

function setCharacter(idx) {
  charIdx = (idx + CHARACTERS.length) % CHARACTERS.length;
  const name = CHARACTERS[charIdx];
  document.getElementById('char-label').textContent = CHARACTER_LABELS[name];
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'change_character', personality: name }));
  }
  const personalitySel = document.getElementById('cfg-personality');
  if (personalitySel) personalitySel.value = name;
}

function setStrategy(idx) {
  stratIdx = (idx + STRATEGIES.length) % STRATEGIES.length;
  const name = STRATEGIES[stratIdx];
  document.getElementById('strategy-name').textContent = STRATEGY_LABELS[name];
  document.getElementById('strategy-display').textContent = 'STRATEGY: ' + name.toUpperCase();
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'set_config', config: { strategy: name } }));
  }
  const stratSel = document.getElementById('cfg-strategy');
  if (stratSel) stratSel.value = name;
}

document.getElementById('char-prev').addEventListener('click', () => setCharacter(charIdx - 1));
document.getElementById('char-next').addEventListener('click', () => setCharacter(charIdx + 1));
document.getElementById('strat-prev').addEventListener('click', () => setStrategy(stratIdx - 1));
document.getElementById('strat-next').addEventListener('click', () => setStrategy(stratIdx + 1));

// Test panel toggle
document.getElementById('test-toggle').addEventListener('click', () => {
  const body = document.getElementById('test-body');
  const arrow = document.getElementById('test-arrow');
  if (body.style.display === 'none') {
    body.style.display = '';
    arrow.textContent = '[-]';
  } else {
    body.style.display = 'none';
    arrow.textContent = '[+]';
  }
});

// Settings section toggles
document.querySelectorAll('.cfg-section-toggle').forEach(toggle => {
  toggle.addEventListener('click', () => {
    const body = toggle.nextElementSibling;
    const arrow = toggle.querySelector('.cfg-arrow');
    if (body.style.display === 'none') {
      body.style.display = '';
      arrow.textContent = '[-]';
    } else {
      body.style.display = 'none';
      arrow.textContent = '[+]';
    }
  });
});

// Test button presses
document.querySelectorAll('.test-btn').forEach(btn => {
  btn.addEventListener('mousedown', () => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'test_key', key: btn.dataset.key, down: true }));
    }
  });
  btn.addEventListener('mouseup', () => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'test_key', key: btn.dataset.key, down: false }));
    }
  });
  btn.addEventListener('mouseleave', () => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'test_key', key: btn.dataset.key, down: false }));
    }
  });
});

const aiBtn = document.getElementById('ai-toggle');
aiBtn.addEventListener('click', () => {
  const newStatus = lastStatus === 'running' ? 'idle' : 'running';
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'set_status', status: newStatus }));
  }
});

// --- Model data loaded from /api/model-pricing ---
let MODEL_DATA = null;
let showAllModels = localStorage.getItem('show-all-models') === 'true';
function getModelCategories() {
  if (!MODEL_DATA) return {};
  return showAllModels ? MODEL_DATA.categories_all : MODEL_DATA.categories_top;
}

fetch('/api/model-pricing')
  .then(r => r.json())
  .then(data => { MODEL_DATA = data; })
  .catch(() => { MODEL_DATA = { pricing: {}, categories_top: {}, categories_all: {} }; });
const BASE_URLS = {
  "openrouter": "https://openrouter.ai/api/v1",
  "openai": "https://api.openai.com/v1",
  "kobold": "http://localhost:5001/v1",
};

function priceLabel(p) {
  if (p === 0) return 'free';
  const perM = p * 1000000;
  if (perM >= 1) return '$' + perM.toFixed(2) + '/M';
  if (perM >= 0.01) return '$' + perM.toFixed(3) + '/M';
  return '$' + perM.toFixed(4) + '/M';
}

function priceSingle(p) {
  const per1k = p * 1000;
  if (per1k >= 0.1) return '$' + per1k.toFixed(2) + '/1k';
  return '$' + (p * 1000000).toFixed(2) + '/M';
}

// --- Context menu for model selection ---
let _activeCtxMenu = null;

function buildCtxMenu(provider, onSelect) {
  const categories = getModelCategories()[provider];
  const menu = document.createElement('div');
  menu.className = 'ctx-menu';
  menu.style.cssText = 'position:fixed;z-index:10000;background:#1e1e2e;border:1px solid rgba(255,107,53,0.3);border-radius:6px;padding:4px 0;min-width:260px;box-shadow:0 8px 24px rgba(0,0,0,0.6);font-size:12px;color:#ccc;';

  if (!categories || Object.keys(categories).length === 0) {
    const item = document.createElement('div');
    item.className = 'ctx-item';
    item.style.cssText = 'padding:6px 16px;cursor:default;color:#666;';
    item.textContent = 'No models available';
    menu.appendChild(item);
    return menu;
  }

  for (const [catName, models] of Object.entries(categories)) {
    const row = document.createElement('div');
    row.style.cssText = 'position:relative;display:flex;align-items:center;justify-content:space-between;padding:5px 12px;cursor:pointer;white-space:nowrap;';
    row.innerHTML = `<span>${catName}</span><span style="font-size:9px;color:#888;">\u25B6</span>`;
    row.onmouseenter = () => row.style.background = 'rgba(255,107,53,0.15)';
    row.onmouseleave = () => { row.style.background = ''; subMenu.style.display = 'none'; };

    const subMenu = document.createElement('div');
    subMenu.className = 'ctx-submenu';
    subMenu.style.cssText = 'display:none;position:absolute;left:100%;top:-4px;background:#1e1e2e;border:1px solid rgba(255,107,53,0.3);border-radius:6px;padding:4px 0;min-width:320px;box-shadow:0 8px 24px rgba(0,0,0,0.6);';

    for (const m of models) {
      if (m === "") continue;
      const mi = document.createElement('div');
      mi.style.cssText = 'padding:4px 12px;cursor:pointer;white-space:nowrap;display:flex;justify-content:space-between;gap:12px;';
      const p = MODEL_DATA?.pricing?.[m];
      let priceText = '';
      if (p) {
        if (p.prompt === 0 && p.completion === 0) priceText = 'free';
        else {
          priceText = `${priceLabel(p.prompt)} in / ${priceLabel(p.completion)} out`;
          if (p.image > 0) priceText += ` +${priceSingle(p.image)} img`;
        }
      }
      mi.innerHTML = `<span>${m}</span><span style="color:#888;font-size:10px;">${priceText}</span>`;
      mi.onmouseenter = () => mi.style.background = 'rgba(255,107,53,0.15)';
      mi.onmouseleave = () => mi.style.background = '';
      mi.addEventListener('click', (e) => { e.stopPropagation(); onSelect(m); closeCtxMenu(); });
      subMenu.appendChild(mi);
    }

    row.onmouseenter = () => { subMenu.style.display = 'block'; };
    row.appendChild(subMenu);
    menu.appendChild(row);
  }
  return menu;
}

function closeCtxMenu() {
  if (_activeCtxMenu) { _activeCtxMenu.remove(); _activeCtxMenu = null; }
}

document.addEventListener('click', closeCtxMenu);

function setupModelPicker(btnId, labelId, hiddenId, providerId, customUrlId) {
  const btn = document.getElementById(btnId);
  const label = document.getElementById(labelId);
  const hidden = document.getElementById(hiddenId);
  const provEl = document.getElementById(providerId);
  const customUrl = document.getElementById(customUrlId);

  btn.addEventListener('click', (e) => {
    e.stopPropagation();
    closeCtxMenu();
    const provider = provEl.value;
    const menu = buildCtxMenu(provider, (model) => {
      hidden.value = model;
      label.textContent = model;
    });
    const rect = btn.getBoundingClientRect();
    menu.style.left = rect.left + 'px';
    menu.style.top = rect.bottom + 'px';
    document.body.appendChild(menu);
    _activeCtxMenu = menu;
  });

  provEl.addEventListener('change', () => {
    const p = provEl.value;
    hidden.value = '';
    label.textContent = '---';
    customUrl.style.display = p === '__custom__' ? '' : 'none';
    if (p !== '__custom__') customUrl.value = '';
    if (p === 'kobold') detectKoboldModel(customUrl, hidden, label);
  });
}

function detectKoboldModel(customUrlEl, hiddenEl, labelEl) {
  const baseUrl = (customUrlEl.value || BASE_URLS['kobold'] || 'http://localhost:5001/v1').replace(/\/$/, '');
  labelEl.textContent = 'Detecting...';
  fetch(baseUrl + '/v1/models', { signal: AbortSignal.timeout(3000) })
    .then(r => r.json())
    .then(data => {
      const models = data?.data;
      if (Array.isArray(models) && models.length > 0) {
        const name = models[0].id || models[0].name || '';
        hiddenEl.value = name;
        labelEl.textContent = name || 'Detected (unknown)';
      } else {
        hiddenEl.value = '';
        labelEl.textContent = 'Not detected';
      }
    })
    .catch(() => {
      hiddenEl.value = '';
      labelEl.textContent = 'Not detected';
    });
}

function getBaseUrl(providerId, customUrlId) {
  const provider = document.getElementById(providerId).value;
  if (provider === '__custom__') return document.getElementById(customUrlId).value || '';
  return BASE_URLS[provider] || '';
}

setupModelPicker('cfg-action-model-btn', 'cfg-action-model-label', 'cfg-action-model', 'cfg-action-provider', 'cfg-action-url-custom');
setupModelPicker('cfg-comm-model-btn', 'cfg-comm-model-label', 'cfg-comm-model', 'cfg-comm-provider', 'cfg-comm-url-custom');

// Model list toggle
const showAllCheckbox = document.getElementById('cfg-show-all-models');
if (showAllCheckbox) {
  showAllCheckbox.checked = showAllModels;
  showAllCheckbox.addEventListener('change', () => {
    showAllModels = showAllCheckbox.checked;
    localStorage.setItem('show-all-models', showAllModels);
  });
}

// Settings modal
const settingsModal = document.getElementById('settings-modal');
document.getElementById('settings-toggle').addEventListener('click', () => {
  settingsModal.style.display = 'flex';
});
document.getElementById('settings-close').addEventListener('click', () => {
  settingsModal.style.display = 'none';
});
document.getElementById('settings-expand').addEventListener('click', (e) => {
  e.stopPropagation();
  const dialog = document.getElementById('settings-dialog');
  const expanded = dialog.dataset.expanded === 'true';
  if (expanded) {
    dialog.style.width = '';
    dialog.dataset.expanded = 'false';
    e.target.textContent = '[+]';
  } else {
    dialog.style.width = 'min(85vw, 1400px)';
    dialog.dataset.expanded = 'true';
    e.target.textContent = '[-]';
  }
});
document.getElementById('cfg-game').addEventListener('change', (e) => {
  const path = e.target.value;
  if (!path) return;
  const name = e.target.options[e.target.selectedIndex].text;
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'change_game', rom_path: path, game_name: name }));
    document.getElementById('cfg-game').disabled = true;
    setTimeout(() => { document.getElementById('cfg-game').disabled = false; }, 3000);
  }
  e.target.value = '';
});

let allGames = [];
let consoles = ['All'];
let consoleIdx = 0;

function filterGames() {
  const sel = document.getElementById('cfg-game');
  const label = document.getElementById('console-label');
  const cur = consoles[consoleIdx];
  label.textContent = cur;
  const prev = sel.value;
  const filtered = cur === 'All' ? allGames : allGames.filter(g => g.console === cur);
  sel.innerHTML = '<option value="">-- Select game --</option>' +
    filtered.map(g => '<option value="' + g.path + '">' + g.name + '</option>').join('');
  if (prev && filtered.some(g => g.path === prev)) {
    sel.value = prev;
  }
}

document.getElementById('console-prev').addEventListener('click', () => {
  consoleIdx = (consoleIdx - 1 + consoles.length) % consoles.length;
  filterGames();
});
document.getElementById('console-next').addEventListener('click', () => {
  consoleIdx = (consoleIdx + 1) % consoles.length;
  filterGames();
});
settingsModal.addEventListener('click', (e) => {
  if (e.target === settingsModal) settingsModal.style.display = 'none';
});
document.getElementById('settings-save').addEventListener('click', () => {
  const config = {
    min_llm_interval: parseFloat(document.getElementById('cfg-action-interval').value) || 12,
    min_commentary_interval: parseFloat(document.getElementById('cfg-comm-interval').value) || 30,
    shared_ai_cooldown: document.getElementById('cfg-shared-cooldown').checked,
    retry_rate_base: parseFloat(document.getElementById('cfg-retry-base').value) || 2,
    retry_rate_max: parseFloat(document.getElementById('cfg-retry-max').value) || 30,
    action_model_provider: document.getElementById('cfg-action-provider').value || 'openrouter',
    action_model_name: document.getElementById('cfg-action-model').value || '',
    action_model_base_url: getBaseUrl('cfg-action-provider', 'cfg-action-url-custom'),
    action_temperature: parseFloat(document.getElementById('cfg-action-temp').value) || 0.7,
    action_max_tokens: parseInt(document.getElementById('cfg-action-maxtokens').value) || 16,
    commentary_model_provider: document.getElementById('cfg-comm-provider').value || 'openrouter',
    commentary_model_name: document.getElementById('cfg-comm-model').value || '',
    commentary_model_base_url: getBaseUrl('cfg-comm-provider', 'cfg-comm-url-custom'),
    commentary_temperature: parseFloat(document.getElementById('cfg-comm-temp').value) || 0.9,
    commentary_max_tokens: parseInt(document.getElementById('cfg-comm-maxtokens').value) || 120,
    strategy: document.getElementById('cfg-strategy').value || 'balanced',
    personality: document.getElementById('cfg-personality').value || 'energetic',
    tts_enabled: document.getElementById('cfg-tts-enabled').checked,
    commentary_enabled: document.getElementById('cfg-commentary-enabled').checked,
    action_enabled: document.getElementById('cfg-action-enabled').checked,
    commentary_context: document.getElementById('cfg-commentary-context').checked,
    vtuber_model: parseInt(document.getElementById('cfg-vtuber-model').value) || 0,
    eye_tracking: document.getElementById('cfg-eye-tracking').checked,
    eye_interval: parseFloat(document.getElementById('cfg-eye-interval').value) || 2.0,
    lip_sync: document.getElementById('cfg-lip-sync').value || 'sine',
    blink_interval: parseFloat(document.getElementById('cfg-blink-interval').value) || 3.5,
    eye_range: parseFloat(document.getElementById('cfg-eye-range').value) || 0.4,
    idle_sway: document.getElementById('cfg-idle-sway').checked,
    sway_strength: parseFloat(document.getElementById('cfg-sway-strength').value) || 0.003,
    mood_expressions: document.getElementById('cfg-mood-expressions').checked,
    screenshot_noise: document.getElementById('cfg-screenshot-noise').checked,
  };
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'set_config', config }));
  }
  settingsModal.style.display = 'none';
});
document.getElementById('ai-stop').addEventListener('click', () => {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'set_status', status: 'idle' }));
  }
});

// --- Avatar panel controls ---
let avatarFrozen = false;

document.getElementById('av-reset-cam').addEventListener('click', () => {
  const bridge = window.avatarBridge;
  if (bridge && bridge.resetCamera) bridge.resetCamera();
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'avatar_reset_camera' }));
  }
});

document.getElementById('av-speak-now').addEventListener('click', () => {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'voice_trigger' }));
  }
});

document.getElementById('av-eye-status').addEventListener('click', () => {
  const eyeEl = document.getElementById('av-eye-status');
  const isOn = eyeEl.textContent === 'ON';
  const newState = !isOn;
  eyeEl.textContent = newState ? 'ON' : 'OFF';
  eyeEl.style.color = newState ? '#4caf50' : '#f44336';
  const eyeCheck = document.getElementById('cfg-eye-tracking');
  if (eyeCheck) eyeCheck.checked = newState;
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'avatar_config', config: { eye_tracking: newState } }));
  }
});

// Animations panel toggle
document.getElementById('anim-toggle').addEventListener('click', () => {
  const body = document.getElementById('anim-body');
  const arrow = document.getElementById('anim-arrow');
  if (body.style.display === 'none') {
    body.style.display = '';
    arrow.textContent = '[-]';
  } else {
    body.style.display = 'none';
    arrow.textContent = '[+]';
  }
});

// VRMA animation buttons
document.querySelectorAll('.anim-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const index = parseInt(btn.dataset.index, 10);
    const bridge = window.avatarBridge;
    if (bridge && bridge.loadAndPlayVRMA) bridge.loadAndPlayVRMA(index);
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'avatar_vrma_load', index }));
      ws.send(JSON.stringify({ type: 'avatar_vrma_play' }));
    }
  });
});

document.getElementById('anim-play').addEventListener('click', () => {
  const bridge = window.avatarBridge;
  if (bridge && bridge.loadAndPlayVRMA && bridge.currentVrmaIndex >= 0) {
    // Re-trigger: loadAndPlayVRMA again with current index
    // Actually just play the loaded clip
  }
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'avatar_vrma_play' }));
  }
});

document.getElementById('anim-stop').addEventListener('click', () => {
  const bridge = window.avatarBridge;
  if (bridge && bridge.stopVRMA) bridge.stopVRMA();
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'avatar_vrma_stop' }));
  }
});

document.getElementById('av-freeze').addEventListener('click', () => {
  avatarFrozen = !avatarFrozen;
  const btn = document.getElementById('av-freeze');
  btn.textContent = avatarFrozen ? 'UNFREEZE' : 'FREEZE';
  btn.className = 'ai-btn' + (avatarFrozen ? ' frozen' : ' ai-idle');
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'avatar_freeze', value: avatarFrozen }));
  }
});

function connectWS() {
  ws = new WebSocket(`ws://${location.host}/ws`);

  ws.onmessage = (event) => {
    wsReconnectDelay = 1000;
    const data = JSON.parse(event.data);

    if (data.screenshot || data.screenshot_full) {
      const src = useAiView ? data.screenshot : data.screenshot_full;
      if (src) {
        document.getElementById('game-screen').src = 'data:image/jpeg;base64,' + src;
      }
    }

    const actionEl = document.getElementById('last-action');
    if (actionEl && data.last_action !== undefined) {
      actionEl.textContent = data.last_action || 'none';
    }

    const commentaryEl = document.getElementById('commentary-text');
    if (commentaryEl && data.commentary && data.commentary !== lastCommentary) {
      lastCommentary = data.commentary;
      commentaryEl.textContent = data.commentary;
      commentaryEl.classList.remove('fade-in');
      void commentaryEl.offsetWidth;
      commentaryEl.classList.add('fade-in');

      const bridge = window.avatarBridge;
      if (bridge) {
        bridge.isSpeaking = true;
      }
      document.getElementById('vtuber-indicator').className = 'vtuber-indicator active';
      if (commentaryTimeout) clearTimeout(commentaryTimeout);
      commentaryTimeout = setTimeout(() => {
        if (bridge) {
          bridge.isSpeaking = false;
          bridge.speechEndTime = bridge.clock.elapsedTime + 0.5;
        }
        commentaryTimeout = null;
        document.getElementById('vtuber-indicator').className = 'vtuber-indicator idle';
      }, Math.max(2000, data.commentary.length * 60));
    }

    if (data.tts_speaking) {
      const bridge = window.avatarBridge;
      if (bridge) bridge.isSpeaking = true;
      document.getElementById('vtuber-indicator').className = 'vtuber-indicator active';
      if (commentaryTimeout) clearTimeout(commentaryTimeout);
    } else if (window.avatarBridge && window.avatarBridge.isSpeaking && commentaryTimeout === null) {
      window.avatarBridge.isSpeaking = false;
      window.avatarBridge.speechEndTime = window.avatarBridge.clock.elapsedTime + 0.3;
      document.getElementById('vtuber-indicator').className = 'vtuber-indicator idle';
    }

    if (data.audio_amplitude !== undefined) {
      const bridge = window.avatarBridge;
      if (bridge) bridge.setAudioAmplitude(data.audio_amplitude);
    }

    if (data.avatar_mood) {
      const bridge = window.avatarBridge;
      if (bridge) bridge.setMood(data.avatar_mood);
      const moodEl = document.getElementById('av-mood');
      if (moodEl) {
        moodEl.textContent = data.avatar_mood;
        moodEl.className = data.avatar_mood;
      }
    }

    if (data.type === 'avatar_reset_camera') {
      const bridge = window.avatarBridge;
      if (bridge && bridge.resetCamera) bridge.resetCamera();
    }

    if (data.type === 'avatar_freeze') {
      avatarFrozen = data.value;
      const btn = document.getElementById('av-freeze');
      if (btn) {
        btn.textContent = avatarFrozen ? 'UNFREEZE' : 'FREEZE';
        btn.className = 'ai-btn' + (avatarFrozen ? ' frozen' : ' ai-idle');
      }
    }

    if (data.type === 'avatar_config') {
      const ac = data.config;
      const eyeEl = document.getElementById('av-eye-status');
      if (eyeEl && ac.eye_tracking !== undefined) {
        eyeEl.textContent = ac.eye_tracking ? 'ON' : 'OFF';
        eyeEl.style.color = ac.eye_tracking ? '#4caf50' : '#f44336';
      }
    }

    if (data.type === 'avatar_vrma_mood') {
      const bridge = window.avatarBridge;
      if (bridge && bridge.loadAndPlayVRMA) bridge.loadAndPlayVRMA(data.index);
    }

    if (data.config && data.config.strategy) {
      const stratSel = document.getElementById('cfg-strategy');
      if (stratSel) stratSel.value = data.config.strategy;
      const idx = STRATEGIES.indexOf(data.config.strategy);
      if (idx >= 0) {
        stratIdx = idx;
        document.getElementById('strategy-name').textContent = STRATEGY_LABELS[data.config.strategy] || data.config.strategy;
        document.getElementById('strategy-display').textContent = 'STRATEGY: ' + data.config.strategy.toUpperCase();
      }
    }

    if (data.model) {
      document.getElementById('model-name').textContent = data.model;
    }

    if (data.mode) {
      document.getElementById('mode-select').value = data.mode;
    }

    if (data.config && data.config.personality) {
      const charSel = document.getElementById('cfg-personality');
      if (charSel) charSel.value = data.config.personality;
      const idx = CHARACTERS.indexOf(data.config.personality);
      if (idx >= 0) {
        charIdx = idx;
        document.getElementById('char-label').textContent = CHARACTER_LABELS[data.config.personality];
      }
    }

    if (data.available_games) {
      allGames = data.available_games;
      const consoleSet = [...new Set(allGames.map(g => g.console).filter(Boolean))];
      const newConsoles = ['All', ...consoleSet];
      const consolesChanged = JSON.stringify(newConsoles) !== JSON.stringify(consoles);
      consoles = newConsoles;
      const gamePath = (data.game_path || '').replace(/^\.\//, '');
      if (consolesChanged) {
        consoleIdx = 0;
        if (gamePath) {
          const match = allGames.find(g => g.path === gamePath || g.path === data.game_path);
          if (match && match.console) {
            const ci = consoles.indexOf(match.console);
            if (ci > 0) consoleIdx = ci;
          }
        }
      }
      filterGames();
      const sel = document.getElementById('cfg-game');
      if (gamePath && allGames.some(g => g.path === gamePath)) {
        sel.value = gamePath;
      } else if (data.game_name) {
        const match = allGames.find(g => g.name === data.game_name);
        if (match) sel.value = match.path;
      }
    }

    if (data.status && data.status !== lastStatus) {
      lastStatus = data.status;
      if (data.status === 'running') {
        aiBtn.textContent = 'STOP';
        aiBtn.className = 'ai-btn ai-running';
      } else {
        aiBtn.textContent = 'START';
        aiBtn.className = 'ai-btn ai-idle';
      }
    }

    if (data.config && settingsModal.style.display !== 'flex') {
      const c = data.config;
      document.getElementById('cfg-action-provider').value = c.action_model_provider || 'openrouter';
      document.getElementById('cfg-comm-provider').value = c.commentary_model_provider || 'openrouter';
      document.getElementById('cfg-action-model').value = c.action_model_name || '';
      document.getElementById('cfg-action-model-label').textContent = c.action_model_name || '---';
      document.getElementById('cfg-comm-model').value = c.commentary_model_name || '';
      document.getElementById('cfg-comm-model-label').textContent = c.commentary_model_name || '---';
      const actionCustom = document.getElementById('cfg-action-url-custom');
      const commCustom = document.getElementById('cfg-comm-url-custom');
      const actionBase = c.action_model_base_url || '';
      const commBase = c.commentary_model_base_url || '';
      if (c.action_model_provider === '__custom__' && actionBase) {
        actionCustom.style.display = '';
        actionCustom.value = actionBase;
      } else {
        actionCustom.style.display = 'none';
      }
      if (c.commentary_model_provider === '__custom__' && commBase) {
        commCustom.style.display = '';
        commCustom.value = commBase;
      } else {
        commCustom.style.display = 'none';
      }
      document.getElementById('cfg-action-temp').value = c.action_temperature ?? 0.7;
      document.getElementById('cfg-action-maxtokens').value = c.action_max_tokens ?? 16;
      document.getElementById('cfg-comm-temp').value = c.commentary_temperature ?? 0.9;
      document.getElementById('cfg-comm-maxtokens').value = c.commentary_max_tokens ?? 120;
      document.getElementById('cfg-strategy').value = c.strategy || 'balanced';
      document.getElementById('cfg-personality').value = c.personality || 'energetic';
      document.getElementById('cfg-tts-enabled').checked = c.tts_enabled ?? false;
      document.getElementById('cfg-commentary-enabled').checked = c.commentary_enabled ?? true;
      document.getElementById('cfg-action-enabled').checked = c.action_enabled ?? true;
      document.getElementById('cfg-commentary-context').checked = c.commentary_context ?? false;
      document.getElementById('cfg-action-interval').value = c.min_llm_interval ?? 12;
      document.getElementById('cfg-comm-interval').value = c.min_commentary_interval ?? 30;
      document.getElementById('cfg-retry-base').value = c.retry_rate_base ?? 2;
      document.getElementById('cfg-retry-max').value = c.retry_rate_max ?? 30;
      document.getElementById('cfg-shared-cooldown').checked = c.shared_ai_cooldown ?? false;
      document.getElementById('cfg-screenshot-noise').checked = c.screenshot_noise ?? false;
      const gameSel = document.getElementById('cfg-game');
      if (data.game_path && Array.from(gameSel.options).some(o => o.value === data.game_path)) {
        gameSel.value = data.game_path;
      }
    }

    if (data.costs) {
      const c = data.costs;
      const el = document.getElementById('cost-display');
      el.textContent = `Cost: $${c.total_cost.toFixed(6)}`;
      el.style.color = c.total_cost > 0.50 ? '#ff4444' : (c.total_cost > 0.10 ? '#ffaa00' : '#aaa');
      document.getElementById('cost-rate').textContent = `($${c.hourly_rate.toFixed(2)}/hr)`;
      document.getElementById('cost-model').textContent = c.model;
    }
  };

  ws.onclose = () => {
    document.getElementById('status-dot').className = 'dot idle';
    document.getElementById('status-text').textContent = 'Reconnecting...';
    setTimeout(connectWS, wsReconnectDelay);
    wsReconnectDelay = Math.min(wsReconnectDelay * 1.5, 30000);
  };

  ws.onopen = () => {
    document.getElementById('status-dot').className = 'dot active';
    document.getElementById('status-text').textContent = 'Running';
  };
}

connectWS();

let useAiView = false;
document.getElementById('res-check').addEventListener('change', () => {
  useAiView = document.getElementById('res-check').checked;
  document.getElementById('res-label').textContent = useAiView ? 'AI View' : '1:1';
});

// TTS volume slider
const ttsVolume = document.getElementById('tts-volume');
const ttsVolumeLabel = document.getElementById('tts-volume-label');
ttsVolume.addEventListener('input', () => {
  const vol = parseInt(ttsVolume.value, 10);
  ttsVolumeLabel.textContent = vol + '%';
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'set_volume', volume: vol / 100 }));
  }
});
