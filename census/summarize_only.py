#!/usr/bin/env python3
"""Aggregate streamed observations through the project's own reporting.summarize."""
import json, sys
from collections import Counter
from pathlib import Path
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "src"))
from awkeys.reporting import summarize  # noqa: E402

obs = [json.loads(l) for l in Path(sys.argv[1]).read_text().splitlines() if l.strip()]
status = [json.loads(l) for l in Path(sys.argv[2]).read_text().splitlines() if l.strip()]
manifest = {
    "started_at": None, "finished_at": None, "request_count": None,
    "collection_mode": "public_clone_snapshot_handcurated_index_sample",
    "discovered_repository_count": len(status),
    "repository_budget_truncated": True,
    "search_returned_pages_complete": False,
    "snapshot_analysis_complete": False,
    "index_population_exhaustive": False,
    "repositories": [{"status": s["status"]} for s in status],
    "errors": [s for s in status if s["status"] not in ("analyzed",)],
}
summary = summarize(obs, manifest)
Path(sys.argv[3]).write_text(json.dumps(summary, indent=2))
a = summary["all"]
print("repos with >=1 agent job:", a["repositories_with_agent_jobs"], "/ attempted", len(status))
print("agent jobs:", a["agent_jobs"])
print("triple-indicator jobs:", a["triple_indicator_jobs"])
print("repos with triple-indicator:", a["repositories_with_triple_indicator"])
print("non-model secret jobs:", a["referenced_non_model_secret_jobs"])
print("model secret jobs:", a["referenced_model_secret_jobs"])
print("self-hosted jobs:", a["self_hosted_label_jobs"])
print("inherited/unknown token jobs:", a["inherited_or_unknown_token_jobs"])
print("unpinned direct remote action uses:", a["unpinned_direct_remote_action_uses"])
print("A input:", a["a_input_indicator"])
print("B sensitive:", a["b_sensitive_indicator"])
print("C declared write:", a["c_declared_repository_write"])
print("secret categories:", a["secret_categories_jobs"])
print("agents:", a["agents_jobs"])
print("engine subsets: game jobs =", summary["game_markers_present"]["agent_jobs"],
      "| no-marker(complete tree) =", summary["no_engine_marker_complete_tree"]["agent_jobs"],
      "| unknown =", summary["engine_classification_unknown"]["agent_jobs"])
