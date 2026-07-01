# AgentSmith Architecture

## Overview

AgentSmith is an AI-powered retro game streamer. It uses an LLM to watch emulated gameplay (2048 on Game Boy), decide actions, and provide live commentary like a human streamer. The VTuber overlay shows a 3D VRM avatar that lip-syncs to commentary, a live game screen, stats, and a TTS system.

---

## System Flow

```
VBA Emulator ───screenshot──→ AgentBrain ──action──→ VBA Emulator
                   │              │                      │
                   │              │ commentary            │
                   │              ▼                      │
                   │      CommentaryGenerator ──→ TTS (pyttsx3)
                   │              │
                   │              │ state + commentary
                   │              ▼
                   │      OverlayServer (aiohttp :8765)
                   │              │
                   ▼              ▼
              WebSocket ───→ Browser Overlay (1920x1080)
                                    │
                                    ├─ Game Screen (left)
                                    ├─ VRM Avatar (right) ← lip-sync
                                    ├─ Stats Panel (right)
                                    ├─ Commentary Bar
                                    └─ Bottom Bar
```

---

## Component Breakdown

### 1. Entry Point: `src/main.py`
- Parses `--config` and `--headless` CLI args
- Loads config JSON (e.g. `configs/default.json`)
- Assembles all subsystems:
  - **GameAdapter** (VBA emulator wrapper)
  - **TTSController** (optional pyttsx3 speech)
  - **CommentaryGenerator** (text cleaning + personality)
  - **OverlayServer** (aiohttp on port 8765)
  - **LLMClient** x2 (one for actions, one for commentary)
- Starts the `AgentBrain.run()` loop
- On exit: closes game, stops overlay, stops TTS

### 2. Game Adapter: `src/game/vba_adapter.py`
- Launches `VisualBoyAdvance.exe` as subprocess with ROM
- Captures screenshots via `mss` (screen capture library)
- Sends keyboard input via `PostMessage` (Win32 API)
- Reads emulated RAM via `ReadProcessMemory`
- Action names: `a`, `b`, `up`, `down`, `left`, `right`, `start`, `select`
- Returns `GameState(screenshot, ram, done, reward)`

### 3. Agent Brain: `src/agent/brain.py`
- **The core loop**: for each frame:
  1. Check if action LLM cooldown (10s) is OK AND TTS is not busy
  2. If yes: build prompt with RAM summary + screenshot (224x224)
  3. Call action LLM to choose a move (up/down/left/right/none)
  4. Execute action on emulator
  5. Every 60 frames: check commentary cooldown (12s)
  6. If yes: call commentary LLM -> clean text -> TTS speak -> store `last_comment`
  7. Every frame: broadcast state over WebSocket to overlay
- Action LLM has **fallback**: if primary (OpenRouter) fails, tries local (gemma-3-27b-it at localhost:5001)
- Cooldowns prevent spam and let TTS finish before next decision
- State sent to overlay: `{frame, reward, done, last_action, strategy, model, episode, memory_size, commentary, screenshot (base64), tts_speaking}`
- `tts_speaking: bool` tells the browser avatar when to keep animating mouth

### 4. LLM Client: `src/agent/llm_client.py`
- Supports OpenAI-compatible and Anthropic APIs
- Configurable provider, model, base_url, temperature
- `choose_action()`: injects available actions into system prompt, returns action name
- `commentate()`: higher temperature (0.9), returns commentary text
- Retry with exponential backoff on rate limit (429) or empty response
- Reads API keys from `.env` file

### 5. Memory: `src/agent/memory.py`
- Circular deque (default max 50 entries)
- Each entry: `{frame, reward, done, action, ram_snapshot}`
- Tracks total_reward, episode_reward, episode_frames, episode_count
- `summarize()`: returns last 5 events as text for LLM context

### 6. Commentary: `src/commentary/generator.py`
- Receives raw LLM commentary text
- Cleans it: strips leading text before first `"`, truncates at 128 words, removes unclosed quotes
- Stores in `self.last_comment` (sent to overlay)
- Passes to TTS if enabled
- Personality styles: `energetic`, `chill`, `sarcastic`, `lore_keeper`, `neuro`

### 7. TTS: `src/commentary/tts.py`
- pyttsx3 (offline TTS engine)
- Runs `say()` in a daemon thread so it doesn't block the game loop
- Thread-safe `_speak_count` counter for `is_speaking` property
- Configurable rate (180) and volume (0.9)
- **Disabled by default** in `configs/default.json` (`tts_enabled: false`)

