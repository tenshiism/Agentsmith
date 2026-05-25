from pathlib import Path


OVERLAY_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AgentSmith Overlay</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Press+Start+2P&family=Inter:wght@400;600;700&display=swap');

  * { margin: 0; padding: 0; box-sizing: border-box; }

  body {
    background: transparent;
    font-family: 'Inter', sans-serif;
    color: #fff;
    overflow: hidden;
    width: 1920px;
    height: 1080px;
  }

  #overlay {
    display: grid;
    grid-template-columns: 960px 1fr;
    grid-template-rows: 1fr auto auto;
    grid-template-areas:
      "game      right"
      "comment   comment"
      "bottom    bottom";
    width: 100%;
    height: 100%;
    gap: 0;
  }

  /* ---- Game screen ---- */
  #game-container {
    grid-area: game;
    margin: 20px 10px 10px 20px;
    border: 3px solid #ff6b35;
    border-radius: 8px;
    overflow: hidden;
    background: #000;
    box-shadow: 0 0 30px rgba(255, 107, 53, 0.3);
    position: relative;
  }

  #game-container img {
    width: 100%;
    height: 100%;
    image-rendering: pixelated;
    object-fit: contain;
    transform-origin: center center;
  }

  /* ---- Right panel: avatar + info grid ---- */
  #right-panel {
    grid-area: right;
    display: flex;
    flex-direction: column;
    margin: 20px 20px 10px 10px;
    gap: 10px;
    overflow: hidden;
  }

  /* Info panel (stats) */
  #info-panel {
    background: rgba(10, 10, 30, 0.85);
    border: 2px solid #ff6b35;
    border-radius: 8px;
    padding: 16px 20px;
    backdrop-filter: blur(4px);
  }

  #info-panel h1 {
    font-family: 'Press Start 2P', monospace;
    font-size: 14px;
    color: #ff6b35;
    text-shadow: 0 0 10px rgba(255, 107, 53, 0.5);
    margin-bottom: 8px;
  }

  .stat-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 4px;
  }

  .stat-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 4px 10px;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 4px;
    font-size: 12px;
  }

  .stat-label {
    color: #888;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .stat-value {
    color: #fff;
    font-weight: 700;
    font-size: 13px;
  }

  .stat-value.positive { color: #4caf50; }
  .stat-value.negative { color: #f44336; }
  .stat-value.neutral  { color: #ffc107; }

  .mode-row {
    grid-column: 1 / -1;
  }

  .mode-select {
    background: rgba(255, 255, 255, 0.1);
    color: #fff;
    border: 1px solid rgba(255, 107, 53, 0.5);
    border-radius: 4px;
    padding: 2px 8px;
    font-family: 'Inter', sans-serif;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    outline: none;
  }

  .mode-select:focus {
    border-color: #ff6b35;
  }

  .mode-select option {
    background: #1a1a2e;
    color: #fff;
  }

  .ai-btn {
    border: none;
    border-radius: 4px;
    padding: 4px 16px;
    font-family: 'Inter', sans-serif;
    font-size: 12px;
    font-weight: 700;
    cursor: pointer;
    letter-spacing: 1px;
    transition: background 0.2s;
  }

  .ai-btn.ai-idle {
    background: #2e7d32;
    color: #fff;
  }

  .ai-btn.ai-idle:hover {
    background: #388e3c;
  }

  .ai-btn.ai-running {
    background: #c62828;
    color: #fff;
  }

  .ai-btn.ai-running:hover {
    background: #d32f2f;
  }

  /* Avatar container */
  #avatar-container {
    flex: 1;
    position: relative;
    background: rgba(10, 10, 30, 0.6);
    border: 2px solid rgba(255, 107, 53, 0.4);
    border-radius: 8px;
    overflow: hidden;
    min-height: 300px;
  }

  #avatar-container canvas {
    display: block;
    width: 100%;
    height: 100%;
  }

  #avatar-loading {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    color: rgba(255, 255, 255, 0.5);
    font-family: 'Press Start 2P', monospace;
    font-size: 10px;
    text-align: center;
  }

  /* ---- Commentary bar ---- */
  #commentary-bar {
    grid-area: comment;
    margin: 0 20px 0 20px;
    padding: 10px 20px;
    background: rgba(10, 10, 30, 0.85);
    border: 1px solid rgba(255, 107, 53, 0.3);
    border-radius: 6px;
    display: flex;
    align-items: center;
    gap: 12px;
    backdrop-filter: blur(4px);
    min-height: 50px;
  }

  #commentary-bar .label {
    font-family: 'Press Start 2P', monospace;
    font-size: 9px;
    color: #ff6b35;
    white-space: nowrap;
  }

  #commentary-bar .text {
    font-size: 14px;
    line-height: 1.4;
    color: #e0e0e0;
    flex: 1;
  }

  .vtuber-indicator {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .vtuber-indicator.active { background: #4caf50; box-shadow: 0 0 8px #4caf50; }
  .vtuber-indicator.idle   { background: #666; }

  /* ---- Bottom bar ---- */
  #bottom-bar {
    grid-area: bottom;
    margin: 10px 20px 20px 20px;
    height: 50px;
    background: rgba(10, 10, 30, 0.8);
    border-radius: 6px;
    border: 1px solid #333;
    display: flex;
    align-items: center;
    padding: 0 20px;
    gap: 20px;
  }

  #bottom-bar .segment {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 12px;
    color: #aaa;
  }

  #bottom-bar .segment .dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    display: inline-block;
  }

  .dot.active { background: #4caf50; }
  .dot.idle   { background: #ffc107; }

  #bottom-bar .strategy {
    margin-left: auto;
    font-family: 'Press Start 2P', monospace;
    font-size: 9px;
    color: #ff6b35;
  }

  /* Animations */
  .fade-in {
    animation: fadeIn 0.3s ease-in;
  }

  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: translateY(0); }
  }

