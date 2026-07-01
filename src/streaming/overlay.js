import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { VRMLoaderPlugin, VRMUtils } from '@pixiv/three-vrm';
import { VRMAnimationLoaderPlugin, createVRMAnimationClip } from '@pixiv/three-vrm-animation';

const MODELS = [
  { name: 'Seed-san',          file: '/assets/models/Seed-san.vrm' },
  { name: 'Alicia Solid',      file: '/assets/models/AliciaSolid_vrm-0.51.vrm' },
  { name: 'Avatar Orion',      file: '/assets/models/Avatar_Orion.vrm' },
  { name: 'ExampleAvatar A',   file: '/assets/models/ExampleAvatar_A.vrm' },
  { name: 'ExampleAvatar C',   file: '/assets/models/ExampleAvatar_C.vrm' },
];

const VRMA_FILES = [
  { name: 'Angry',      file: '/assets/vrma/Angry.vrma' },
  { name: 'Blush',      file: '/assets/vrma/Blush.vrma' },
  { name: 'Clapping',   file: '/assets/vrma/Clapping.vrma' },
  { name: 'Goodbye',    file: '/assets/vrma/Goodbye.vrma' },
  { name: 'Jump',       file: '/assets/vrma/Jump.vrma' },
  { name: 'LookAround', file: '/assets/vrma/LookAround.vrma' },
  { name: 'Relax',      file: '/assets/vrma/Relax.vrma' },
  { name: 'Sad',        file: '/assets/vrma/Sad.vrma' },
  { name: 'Sleepy',     file: '/assets/vrma/Sleepy.vrma' },
  { name: 'Surprised',  file: '/assets/vrma/Surprised.vrma' },
  { name: 'Thinking',   file: '/assets/vrma/Thinking.vrma' },
];

let currentModelIdx = 0;
let vrmCenter = new THREE.Vector3(0, 0.9, 0);

// VRMA state
let currentMixer = null;
let currentAction = null;
let vrmaAnimationClip = null;
let currentVrmaIndex = -1;

function createVrmLoader() {
  const l = new GLTFLoader();
  l.crossOrigin = 'anonymous';
  l.register((parser) => new VRMLoaderPlugin(parser));
  l.register((parser) => new VRMAnimationLoaderPlugin(parser));
  return l;
}
let vrm = null;
let clock = new THREE.Clock();
let loadingEl, debugEl, canvas, container;
let renderer, scene, camera;

const CAM_DEFAULTS = { pos: [0, 1.1, 2.8], lookAt: [0, 0.9, 0], fov: 28 };
let camZoom = 1.0;
let camPanX = 0;
let camPanY = 0;
let isDragging = false;
let dragStartX = 0;
let dragStartY = 0;
let dragStartPanX = 0;
let dragStartPanY = 0;

window.avatarBridge = {
  isSpeaking: false,
  speechEndTime: 0,
  clock,
  loadVRM,
  loadAndPlayVRMA,
  stopVRMA,
  resetCamera: resetCamera,
  setMood(mood) {
    if (mood && mood !== lastMood) {
      lastMood = mood;
      moodWeight = 0.8;
    }
  },
  setAudioAmplitude(val) {
    audioAmplitude = val;
  },
  setEyeTracking(enabled, interval) {
    eyeTrackingEnabled = enabled;
    if (interval !== undefined) eyeTrackingInterval = interval;
  },
};

function initScene() {
  loadingEl = document.getElementById('avatar-loading');
  debugEl = document.getElementById('avatar-debug');
  canvas = document.getElementById('avatar-canvas');
  container = document.getElementById('avatar-container');
  if (!container || !canvas) {
    throw new Error('avatar-container or avatar-canvas not found in DOM');
  }
  const w = container.clientWidth;
  const h = container.clientHeight;
  debugEl.textContent = `size: ${w}x${h}`;
  canvas.width = w * devicePixelRatio;
  canvas.height = h * devicePixelRatio;

  renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
  renderer.setSize(w, h, false);
  renderer.setPixelRatio(devicePixelRatio);
  renderer.setClearColor(0x000000, 0);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;

  const gl = renderer.getContext();
  debugEl.textContent = `WebGL: ${gl ? 'ok' : 'FAIL'} ${w}x${h} dpr:${devicePixelRatio}`;

  scene = new THREE.Scene();

  camera = new THREE.PerspectiveCamera(28, w / h, 0.1, 20);
  camera.position.set(0, 1.1, 2.8);
  camera.lookAt(0, 0.9, 0);

  scene.add(new THREE.AmbientLight(0xffffff, 0.6));

  const dirLight = new THREE.DirectionalLight(0xffffff, 1.2);
  dirLight.position.set(1.5, 2.0, 1.5);
  scene.add(dirLight);

  const fillLight = new THREE.DirectionalLight(0x8888ff, 0.4);
  fillLight.position.set(-1.0, 0.5, 1.0);
  scene.add(fillLight);

  const rimLight = new THREE.DirectionalLight(0xff8844, 0.3);
  rimLight.position.set(0, 1.5, -2.0);
  scene.add(rimLight);
}

