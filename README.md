# AgentSmith

An AI-powered retro game streamer. AgentSmith watches a game, thinks about what to do, and provides live commentary — just like a human streamer, but powered by LLMs.

## How it works

```
┌───────────┐   frames   ┌───────────┐   actions   ┌───────────┐
│  Game     │──────────▶│   Agent   │────────────▶│  Game     │
│  Emulator │  screens   │   Brain   │  button     │  Emulator │
│  / ROM    │  + RAM     │  (LLM)    │  presses    │  / ROM    │
└───────────┘            └─────┬─────┘             └───────────┘
                               │ commentary
                               ▼
                        ┌──────────────┐
                        │  Commentary  │
                        │  Engine      │──▶ TTS / chat / overlay
                        └──────────────┘
```

**Loop:** Every N frames, the agent observes the game state (screenshot + RAM values), decides on the next move via an LLM, executes it, and narrates the action in real-time.

## Architecture

```
agentsmith/
├── src/
│   ├── main.py                 # Entry point — wires everything together
│   ├── agent/
│   │   ├── brain.py            # Core loop: observe → think → act → commentate
│   │   ├── llm_client.py       # LLM API wrapper (OpenAI, Anthropic, local)
│   │   ├── memory.py           # Game-aware memory (short + long term)
│   │   └── strategies.py       # Play-style configs (aggressive, speedrun, etc.)
│   ├── game/
│   │   ├── base.py             # Abstract game adapter
│   │   ├── gym_adapter.py      # OpenAI Gym Retro adapter
│   │   └── pyboy_adapter.py    # PyBoy (Game Boy) adapter
│   ├── commentary/
│   │   ├── generator.py        # Generates live commentary text
│   │   ├── personalities.py    # Streamer persona definitions
│   │   └── tts.py              # Text-to-speech output
│   └── streaming/
│       ├── overlay.py          # HTML/CSS overlay (PixelForge assets)
│       ├── server.py           # WebSocket server for real-time UI
│       └── obs_integration.py  # OBS browser source helper
├── configs/
│   ├── pokemon_red.json        # Game-specific config
│   └── personalities/          # Personality JSON files
├── assets/                     # PixelForge-generated overlays
└── requirements.txt
```

## Quick start

```bash
pip install -r requirements.txt
python src/main.py --game pokemon_red --personality energetic
```

## Config structure

```json
{
  "game": {
    "name": "Pokémon Red",
    "adapter": "pyboy",
    "rom_path": "./roms/pokemon_red.gb",
    "speed": 1.0,
    "observe_every_n_frames": 30
  },
  "agent": {
    "model": "gpt-4o",
    "temperature": 0.7,
    "strategy": "balanced",
    "max_history": 50
  },
  "commentary": {
    "personality": "energetic",
    "tts_enabled": true,
    "tts_voice": "en-US-1"
  },
  "streaming": {
    "overlay_port": 8765,
    "obs_enabled": true
  }
}
```
