# Prices are per-token in USD. Image price = estimated cost for a 224x224 image
# (~85 tokens at the prompt rate). Keyed by exact model ID as used in config.
MODEL_PRICING = {
    "google/gemma-4-26b-a4b-it:free":             {"prompt": 0, "completion": 0, "image": 0},
    "google/gemma-4-31b-it:free":                  {"prompt": 0, "completion": 0, "image": 0},
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free": {"prompt": 0, "completion": 0, "image": 0},
    "nvidia/nemotron-nano-12b-v2-vl:free":         {"prompt": 0, "completion": 0, "image": 0},
    "openrouter/free":                              {"prompt": 0, "completion": 0, "image": 0},
    "google/gemma-3-4b-it":                        {"prompt": 4e-8, "completion": 8e-8, "image": 3.4e-6},
    "google/gemma-3-12b-it":                       {"prompt": 4e-8, "completion": 1.3e-7, "image": 3.4e-6},
    "qwen/qwen3.5-9b":                             {"prompt": 4e-8, "completion": 1.5e-7, "image": 3.4e-6},
    "openai/gpt-5-nano":                           {"prompt": 5e-8, "completion": 4e-7, "image": 4.25e-6},
    "openai/gpt-4o":                               {"prompt": 2.5e-6, "completion": 1e-5, "image": 2.13e-4},
    "openai/gpt-4o-mini":                          {"prompt": 1.5e-7, "completion": 6e-7, "image": 1.28e-5},
    "openai/gpt-4.1":                              {"prompt": 2e-6, "completion": 8e-6, "image": 1.7e-4},
    "openai/gpt-4.1-nano":                         {"prompt": 1e-7, "completion": 4e-7, "image": 8.5e-6},
    "qwen/qwen3.5-flash-02-23":                    {"prompt": 6.5e-8, "completion": 2.6e-7, "image": 5.5e-6},
    "google/gemini-2.0-flash-001":                 {"prompt": 1e-7, "completion": 4e-7, "image": 8.5e-6},
    "google/gemini-2.0-flash-lite-001":            {"prompt": 7.5e-8, "completion": 3e-7, "image": 6.4e-6},
    "google/gemini-2.5-flash-001":                 {"prompt": 1.5e-7, "completion": 6e-7, "image": 1.28e-5},
}