function applyCamera() {
  if (!camera) return;
  const baseZ = CAM_DEFAULTS.pos[2] / camZoom;
  camera.position.set(
    CAM_DEFAULTS.pos[0] + camPanX,
    CAM_DEFAULTS.pos[1] + camPanY,
    baseZ
  );
  camera.fov = CAM_DEFAULTS.fov;
  camera.updateProjectionMatrix();
  camera.lookAt(
    CAM_DEFAULTS.lookAt[0] + camPanX,
    CAM_DEFAULTS.lookAt[1] + camPanY,
    CAM_DEFAULTS.lookAt[2]
  );
  if (vrm && vrm.lookAt && vrm.lookAt.target) {
    vrm.lookAt.target.set(
      CAM_DEFAULTS.lookAt[0] + camPanX,
      CAM_DEFAULTS.lookAt[1] + camPanY,
      CAM_DEFAULTS.lookAt[2]
    );
  }
}

function resetCamera() {
  camZoom = 1.0;
  camPanX = 0;
  camPanY = 0;
  localStorage.removeItem('avatar-cam-zoom');
  localStorage.removeItem('avatar-cam-pan');
  applyCamera();
  debugEl.textContent = 'camera reset';
}

function saveCameraState() {
  localStorage.setItem('avatar-cam-zoom', camZoom);
  localStorage.setItem('avatar-cam-pan', JSON.stringify([camPanX, camPanY]));
}

function restoreCameraState() {
  const z = localStorage.getItem('avatar-cam-zoom');
  const p = localStorage.getItem('avatar-cam-pan');
  if (z !== null) camZoom = parseFloat(z) || 1.0;
  if (p !== null) {
    try {
      const arr = JSON.parse(p);
      camPanX = arr[0] || 0;
      camPanY = arr[1] || 0;
    } catch(e) {}
  }
}

function setupCameraControls() {
  canvas.addEventListener('wheel', (e) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    camZoom = Math.max(0.3, Math.min(3.0, camZoom * delta));
    applyCamera();
    saveCameraState();
  }, { passive: false });

  canvas.addEventListener('mousedown', (e) => {
    if (e.button !== 0) return;
    isDragging = true;
    dragStartX = e.clientX;
    dragStartY = e.clientY;
    dragStartPanX = camPanX;
    dragStartPanY = camPanY;
    canvas.style.cursor = 'grabbing';
  });

  window.addEventListener('mousemove', (e) => {
    if (!isDragging) return;
    const dx = (e.clientX - dragStartX) * 0.003;
    const dy = -(e.clientY - dragStartY) * 0.003;
    camPanX = dragStartPanX + dx;
    camPanY = dragStartPanY + dy;
    applyCamera();
  });

  window.addEventListener('mouseup', () => {
    if (isDragging) {
      isDragging = false;
      canvas.style.cursor = '';
      saveCameraState();
    }
  });

  canvas.style.cursor = 'grab';

  const resetBtn = document.getElementById('cfg-avatar-reset');
  if (resetBtn) {
    resetBtn.addEventListener('click', resetCamera);
  }

  const eyeCheck = document.getElementById('cfg-eye-tracking');
  const eyeSlider = document.getElementById('cfg-eye-interval');
  if (eyeCheck) {
    const saved = localStorage.getItem('avatar-eye-tracking');
    if (saved !== null) eyeCheck.checked = saved !== 'false';
    eyeTrackingEnabled = eyeCheck.checked;
    eyeCheck.addEventListener('change', () => {
      eyeTrackingEnabled = eyeCheck.checked;
      localStorage.setItem('avatar-eye-tracking', eyeTrackingEnabled);
      const bridge = window.avatarBridge;
      if (bridge) bridge.setEyeTracking(eyeTrackingEnabled);
    });
  }
  if (eyeSlider) {
    const saved = localStorage.getItem('avatar-eye-interval');
    if (saved !== null) eyeSlider.value = saved;
    eyeTrackingInterval = parseFloat(eyeSlider.value) || 2.0;
    eyeSlider.addEventListener('input', () => {
      eyeTrackingInterval = parseFloat(eyeSlider.value) || 2.0;
      localStorage.setItem('avatar-eye-interval', eyeTrackingInterval);
      const bridge = window.avatarBridge;
      if (bridge) bridge.setEyeTracking(eyeTrackingEnabled, eyeTrackingInterval);
    });
  }
}

