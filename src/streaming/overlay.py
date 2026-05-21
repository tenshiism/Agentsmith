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
    position: relative;
    width: 100%;
    height: 100%;
  }

  /* Game screen frame */
  #game-container {
    position: absolute;
    top: 40px;
    left: 40px;
    width: 960px;
    height: 864px;
    border: 3px solid #ff6b35;
    border-radius: 8px;
    overflow: hidden;
    background: #000;
    box-shadow: 0 0 30px rgba(255, 107, 53, 0.3);
  }

  #game-container img {
    width: 100%;
    height: 100%;
    image-rendering: pixelated;
    object-fit: contain;
  }

  /* Info panel on the right */
  #info-panel {
    position: absolute;
    top: 40px;
    left: 1040px;
    width: 840px;
    height: 864px;
    background: rgba(10, 10, 30, 0.85);
    border: 2px solid #ff6b35;
    border-radius: 8px;
    padding: 24px;
    display: flex;
    flex-direction: column;
    gap: 16px;
    backdrop-filter: blur(4px);
  }

  #info-panel h1 {
    font-family: 'Press Start 2P', monospace;
    font-size: 16px;
    color: #ff6b35;
    text-shadow: 0 0 10px rgba(255, 107, 53, 0.5);
  }

  .stat-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 12px;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 4px;
    font-size: 14px;
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
    font-size: 16px;
  }

  .stat-value.positive { color: #4caf50; }
  .stat-value.negative { color: #f44336; }
  .stat-value.neutral  { color: #ffc107; }

  /* Commentary box */
  #commentary {
    margin-top: auto;
    padding: 16px;
    background: rgba(255, 107, 53, 0.1);
    border: 1px solid rgba(255, 107, 53, 0.3);
    border-radius: 6px;
    min-height: 80px;
  }

  #commentary .label {
    font-family: 'Press Start 2P', monospace;
    font-size: 10px;
    color: #ff6b35;
    margin-bottom: 8px;
  }

  #commentary .text {
    font-size: 15px;
    line-height: 1.5;
    color: #e0e0e0;
  }

  /* Bottom bar */
  #bottom-bar {
    position: absolute;
    bottom: 20px;
    left: 40px;
    right: 40px;
    height: 60px;
    background: rgba(10, 10, 30, 0.8);
    border-radius: 6px;
    border: 1px solid #333;
    display: flex;
    align-items: center;
    padding: 0 24px;
    gap: 24px;
  }

  #bottom-bar .segment {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
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
    font-size: 10px;
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
  </div>
  <div id="info-panel">
    <h1>⚡ AGENTSMITH</h1>
    <div class="stat-row">
      <span class="stat-label">Frame</span>
      <span class="stat-value" id="frame-count">0</span>
    </div>
    <div class="stat-row">
      <span class="stat-label">Reward</span>
      <span class="stat-value neutral" id="reward-value">0.00</span>
    </div>
    <div class="stat-row">
      <span class="stat-label">Last Action</span>
      <span class="stat-value" id="last-action">—</span>
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
    <div id="commentary">
      <div class="label">💬 LIVE COMMENTARY</div>
      <div class="text" id="commentary-text">Waiting for the stream to start...</div>
    </div>
  </div>
  <div id="bottom-bar">
    <div class="segment">
      <span class="dot active" id="status-dot"></span>
      <span id="status-text">Running</span>
    </div>
    <div class="segment">
      <span>Model:</span>
      <span id="model-name">qwen/qwen3.6-plus:free</span>
    </div>
    <div class="segment">
      <span>FPS:</span>
      <span id="fps-display">—</span>
    </div>
    <div class="strategy" id="strategy-display">STRATEGY: BALANCED</div>
  </div>
</div>

<script>
  const ws = new WebSocket(`ws://${location.host}/ws`);

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);

    if (data.screenshot) {
      document.getElementById('game-screen').src = 'data:image/png;base64,' + data.screenshot;
    }

    const frameEl = document.getElementById('frame-count');
    if (frameEl) frameEl.textContent = data.frame ?? 0;

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
    if (commentaryEl && data.commentary) {
      commentaryEl.textContent = data.commentary;
      commentaryEl.classList.remove('fade-in');
      void commentaryEl.offsetWidth;
      commentaryEl.classList.add('fade-in');
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
  };

  ws.onclose = () => {
    document.getElementById('status-dot').className = 'dot idle';
    document.getElementById('status-text').textContent = 'Disconnected';
  };
</script>
</body>
</html>
"""


class OverlayRenderer:
    def __init__(self, config: dict):
        self.config = config

    def render_overlay(self) -> str:
        return OVERLAY_HTML
