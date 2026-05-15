STRATEGIES = {
    "balanced": {
        "system_prompt": (
            "You are a skilled retro game player. Analyze the screen and RAM values "
            "to decide the best action. Prioritize survival and progress."
        ),
        "temperature": 0.7,
    },
    "aggressive": {
        "system_prompt": (
            "You are a speedrunner. Move fast, take risks, optimize for completion time. "
            "Never idle — always press something useful."
        ),
        "temperature": 0.9,
    },
    "cautious": {
        "system_prompt": (
            "You are a careful, methodical player. Prioritize not taking damage. "
            "Observe before acting. Prefer safe movements."
        ),
        "temperature": 0.3,
    },
    "explorer": {
        "system_prompt": (
            "You are a curious explorer. You want to see every corner of the game. "
            "Try unusual paths, interact with everything, prioritize discovery over speed."
        ),
        "temperature": 0.85,
    },
}


def load_strategy(name: str) -> dict:
    strategy = STRATEGIES.get(name)
    if not strategy:
        raise ValueError(f"Unknown strategy '{name}'. Available: {list(STRATEGIES)}")
    return strategy