</style>
</head>
<body>
<div id="overlay">
  <div id="game-container">
    <img id="game-screen" src="" alt="Game screen">
    <div id="res-toggle" style="
      position: absolute; bottom: 6px; left: 6px;
      background: rgba(0,0,0,0.7); border-radius: 4px;
      padding: 2px 8px; font-size: 11px;
      display: flex; align-items: center; gap: 6px;
      cursor: pointer; z-index: 10;
    ">
      <input type="checkbox" id="res-check" style="cursor:pointer;">
      <label for="res-check" id="res-label" style="cursor:pointer;color:#aaa;">AI View</label>
    </div>
  </div>

  <div id="right-panel">
    <div id="info-panel">
      <h1>AGENTSMITH</h1>
      <div class="stat-grid">
        <div class="stat-row">
          <span class="stat-label">Reward</span>
          <span class="stat-value neutral" id="reward-value">0.00</span>
        </div>
        <div class="stat-row">
          <span class="stat-label">Action</span>
          <span class="stat-value" id="last-action">-</span>
        </div>
        <div class="stat-row">
          <span class="stat-label">Strategy</span>
          <span class="stat-value" id="strategy-name">balanced</span>
        </div>
        <div class="stat-row">
          <span class="stat-label">Episode</span>
          <span class="stat-value" id="episode-count">0</span>
        </div>
        <div class="stat-row">
          <span class="stat-label">Memory</span>
          <span class="stat-value" id="memory-count">0</span>
        </div>
        <div class="stat-row mode-row">
          <span class="stat-label">Mode</span>
          <select id="mode-select" class="mode-select">
            <option value="gentle">Gentle</option>
            <option value="balanced">Balanced</option>
            <option value="custom">Custom</option>
          </select>
        </div>
        <div class="stat-row mode-row" style="margin-top:4px;">
          <span class="stat-label">AI</span>
          <button id="ai-toggle" class="ai-btn ai-idle">START</button>
          <button id="ai-stop" class="ai-btn" style="background:#c62828;margin-left:6px;">STOP</button>
          <button id="settings-toggle" class="ai-btn" style="background:#555;margin-left:6px;">SETTINGS</button>
        </div>
      </div>
    </div>

    <!-- Settings Modal -->
    <div id="settings-modal" style="display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.7);z-index:1000;justify-content:center;align-items:center;">
      <div id="settings-dialog" style="background:#1a1a2e;border:2px solid #ff6b35;border-radius:8px;padding:20px;width:500px;min-width:360px;min-height:300px;max-height:90vh;overflow:auto;resize:both;">
        <h2 style="font-family:'Press Start 2P',monospace;font-size:12px;color:#ff6b35;margin-bottom:16px;display:flex;align-items:center;gap:8px;">
          AI SETTINGS
          <span id="settings-expand" style="font-size:10px;color:#ff6b35;cursor:pointer;border:1px solid #ff6b35;border-radius:3px;padding:1px 7px;user-select:none;white-space:nowrap;margin-left:auto;">[+]</span>
        </h2>

        <!-- Action Model -->
        <h3 style="font-size:11px;color:#aaa;margin:12px 0 6px;text-transform:uppercase;">Action Model</h3>
        <label style="font-size:11px;color:#888;">Provider</label>
        <select id="cfg-action-provider" class="mode-select" style="width:100%;margin-bottom:6px;padding:4px 8px;">
          <option value="openrouter">OpenRouter</option>
          <option value="openai">OpenAI</option>
          <option value="kobold">Kobold (Local)</option>
        </select>
        <label style="font-size:11px;color:#888;">Model</label>
        <select id="cfg-action-model" class="mode-select" style="width:100%;margin-bottom:6px;padding:4px 8px;"></select>
        <label style="font-size:11px;color:#888;">Base URL</label>
        <select id="cfg-action-url" class="mode-select" style="width:100%;margin-bottom:4px;padding:4px 8px;">
          <option value="https://openrouter.ai/api/v1">OpenRouter</option>
          <option value="https://api.openai.com/v1">OpenAI</option>
          <option value="http://localhost:5001/v1">Kobold (Local)</option>
          <option value="__custom__">Custom...</option>
        </select>
        <input id="cfg-action-url-custom" class="mode-select" style="width:100%;margin-bottom:6px;padding:4px 8px;display:none;" placeholder="Enter custom base URL...">

        <div style="display:flex;gap:8px;margin-top:4px;">
          <div style="flex:1;">
            <label style="font-size:11px;color:#888;">Temperature</label>
            <input id="cfg-action-temp" class="mode-select" style="width:100%;padding:4px 8px;" type="number" step="0.05" min="0" max="2" value="0.7">
          </div>
          <div style="flex:1;">
            <label style="font-size:11px;color:#888;">Max Tokens</label>
            <input id="cfg-action-maxtokens" class="mode-select" style="width:100%;padding:4px 8px;" type="number" step="1" min="1" max="200" value="10">
          </div>
        </div>

        <!-- Commentary Model -->
        <h3 style="font-size:11px;color:#aaa;margin:12px 0 6px;text-transform:uppercase;">Commentary Model</h3>
        <label style="font-size:11px;color:#888;">Provider</label>
        <select id="cfg-comm-provider" class="mode-select" style="width:100%;margin-bottom:6px;padding:4px 8px;">
          <option value="openrouter">OpenRouter</option>
          <option value="openai">OpenAI</option>
          <option value="kobold">Kobold (Local)</option>
        </select>
        <label style="font-size:11px;color:#888;">Model</label>
        <select id="cfg-comm-model" class="mode-select" style="width:100%;margin-bottom:6px;padding:4px 8px;"></select>
        <label style="font-size:11px;color:#888;">Base URL</label>
        <select id="cfg-comm-url" class="mode-select" style="width:100%;margin-bottom:4px;padding:4px 8px;">
          <option value="https://openrouter.ai/api/v1">OpenRouter</option>
          <option value="https://api.openai.com/v1">OpenAI</option>
          <option value="http://localhost:5001/v1">Kobold (Local)</option>
          <option value="__custom__">Custom...</option>
        </select>
        <input id="cfg-comm-url-custom" class="mode-select" style="width:100%;margin-bottom:6px;padding:4px 8px;display:none;" placeholder="Enter custom base URL...">

        <div style="display:flex;gap:8px;margin-top:4px;">
          <div style="flex:1;">
            <label style="font-size:11px;color:#888;">Temperature</label>
            <input id="cfg-comm-temp" class="mode-select" style="width:100%;padding:4px 8px;" type="number" step="0.05" min="0" max="2" value="0.9">
          </div>
          <div style="flex:1;">
            <label style="font-size:11px;color:#888;">Max Tokens</label>
            <input id="cfg-comm-maxtokens" class="mode-select" style="width:100%;padding:4px 8px;" type="number" step="1" min="1" max="500" value="120">
          </div>
        </div>

        <!-- Game -->
        <h3 style="font-size:11px;color:#aaa;margin:12px 0 6px;text-transform:uppercase;">Game</h3>
        <select id="cfg-game" class="mode-select" style="width:100%;padding:4px 8px;">
          <option value="">-- Select game --</option>
        </select>

        <!-- Behavior -->
        <h3 style="font-size:11px;color:#aaa;margin:12px 0 6px;text-transform:uppercase;">Behavior</h3>
        <div style="display:flex;gap:8px;">
          <div style="flex:1;">
            <label style="font-size:11px;color:#888;">Strategy</label>
            <select id="cfg-strategy" class="mode-select" style="width:100%;padding:4px 8px;">
              <option value="balanced">Balanced</option>
              <option value="aggressive">Aggressive</option>
              <option value="cautious">Cautious</option>
              <option value="explorer">Explorer</option>
            </select>
          </div>
          <div style="flex:1;">
            <label style="font-size:11px;color:#888;">Personality</label>
            <select id="cfg-personality" class="mode-select" style="width:100%;padding:4px 8px;">
              <option value="energetic">Energetic</option>
              <option value="chill">Chill</option>
              <option value="sarcastic">Sarcastic</option>
              <option value="lore_keeper">Lore Keeper</option>
              <option value="neuro">Neuro</option>
            </select>
          </div>
        </div>

        <!-- Toggles -->
        <h3 style="font-size:11px;color:#aaa;margin:12px 0 6px;text-transform:uppercase;">Toggles</h3>
        <div style="display:flex;gap:12px;margin-top:8px;flex-wrap:wrap;">
          <label style="font-size:11px;color:#888;display:flex;align-items:center;gap:4px;">
            <input id="cfg-tts-enabled" type="checkbox"> TTS Enabled
          </label>
          <label style="font-size:11px;color:#888;display:flex;align-items:center;gap:4px;">
            <input id="cfg-commentary-enabled" type="checkbox" checked> Commentary Enabled
          </label>
          <label style="font-size:11px;color:#888;display:flex;align-items:center;gap:4px;">
            <input id="cfg-shared-cooldown" type="checkbox"> Shared Cooldown
          </label>
        </div>

        <!-- Timing -->
        <h3 style="font-size:11px;color:#aaa;margin:12px 0 6px;text-transform:uppercase;">Timing</h3>
        <div style="display:flex;gap:8px;">
          <div style="flex:1;">
            <label style="font-size:11px;color:#888;">Action Interval (s)</label>
            <input id="cfg-action-interval" class="mode-select" style="width:100%;padding:4px 8px;" type="number" step="0.5" value="12.0">
          </div>
          <div style="flex:1;">
            <label style="font-size:11px;color:#888;">Comm Interval (s)</label>
            <input id="cfg-comm-interval" class="mode-select" style="width:100%;padding:4px 8px;" type="number" step="0.5" value="30.0">
          </div>
        </div>
        <div style="display:flex;gap:8px;margin-top:6px;">
          <div style="flex:1;">
            <label style="font-size:11px;color:#888;">Retry Base (s)</label>
            <input id="cfg-retry-base" class="mode-select" style="width:100%;padding:4px 8px;" type="number" step="0.5" value="2.0">
          </div>
          <div style="flex:1;">
            <label style="font-size:11px;color:#888;">Retry Max (s)</label>
            <input id="cfg-retry-max" class="mode-select" style="width:100%;padding:4px 8px;" type="number" step="0.5" value="30.0">
          </div>
        </div>


        <div style="display:flex;gap:8px;margin-top:16px;">
          <button id="settings-save" class="ai-btn" style="background:#2e7d32;flex:1;">SAVE</button>
          <button id="settings-close" class="ai-btn" style="background:#555;flex:1;">CLOSE</button>
        </div>
      </div>
    </div>

    <div id="avatar-container">
      <div id="avatar-loading">LOADING AVATAR...</div>
      <canvas id="avatar-canvas"></canvas>
    </div>
  </div>

  <div id="commentary-bar">
    <span class="vtuber-indicator idle" id="vtuber-indicator"></span>
    <span class="label">LIVE</span>
    <span class="text" id="commentary-text">-</span>
  </div>

  <div id="bottom-bar">
    <div class="segment">
      <span class="dot active" id="status-dot"></span>
      <span id="status-text">Running</span>
    </div>
    <div class="segment">
      <span>Model:</span>
      <span id="model-name">-</span>
    </div>
    <div class="segment">
      <span>FPS:</span>
      <span id="fps-display">-</span>
    </div>
    <div class="segment">
      <span>VTuber:</span>
      <span id="vtuber-name" style="color:#ff6b35;">-</span>
    </div>
    <div class="strategy" id="strategy-display">STRATEGY: -</div>
  </div>
