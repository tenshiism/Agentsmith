# AgentSmith

AI-powered retro game streamer. AgentSmith watches a game, thinks about what to do, and provides live commentary — just like a human streamer, but powered by LLMs.

## How it works

```
┌──────────────┐   screenshots   ┌──────────────┐   actions    ┌──────────────┐
│  VBA.exe     │◄───────────────│   AgentBrain │─────────────►│  VBA.exe     │
│  (subprocess)│   RAM reads     │   (LLM)      │   input inj. │  (subprocess)│
└──────────────┘                 └──────┬───────┘              └──────────────┘
                                        │ commentary
                                        ▼
                               ┌─────────────────┐
                               │  Commentary Gen │──▶ TTS
                               └────────┬────────┘
                                        │ state
                                        ▼
                               ┌─────────────────┐
                               │  Overlay Server │──▶ Browser / OBS browser source
                               └────────┬────────┘
                                        │ obs-websocket
                                        ▼
                               ┌─────────────────┐
                               │  OBS Portable   │──▶ Twitch/YouTube stream
                               └─────────────────┘
```

## Architecture

```
agentsmith/
├── src/
│   ├── main.py                 # Entry point — wires everything together
│   ├── agent/
│   │   ├── brain.py            # Core loop: observe → think → act → commentate
│   │   ├── llm_client.py       # LLM API wrapper (OpenAI, OpenRouter, local)
│   │   ├── memory.py           # Game-aware memory (short + long term)
│   │   └── strategies.py       # Play-style configs (balanced, gentle)
│   ├── game/
│   │   ├── base.py             # Abstract game adapter
│   │   └── vba_adapter.py      # VisualBoyAdvance subprocess adapter
│   ├── commentary/
│   │   ├── generator.py        # Generates live commentary text
│   │   ├── personalities.py    # 5 streamer persona definitions
│   │   └── tts.py              # Text-to-speech output
│   └── streaming/
│       ├── overlay.py          # HTML overlay with VRM avatar + settings modal
│       └── server.py           # WebSocket server for real-time UI
├── configs/
│   ├── default.json            # Default config (2048 via VBA)
│   ├── pokemon_red.json        # Game-specific config (needs ROM)
│   └── personalities/          # Personality JSON files
├── assets/
│   ├── models/                 # VRM avatar models
│   └── ...
├── roms/
│   ├── 2048.gb                 # Homebrew Game Boy game (Zlib license)
│   ├── geometrix.gbc           # Homebrew GBC game (GPL v3)
│   └── GBA/                    # GBA ROMs + VBA.exe
└── requirements.txt
```

## Quick start

```bash
pip install -r requirements.txt
python main.py -c configs/default.json
```

## Config structure

```json
{
  "game": {
    "name": "2048",
    "adapter": "vba",
    "rom_path": "./roms/2048.gb",
    "observe_every_n_frames": 30
  },
  "agent": {
    "model": "google/gemma-4-26b-a4b-it:free",
    "provider": "openrouter",
    "temperature": 0.7,
    "strategy": "balanced",
    "max_history": 50,
    "fallback": {
      "model": "gemma-3-27b-it",
      "provider": "openai",
      "base_url": "http://localhost:5001/v1"
    }
  },
  "commentary": {
    "model": "google/gemma-4-26b-a4b-it:free",
    "provider": "openrouter",
    "personality": "energetic",
    "tts_enabled": false,
    "min_interval": 12.0
  },
  "streaming": {
    "overlay_enabled": true,
    "overlay_port": 8765
  }
}
```