### 8. Overlay Server: `src/streaming/server.py`
- aiohttp web server on configurable port (default 8765)
- **Routes:**
  - `GET /` — returns the overlay HTML page
  - `GET /ws` — WebSocket endpoint for real-time state
  - `GET /assets/*` — static files (VRM models, etc.)
- `broadcast()`: sends JSON state to all connected WS clients
- Removes dead connections gracefully

### 9. Overlay HTML/JS: `src/streaming/overlay.py`
- Single HTML string served as 1920x1080 OBS browser source
- **Layout (CSS grid):**
  ```
  ┌──────────────────────────────────────────────┐
  │ Game Screen (960px)  │  Stats + VRM Avatar   │
  │                      │  (flex column)          │
  ├──────────────────────────────────────────────┤
  │ Commentary Bar                                │
  ├──────────────────────────────────────────────┤
  │ Bottom Bar: status, model, FPS, VTuber name   │
  └──────────────────────────────────────────────┘
  ```
- **VRM Avatar:** Three.js + @pixiv/three-vrm via CDN importmap
  - 5 models available in `/assets/models/` (Seed-san, Alicia Solid, Avatar Orion, ExampleAvatar A & C)
  - Loads at startup, renders with transparent background + 3-point lighting
  - **Lip-sync:** sine-wave mouth animation when commentary arrives
  - **Blinking:** automatic every ~4 seconds
  - **Idle movement:** eyes look around slowly
  - **TTS-aware:** keeps mouth moving while TTS is speaking
  - Green dot indicator lights up while speaking
- **WebSocket:** receives JSON state, updates game screen, stats, commentary
- **Auto-reconnect:** exponential backoff 1s → 30s on disconnect

---

## Data Flow Per Frame

```
1. Game step (emulator executes action)
2. Capture screenshot + read RAM → GameState
3. Store in GameMemory
4. Every 60 frames + cooldown OK:
   a. Build commentary prompt (RAM + screenshot)
   b. Call commentary LLM
   c. Clean text via CommentaryGenerator.speak()
   d. If TTS enabled: speak in background thread
   e. Store last_comment
5. Broadcast state to overlay:
   {frame, reward, last_action, commentary, tts_speaking, screenshot(b64), ...}
6. Browser receives via WebSocket:
   a. Updates game screen image
   b. Updates stats (frame, reward, action, etc.)
   c. If new commentary: fade-in animation + trigger lip-sync
   d. If tts_speaking=true: keep mouth animated
7. Every 10s (cooldown) + not TTS busy:
   a. Build action prompt
   b. Call action LLM
   c. Execute chosen action
8. Repeat
```

---

## Configuration (`configs/default.json`)

```json
{
  "game": { "adapter": "vba", "rom_path": "roms/2048.gb", "observe_every_n_frames": 60 },
  "agent": { "model": "google/gemma-4-26b-a4b-it:free", "provider": "openrouter", /* ... */ },
  "commentary": { "model": "...", "personality": "energetic", "tts_enabled": false, "min_interval": 12.0 },
  "streaming": { "overlay_enabled": true, "overlay_port": 8765 }
}
```

---

## Dependencies

| Package | Purpose |
|---------|---------|
| aiohttp | Web server + WebSocket |
| Pillow | Image processing |
| numpy | Array ops |
| mss | Screen capture |
| pyttsx3 | TTS (optional) |
| python-dotenv | API key loading |
| requests | HTTP calls to LLM APIs |
| pydantic, pyyaml | Config parsing |

**Browser (CDN):** Three.js r180, @pixiv/three-vrm v3 — no npm/node needed.

---

## Project Layout

```
agentsmith/
├── assets/models/         ← VRM avatar files (*.vrm)
├── configs/               ← JSON configs
├── roms/                  ← Game ROM files
├── src/
│   ├── agent/             ← Brain, LLM client, memory, strategies
│   ├── commentary/        ← Generator, TTS, personalities, mood
│   ├── game/              ← GameAdapter, VBA adapter
│   └── streaming/         ← OverlayServer, overlay HTML
└── tests/
```

---

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| LLM-powered actions | Observes screenshot + RAM, decides move |
| 10s action cooldown | Prevents spamming, lets TTS finish |
| 12s commentary cooldown | Natural pacing, not overwhelming |
| Separate LLM for commentary | Can use cheaper/faster model |
| Fallback LLM for actions | If OpenRouter fails, falls back to local |
| Commentary blocking actions | Don't decide moves while talking |
| VRM for VTuber avatar | Fully open-source (MIT), no proprietary licenses |
| CDN for Three.js/VRM | Zero build tooling, no Node.js needed |