</div>

<div id="cost-bar" style="
  position: fixed; bottom: 0; left: 0; right: 0;
  height: 24px; background: rgba(0,0,0,0.8);
  color: #aaa; font-size: 12px; font-family: monospace;
  display: flex; align-items: center; padding: 0 12px;
  z-index: 1000;
">
  <span id="cost-display">Cost: $0.000000</span>
  <span style="margin-left: 16px;" id="cost-rate">($0.00/hr)</span>
  <span style="margin-left: auto;" id="cost-model"></span>
</div>

<script type="importmap">
{
  "imports": {
    "three": "https://cdn.jsdelivr.net/npm/three@0.180.0/build/three.module.js",
    "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.180.0/examples/jsm/",
    "@pixiv/three-vrm": "https://cdn.jsdelivr.net/npm/@pixiv/three-vrm@3/lib/three-vrm.module.min.js"
  }
}
</script>

<script type="module">
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { VRMLoaderPlugin, VRMUtils, VRMExpressionPresetName } from '@pixiv/three-vrm';

const MODELS = [
  { name: 'Seed-san',          file: '/assets/models/Seed-san.vrm' },
  { name: 'Alicia Solid',      file: '/assets/models/AliciaSolid_vrm-0.51.vrm' },
  { name: 'Avatar Orion',      file: '/assets/models/Avatar_Orion.vrm' },
  { name: 'ExampleAvatar A',   file: '/assets/models/ExampleAvatar_A.vrm' },
  { name: 'ExampleAvatar C',   file: '/assets/models/ExampleAvatar_C.vrm' },
];

