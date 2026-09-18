#!/usr/bin/env python3
"""
Same measured result as scripts/run_isolated_vs_pooled.py, but the
detect -> share -> re-check cycle is orchestrated by a real strands.Agent
deciding to call tools, backed by a local Ollama model — not a Python
`for` loop. See orchestration/strands_agent.py's module docstring for
exactly what that does and doesn't change.

One-time setup (this environment had none of this installed or running
until now):

    py -3 -m pip install strands-agents strands-agents-tools ollama
    winget install --id Ollama.Ollama -e   # or https://ollama.com/download
    ollama pull qwen2.5:1.5b               # ~1 GB, one time, fully offline after

Note on model choice: llama3.2:1b was tried first and could not be made to
reliably emit real tool calls through Ollama's function-calling path -- it
would print tool-call-shaped JSON as plain text instead, which Strands has
no way to execute. qwen2.5:1.5b, which has explicit tool-use training, does
this correctly and is what DEFAULT_MODEL_ID actually points at.

Run from the tripwire/ directory:

    py -3 scripts/run_strands_swarm.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

sys.path.insert(0, str(Path(__file__).parents[1]))

from detection.dataset import SITE_CONFIGS
from orchestration.strands_agent import DEFAULT_MODEL_ID, run_swarm_cycle_via_strands
from policy.gate import PolicyGate
from shared_store.store import LocalPatternStore

LOW_DATA_SITE = "site_c_low_data"


def _header(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def main() -> int:
    root = Path(__file__).parents[1]
    gate = PolicyGate(log_file=root / "policy" / "logs" / "decisions.jsonl")
    store = LocalPatternStore(root / "shared_store" / "pool_strands.jsonl")
    store.clear()

    _header("TRIPWIRE — swarm cycle orchestrated by a real Strands agent")
    print(f"model: {DEFAULT_MODEL_ID} via Ollama (local, offline, no API key)")
    print(f"sites: {', '.join(c.site_id for c in SITE_CONFIGS)}")
    print()
    print("Asking the agent to run detect -> share -> re-check for every site...")
    print("(first call includes Ollama loading the model into memory — slower than the rest)")

    started = time.time()
    result = run_swarm_cycle_via_strands(gate, store, SITE_CONFIGS)
    elapsed = time.time() - started

    _header("Agent's closing summary (its own words, not the proof — see numbers below)")
    print(result.transcript)

    cycle = result.cycle
    _header("STEP 1 — isolated baseline (unchanged, same detector as always)")
    for site_id in [c.site_id for c in SITE_CONFIGS]:
        print("  " + cycle.isolated_metrics[site_id].summary_line(site_id))

    _header("STEP 2 — after the Strands-orchestrated share + re-check round")
    for site_id in [c.site_id for c in SITE_CONFIGS]:
        before = cycle.isolated_metrics[site_id].detection_rate
        after = cycle.pooled_metrics[site_id].detection_rate
        marker = "  <-- the low-data site" if site_id == LOW_DATA_SITE else ""
        print(f"  {site_id}: {before:.1%} -> {after:.1%}{marker}")

    print(f"\n  shared pool holds {cycle.pool_size} signatures")
    print(f"  wall-clock time for the whole agent-orchestrated cycle: {elapsed:.1f}s")
    print()
    print("  This number matches run_isolated_vs_pooled.py's because the underlying")
    print("  detection, policy and pooling code is identical either way — only the")
    print("  orchestration changed, from a fixed loop to a real Strands agent's")
    print("  own tool-calling decisions.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