function loadVRM(modelIdx) {
  const model = MODELS[modelIdx];
  if (!model) { debugEl.textContent = 'no model at idx ' + modelIdx; return; }

  loadingEl.style.display = 'block';
  loadingEl.textContent = 'LOADING ' + model.name.toUpperCase() + '...';
  debugEl.textContent = 'loading ' + model.file;
  document.getElementById('vtuber-name').textContent = model.name;

  if (vrm) {
    scene.remove(vrm.scene);
    VRMUtils.deepDispose(vrm.scene);
    vrm = null;
  }

  const loader = createVrmLoader();

  loader.load(
    model.file,
    (gltf) => {
      vrm = gltf.userData.vrm;
      debugEl.textContent = 'vrm: ' + (vrm ? 'ok' : 'null') + ' scene: ' + !!gltf.scene;
      VRMUtils.removeUnnecessaryVertices(gltf.scene);
      VRMUtils.combineSkeletons(gltf.scene);
      VRMUtils.combineMorphs(vrm);

      vrm.scene.traverse((obj) => { obj.frustumCulled = false; });
      scene.add(vrm.scene);

      VRMUtils.rotateVRM0(vrm);

      const box = new THREE.Box3().setFromObject(vrm.scene);
      const size = box.getSize(new THREE.Vector3());
      const center = box.getCenter(new THREE.Vector3());
      vrmCenter.copy(center);
      debugEl.textContent = `box: ${size.x.toFixed(2)}x${size.y.toFixed(2)}x${size.z.toFixed(2)} center: ${center.x.toFixed(1)},${center.y.toFixed(1)},${center.z.toFixed(1)}`;

      const maxDim = Math.max(size.x, size.y, size.z);
      const fov = camera.fov * (Math.PI / 180);
      let dist = maxDim / (2 * Math.tan(fov / 2));
      dist *= 1.5;
      CAM_DEFAULTS.pos = [center.x, center.y, center.z + dist];
      CAM_DEFAULTS.lookAt = [center.x, center.y, center.z];
      applyCamera();
      camera.near = dist * 0.01;
      camera.far = dist * 10;
      camera.updateProjectionMatrix();

      if (vrm.lookAt && vrm.lookAt.target) {
        vrm.lookAt.target.set(center.x, center.y, center.z);
      }

      loadingEl.style.display = 'none';
      clock = new THREE.Clock();
    },
    (progress) => {
      const pct = Math.round(100 * progress.loaded / progress.total);
      loadingEl.textContent = 'LOADING ' + model.name.toUpperCase() + '... ' + pct + '%';
    },
    (err) => {
      console.error('VRM load error:', err);
      loadingEl.textContent = 'AVATAR LOAD FAILED\n' + (err.message || err);
      loadingEl.style.color = '#f44336';
      loadingEl.style.fontSize = '8px';
      loadingEl.style.whiteSpace = 'pre-wrap';
    }
  );
}

let blinkTimer = 0;
let blinkInterval = 3.5 + Math.random() * 2;
let blinkPhase = 0;
let lastMood = 'neutral';
let moodWeight = 0;
let eyeTrackingEnabled = true;
let eyeTrackingInterval = 2.0;
let lastEyeUpdate = 0;
let eyeTargetX = 0;
let eyeTargetY = 0.9;
let audioAmplitude = 0;
let mouthSmooth = 0;