let currentModelIdx = 0;
let vrm = null;
let isSpeaking = false;
let speechEndTime = 0;
let clock = new THREE.Clock();
let loadingEl = document.getElementById('avatar-loading');
let canvas = document.getElementById('avatar-canvas');
let container = document.getElementById('avatar-container');

function initScene() {
  const w = container.clientWidth;
  const h = container.clientHeight;
  canvas.width = w * devicePixelRatio;
  canvas.height = h * devicePixelRatio;

  const renderer = new THREE.WebGLRenderer({
    canvas,
    alpha: true,
    antialias: true,
  });
  renderer.setSize(w, h, false);
  renderer.setPixelRatio(devicePixelRatio);
  renderer.setClearColor(0x000000, 0);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;

  const scene = new THREE.Scene();

  const camera = new THREE.PerspectiveCamera(28, w / h, 0.1, 20);
  camera.position.set(0, 1.1, 2.8);
  camera.lookAt(0, 0.9, 0);

  const ambient = new THREE.AmbientLight(0xffffff, 0.6);
  scene.add(ambient);

  const dirLight = new THREE.DirectionalLight(0xffffff, 1.2);
  dirLight.position.set(1.5, 2.0, 1.5);
  scene.add(dirLight);

  const fillLight = new THREE.DirectionalLight(0x8888ff, 0.4);
  fillLight.position.set(-1.0, 0.5, 1.0);
  scene.add(fillLight);

  const rimLight = new THREE.DirectionalLight(0xff8844, 0.3);
  rimLight.position.set(0, 1.5, -2.0);
  scene.add(rimLight);

  return { renderer, scene, camera };
}

let renderer, scene, camera;

function loadVRM(modelIdx) {
  const model = MODELS[modelIdx];
  if (!model) return;

  loadingEl.style.display = 'block';
  loadingEl.textContent = 'LOADING ' + model.name.toUpperCase() + '...';
  document.getElementById('vtuber-name').textContent = model.name;

  if (vrm) {
    scene.remove(vrm.scene);
    VRMUtils.deepDispose(vrm.scene);
    vrm = null;
  }

  const loader = new GLTFLoader();
  loader.crossOrigin = 'anonymous';
  loader.register((parser) => new VRMLoaderPlugin(parser));

  loader.load(
    model.file,
    (gltf) => {
      vrm = gltf.userData.vrm;
      VRMUtils.removeUnnecessaryVertices(gltf.scene);
      VRMUtils.combineSkeletons(gltf.scene);
      VRMUtils.combineMorphs(vrm);

      vrm.scene.traverse((obj) => { obj.frustumCulled = false; });
      scene.add(vrm.scene);

      VRMUtils.rotateVRM0(vrm);

      loadingEl.style.display = 'none';

  if (vrm.lookAt) {
    vrm.lookAt.target.set(0, 1, 0);
  }

  if (!vrm.expressionManager) {
    console.warn('VRM model has no expression manager');
  }

  clock = new THREE.Clock();
    },
    (progress) => {
      const pct = Math.round(100 * progress.loaded / progress.total);
      loadingEl.textContent = 'LOADING ' + model.name.toUpperCase() + '... ' + pct + '%';
    },
    (err) => {
      console.error('VRM load error:', err);
      loadingEl.textContent = 'AVATAR LOAD FAILED';
      loadingEl.style.color = '#f44336';
    }
  );
}

function animate() {
  requestAnimationFrame(animate);

  if (!vrm) {
    if (renderer) renderer.render(scene, camera);
    return;
  }

  const delta = clock.getDelta();
  const elapsed = clock.elapsedTime;

  if (vrm.expressionManager) {
    if (isSpeaking) {
      const mouthValue = 0.3 + 0.5 * Math.abs(Math.sin(elapsed * 10));
      vrm.expressionManager.setValue('aa', mouthValue);
      vrm.expressionManager.setValue('oh', mouthValue * 0.3);
    } else {
      const t = Math.max(0, speechEndTime - elapsed);
      if (t > 0) {
        const mouthValue = t * 0.3;
        vrm.expressionManager.setValue('aa', mouthValue);
        vrm.expressionManager.setValue('oh', mouthValue * 0.2);
      } else {
        vrm.expressionManager.setValue('aa', 0);
        vrm.expressionManager.setValue('oh', 0);
      }
    }

    const blinkCycle = elapsed % 4;
    if (blinkCycle > 3.95) {
      vrm.expressionManager.setValue('blink', (blinkCycle - 3.95) * 20);
    } else if (blinkCycle > 3.8) {
      vrm.expressionManager.setValue('blink', (3.95 - blinkCycle) * 20);
    } else {
      vrm.expressionManager.setValue('blink', 0);
    }

    vrm.expressionManager.update();
  }

  if (vrm.lookAt) {
    vrm.lookAt.target.set(
      Math.sin(elapsed * 0.3) * 0.2,
      0.9 + Math.sin(elapsed * 0.15) * 0.05,
      1.0
    );
  }

  vrm.update(delta);

  renderer.render(scene, camera);
}