function animate() {
  requestAnimationFrame(animate);

  if (!vrm) {
    if (renderer) renderer.render(scene, camera);
    return;
  }

  const delta = clock.getDelta();
  const elapsed = clock.elapsedTime;
  const bridge = window.avatarBridge;

  if (vrm.expressionManager) {
    if (bridge.isSpeaking || audioAmplitude > 0.01) {
      const amp = bridge.isSpeaking ? (0.3 + 0.5 * Math.abs(Math.sin(elapsed * 10))) : audioAmplitude;
      const target = Math.min(1.0, amp);
      mouthSmooth += (target - mouthSmooth) * 0.3;
      vrm.expressionManager.setValue('aa', mouthSmooth * 0.9);
      vrm.expressionManager.setValue('oh', mouthSmooth * 0.2);
      vrm.expressionManager.setValue('ih', mouthSmooth * 0.15);
    } else {
      mouthSmooth *= 0.85;
      if (mouthSmooth < 0.01) mouthSmooth = 0;
      vrm.expressionManager.setValue('aa', mouthSmooth);
      vrm.expressionManager.setValue('oh', mouthSmooth * 0.2);
      vrm.expressionManager.setValue('ih', mouthSmooth * 0.15);
    }

    const breathing = Math.sin(elapsed * 2.1) * 0.04 + 0.04;
    vrm.expressionManager.setValue('relaxed', breathing);

    blinkTimer += delta;
    if (blinkPhase === 0 && blinkTimer >= blinkInterval) {
      blinkPhase = 1;
      blinkTimer = 0;
      blinkInterval = 2.5 + Math.random() * 3.5;
    }
    if (blinkPhase === 1) {
      const t = blinkTimer * 8;
      if (t < 1) {
        vrm.expressionManager.setValue('blink', t);
      } else if (t < 2) {
        vrm.expressionManager.setValue('blink', 2 - t);
      } else {
        vrm.expressionManager.setValue('blink', 0);
        blinkPhase = 0;
        blinkTimer = 0;
      }
    } else {
      vrm.expressionManager.setValue('blink', 0);
    }

    if (moodWeight > 0.01) {
      vrm.expressionManager.setValue(lastMood, moodWeight);
      moodWeight *= 0.995;
    }

    vrm.expressionManager.update();
  }

  if (vrm.lookAt && vrm.lookAt.target) {
    if (eyeTrackingEnabled && elapsed - lastEyeUpdate > eyeTrackingInterval) {
      eyeTargetX = (Math.random() - 0.5) * 0.4;
      eyeTargetY = 0.8 + Math.random() * 0.3;
      lastEyeUpdate = elapsed;
    }
    const cur = vrm.lookAt.target;
    cur.x += (eyeTargetX - cur.x) * 0.05;
    cur.y += (eyeTargetY - cur.y) * 0.05;
    cur.z = 1.0;
  }

  const swayX = Math.sin(elapsed * 0.7) * 0.003;
  const swayY = Math.sin(elapsed * 1.1) * 0.002;
  if (camera && CAM_DEFAULTS) {
    const baseZ = CAM_DEFAULTS.pos[2] / camZoom;
    camera.position.x = CAM_DEFAULTS.pos[0] + camPanX + swayX;
    camera.position.y = CAM_DEFAULTS.pos[1] + camPanY + swayY;
    camera.position.z = baseZ;
    camera.lookAt(
      CAM_DEFAULTS.lookAt[0] + camPanX + swayX,
      CAM_DEFAULTS.lookAt[1] + camPanY + swayY,
      CAM_DEFAULTS.lookAt[2]
    );
  }

  if (currentMixer) currentMixer.update(delta);
  vrm.update(delta);
  renderer.render(scene, camera);
}

// --- VRMA Functions ---
async function loadAndPlayVRMA(index) {
  if (index < 0 || index >= VRMA_FILES.length) { stopVRMA(); return; }
  currentVrmaIndex = index;
  stopVRMA();
  const url = VRMA_FILES[index].file;
  const l = createVrmLoader();
  l.load(
    url,
    (gltf) => {
      const animData = gltf.userData.vrmAnimations && gltf.userData.vrmAnimations[0];
      if (animData) {
        const clip = createVRMAnimationClip(animData, vrm);
        if (clip) { vrmaAnimationClip = clip; playVRMA(); }
      }
    },
    undefined,
    (err) => console.error('VRMA load error:', err)
  );
}

function playVRMA() {
  if (!vrm || !vrmaAnimationClip) return;
  if (!currentMixer) currentMixer = new THREE.AnimationMixer(vrm.scene);
  if (currentAction) currentAction.stop();
  currentAction = currentMixer.clipAction(vrmaAnimationClip);
  currentAction.setLoop(THREE.LoopOnce);
  currentAction.clampWhenFinished = true;
  currentAction.reset();
  currentAction.play();
}

function stopVRMA() {
  if (currentAction) { currentAction.stop(); currentAction = null; }
  if (currentMixer) currentMixer.stopAllAction();
  if (vrm && vrm.humanoid) vrm.humanoid.resetPose();
  vrmaAnimationClip = null;
  currentVrmaIndex = -1;
}

function init() {
  initScene();
  restoreCameraState();
  setupCameraControls();

  const vrmSel = document.getElementById('cfg-vtuber-model');
  MODELS.forEach((m, i) => {
    const opt = document.createElement('option');
    opt.value = i;
    opt.textContent = m.name;
    vrmSel.appendChild(opt);
  });
  const savedModel = localStorage.getItem('vtuber-model-idx');
  if (savedModel !== null) {
    currentModelIdx = parseInt(savedModel, 10) || 0;
  }
  vrmSel.value = currentModelIdx;
  vrmSel.addEventListener('change', () => {
    currentModelIdx = parseInt(vrmSel.value, 10) || 0;
    localStorage.setItem('vtuber-model-idx', currentModelIdx);
    loadVRM(currentModelIdx);
  });

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

try {
  init();
  window._avatarLoaded = true;
} catch(err) {
  console.error('Avatar init failed:', err);
  window._avatarError = err.message;
  const el = document.getElementById('avatar-loading');
  if (el) {
    el.textContent = 'AVATAR ERROR: ' + err.message;
    el.style.color = '#f44336';
    el.style.display = 'block';
    el.style.fontSize = '8px';
    el.style.wordBreak = 'break-word';
    el.style.padding = '10px';
  }
}