function init() {
  const setup = initScene();
  renderer = setup.renderer;
  scene = setup.scene;
  camera = setup.camera;

  loadVRM(currentModelIdx);
  animate();

  window.addEventListener('resize', () => {
    const w = container.clientWidth;
    const h = container.clientHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  });
}

init();

let lastCommentary = '';
let commentaryTimeout = null;
let lastStatus = 'idle';

document.getElementById('mode-select').addEventListener('change', (e) => {
  const mode = e.target.value;
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'set_mode', mode }));
  }
});

const aiBtn = document.getElementById('ai-toggle');
aiBtn.addEventListener('click', () => {
  const newStatus = lastStatus === 'running' ? 'idle' : 'running';
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'set_status', status: newStatus }));
  }
});

// --- Provider/model/URL mappings ---
const MODEL_MAP = {
  "openrouter": [
    "google/gemma-4-26b-a4b-it:free",
    "google/gemma-4-31b-it:free",
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
    "nvidia/nemotron-nano-12b-v2-vl:free",
    "openrouter/free",
    "google/gemma-3-4b-it",
    "google/gemma-3-12b-it",
    "qwen/qwen3.5-9b",
    "openai/gpt-5-nano",
    "qwen/qwen3.5-flash-02-23",
    "google/gemini-2.0-flash-001",
    "google/gemini-2.0-flash-lite-001",
    "google/gemini-2.5-flash-001",
  ],
  "openai": ["gpt-4o", "gpt-4o-mini", "gpt-4.1", "gpt-4.1-nano"],
  "kobold": [""],
};
const BASE_URL_MAP = {
  "openrouter": "https://openrouter.ai/api/v1",
  "openai": "https://api.openai.com/v1",
  "kobold": "http://localhost:5001/v1",
};

const MODEL_PRICING = {
  "google/gemma-4-26b-a4b-it:free":             { prompt: 0, completion: 0, image: 0 },
  "google/gemma-4-31b-it:free":                  { prompt: 0, completion: 0, image: 0 },
  "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free": { prompt: 0, completion: 0, image: 0 },
  "nvidia/nemotron-nano-12b-v2-vl:free":         { prompt: 0, completion: 0, image: 0 },
  "openrouter/free":                              { prompt: 0, completion: 0, image: 0 },
  "google/gemma-3-4b-it":                        { prompt: 4e-8, completion: 8e-8, image: 3.4e-6 },
  "google/gemma-3-12b-it":                       { prompt: 4e-8, completion: 1.3e-7, image: 3.4e-6 },
  "qwen/qwen3.5-9b":                             { prompt: 4e-8, completion: 1.5e-7, image: 3.4e-6 },
  "openai/gpt-5-nano":                           { prompt: 5e-8, completion: 4e-7, image: 4.25e-6 },
  "qwen/qwen3.5-flash-02-23":                    { prompt: 6.5e-8, completion: 2.6e-7, image: 5.5e-6 },
  "google/gemini-2.0-flash-001":                 { prompt: 1e-7, completion: 4e-7, image: 8.5e-6 },
  "google/gemini-2.0-flash-lite-001":            { prompt: 7.5e-8, completion: 3e-7, image: 6.4e-6 },
  "google/gemini-2.5-flash-001":                 { prompt: 1.5e-7, completion: 6e-7, image: 1.28e-5 },
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

function populateModels(providerId, modelId) {
  const provider = document.getElementById(providerId).value;
  const modelSelect = document.getElementById(modelId);
  const models = MODEL_MAP[provider] || [""];
  modelSelect.innerHTML = models.map(m => {
    if (m === "") return '<option value="">---</option>';
    const p = MODEL_PRICING[m];
    let suffix = '';
    if (p) {
      if (p.prompt === 0 && p.completion === 0) {
        suffix = '  (free)';
      } else {
        suffix = `  (${priceLabel(p.prompt)} in, ${priceLabel(p.completion)} out`;
        if (p.image && p.image > 0) {
          suffix += ` +${priceSingle(p.image)} img)`;
        } else {
          suffix += ')';
        }
      }
    }
    return `<option value="${m}">${m}${suffix}</option>`;
  }).join('');
}

function syncBaseUrl(providerId, urlId, customId) {
  const provider = document.getElementById(providerId).value;
  const urlSelect = document.getElementById(urlId);
  const customInput = document.getElementById(customId);
  urlSelect.value = BASE_URL_MAP[provider] || "";
  customInput.style.display = 'none';
  customInput.value = '';
}

function setupProviderGroup(providerId, modelId, urlId, customId) {
  const provEl = document.getElementById(providerId);
  provEl.addEventListener('change', () => {
    populateModels(providerId, modelId);
    syncBaseUrl(providerId, urlId, customId);
  });
  const urlEl = document.getElementById(urlId);
  urlEl.addEventListener('change', () => {
    const customInput = document.getElementById(customId);
    if (urlEl.value === '__custom__') {
      customInput.style.display = '';
      customInput.value = '';
    } else {
      customInput.style.display = 'none';
      customInput.value = '';
    }
  });
  populateModels(providerId, modelId);
  syncBaseUrl(providerId, urlId, customId);
}

setupProviderGroup('cfg-action-provider', 'cfg-action-model', 'cfg-action-url', 'cfg-action-url-custom');
setupProviderGroup('cfg-comm-provider', 'cfg-comm-model', 'cfg-comm-url', 'cfg-comm-url-custom');

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
settingsModal.addEventListener('click', (e) => {
  if (e.target === settingsModal) settingsModal.style.display = 'none';
});
document.getElementById('settings-save').addEventListener('click', () => {
  function readUrl(providerId, urlId, customId) {
    const urlSelect = document.getElementById(urlId);
    const customInput = document.getElementById(customId);
    if (urlSelect.value === '__custom__') return customInput.value || '';
    return urlSelect.value;
  }
  const config = {
    min_llm_interval: parseFloat(document.getElementById('cfg-action-interval').value) || 12,
    min_commentary_interval: parseFloat(document.getElementById('cfg-comm-interval').value) || 30,
    shared_ai_cooldown: document.getElementById('cfg-shared-cooldown').checked,
    retry_rate_base: parseFloat(document.getElementById('cfg-retry-base').value) || 2,
    retry_rate_max: parseFloat(document.getElementById('cfg-retry-max').value) || 30,
    action_model_provider: document.getElementById('cfg-action-provider').value || 'openrouter',
    action_model_name: document.getElementById('cfg-action-model').value || '',
    action_model_base_url: readUrl('cfg-action-provider', 'cfg-action-url', 'cfg-action-url-custom'),
    action_temperature: parseFloat(document.getElementById('cfg-action-temp').value) || 0.7,
    action_max_tokens: parseInt(document.getElementById('cfg-action-maxtokens').value) || 10,
    commentary_model_provider: document.getElementById('cfg-comm-provider').value || 'openrouter',
    commentary_model_name: document.getElementById('cfg-comm-model').value || '',
    commentary_model_base_url: readUrl('cfg-comm-provider', 'cfg-comm-url', 'cfg-comm-url-custom'),
    commentary_temperature: parseFloat(document.getElementById('cfg-comm-temp').value) || 0.9,
    commentary_max_tokens: parseInt(document.getElementById('cfg-comm-maxtokens').value) || 120,
    strategy: document.getElementById('cfg-strategy').value || 'balanced',
    personality: document.getElementById('cfg-personality').value || 'energetic',
    tts_enabled: document.getElementById('cfg-tts-enabled').checked,
    commentary_enabled: document.getElementById('cfg-commentary-enabled').checked,
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

let ws = null;
let wsReconnectDelay = 1000;

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

    const rewardEl = document.getElementById('reward-value');
    if (rewardEl && data.reward !== undefined) {
      rewardEl.textContent = data.reward.toFixed(2);
      rewardEl.className = 'stat-value ' + (
        data.reward > 0 ? 'positive' : data.reward < 0 ? 'negative' : 'neutral'
      );
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

      isSpeaking = true;
      document.getElementById('vtuber-indicator').className = 'vtuber-indicator active';
      if (commentaryTimeout) clearTimeout(commentaryTimeout);
      commentaryTimeout = setTimeout(() => {
        isSpeaking = false;
        speechEndTime = clock.elapsedTime + 0.5;
        document.getElementById('vtuber-indicator').className = 'vtuber-indicator idle';
      }, Math.max(2000, data.commentary.length * 60));
    }

    if (data.tts_speaking) {
      isSpeaking = true;
      document.getElementById('vtuber-indicator').className = 'vtuber-indicator active';
      if (commentaryTimeout) clearTimeout(commentaryTimeout);
    } else if (isSpeaking && commentaryTimeout === null) {
      isSpeaking = false;
      speechEndTime = clock.elapsedTime + 0.3;
      document.getElementById('vtuber-indicator').className = 'vtuber-indicator idle';
    }

    const episodeEl = document.getElementById('episode-count');
    if (episodeEl && data.episode !== undefined) episodeEl.textContent = data.episode;

    const memoryEl = document.getElementById('memory-count');
    if (memoryEl && data.memory_size !== undefined) memoryEl.textContent = data.memory_size;

    if (data.strategy) {
      const s = document.getElementById('strategy-name');
      const sd = document.getElementById('strategy-display');
      if (s) s.textContent = data.strategy;
      if (sd) sd.textContent = 'STRATEGY: ' + data.strategy.toUpperCase();
    }

    if (data.model) {
      document.getElementById('model-name').textContent = data.model;
    }

    if (data.mode) {
      document.getElementById('mode-select').value = data.mode;
    }

    if (data.available_games) {
      const sel = document.getElementById('cfg-game');
      const current = sel.value;
      sel.innerHTML = '<option value="">-- Select game --</option>' +
        data.available_games.map(g => '<option value="' + g.path + '">' + g.name + '</option>').join('');
      if (data.game_path && data.available_games.some(g => g.path === data.game_path)) {
        sel.value = data.game_path;
      } else if (data.game_name) {
        const match = data.available_games.find(g => g.name === data.game_name);
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
      // Restore provider selects
      document.getElementById('cfg-action-provider').value = c.action_model_provider || 'openrouter';
      document.getElementById('cfg-comm-provider').value = c.commentary_model_provider || 'openrouter';
      // Populate model dropdowns then set value
      populateModels('cfg-action-provider', 'cfg-action-model');
      populateModels('cfg-comm-provider', 'cfg-comm-model');
      const aModel = document.getElementById('cfg-action-model');
      const cModel = document.getElementById('cfg-comm-model');
      const hasOpt = (sel, val) => Array.from(sel.options).some(o => o.value === val);
      if (c.action_model_name && !hasOpt(aModel, c.action_model_name)) {
        const opt = document.createElement('option');
        opt.value = c.action_model_name;
        opt.textContent = c.action_model_name;
        aModel.appendChild(opt);
      }
      aModel.value = c.action_model_name || '';
      if (c.commentary_model_name && !hasOpt(cModel, c.commentary_model_name)) {
        const opt = document.createElement('option');
        opt.value = c.commentary_model_name;
        opt.textContent = c.commentary_model_name;
        cModel.appendChild(opt);
      }
      cModel.value = c.commentary_model_name || '';
      // Restore base URL selects
      const actionUrl = document.getElementById('cfg-action-url');
      const commUrl = document.getElementById('cfg-comm-url');
      const actionCustom = document.getElementById('cfg-action-url-custom');
      const commCustom = document.getElementById('cfg-comm-url-custom');
      const actionBase = c.action_model_base_url || BASE_URL_MAP[c.action_model_provider] || '';
      const commBase = c.commentary_model_base_url || BASE_URL_MAP[c.commentary_model_provider] || '';
      if (actionBase && !hasOpt(actionUrl, actionBase)) {
        actionUrl.value = '__custom__';
        actionCustom.style.display = '';
        actionCustom.value = actionBase;
      } else {
        actionUrl.value = actionBase;
        actionCustom.style.display = 'none';
      }
      if (commBase && !hasOpt(commUrl, commBase)) {
        commUrl.value = '__custom__';
        commCustom.style.display = '';
        commCustom.value = commBase;
      } else {
        commUrl.value = commBase;
        commCustom.style.display = 'none';
      }
      // Remaining fields
      document.getElementById('cfg-action-temp').value = c.action_temperature ?? 0.7;
      document.getElementById('cfg-action-maxtokens').value = c.action_max_tokens ?? 10;
      document.getElementById('cfg-comm-temp').value = c.commentary_temperature ?? 0.9;
      document.getElementById('cfg-comm-maxtokens').value = c.commentary_max_tokens ?? 120;
      document.getElementById('cfg-strategy').value = c.strategy || 'balanced';
      document.getElementById('cfg-personality').value = c.personality || 'energetic';
      document.getElementById('cfg-tts-enabled').checked = c.tts_enabled ?? false;
      document.getElementById('cfg-commentary-enabled').checked = c.commentary_enabled ?? true;
      document.getElementById('cfg-action-interval').value = c.min_llm_interval ?? 12;
      document.getElementById('cfg-comm-interval').value = c.min_commentary_interval ?? 30;
      document.getElementById('cfg-retry-base').value = c.retry_rate_base ?? 2;
      document.getElementById('cfg-retry-max').value = c.retry_rate_max ?? 30;
      document.getElementById('cfg-shared-cooldown').checked = c.shared_ai_cooldown ?? false;
      // Restore game selector
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
</script>
</body>
</html>
"""


class OverlayRenderer:
    def __init__(self, config: dict):
        self.config = config

    def render_overlay(self) -> str:
        return OVERLAY_HTML
