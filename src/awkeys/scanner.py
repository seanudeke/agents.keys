"""Read YAML only. Never execute, import or install code from scanned repositories."""
from __future__ import annotations

import copy
import json
import re
from importlib.resources import files
from pathlib import PurePosixPath
from typing import Any

import yaml

from .io import sha256

MAX_BYTES = 1_048_576
MAX_EVENTS = 30_000
MAX_ALIASES = 100
UNTRUSTED_EVENTS = {
    "issues", "issue_comment", "pull_request", "pull_request_target",
    "pull_request_review", "pull_request_review_comment", "discussion", "discussion_comment",
}
EVENT_TEXT = re.compile(
    r"github\.event\.(?:(?:issue|comment|discussion|review)\.(?:body|title)|"
    r"pull_request\.(?:body|title)|head_commit\.message|commits\b)"
)
SECRET = re.compile(r"secrets\s*(?:\.\s*([A-Za-z_][A-Za-z0-9_]*)|\[\s*['\"]([^'\"]+)['\"]\s*\])")
SHA = re.compile(r"^[0-9a-fA-F]{40}$")


class WorkflowError(ValueError):
    pass


class WorkflowLoader(yaml.SafeLoader):
    """YAML 1.2 booleans so GitHub's 'on' key remains a string."""


WorkflowLoader.yaml_implicit_resolvers = copy.deepcopy(yaml.SafeLoader.yaml_implicit_resolvers)
for key, resolvers in WorkflowLoader.yaml_implicit_resolvers.items():
    WorkflowLoader.yaml_implicit_resolvers[key] = [
        (tag, pattern) for tag, pattern in resolvers if tag != "tag:yaml.org,2002:bool"
    ]
WorkflowLoader.add_implicit_resolver("tag:yaml.org,2002:bool", re.compile(r"^(?:true|false)$", re.I), list("tTfF"))


def _mapping(loader: WorkflowLoader, node: yaml.MappingNode, deep: bool = False) -> dict:
    loader.flatten_mapping(node)
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            duplicate = key in result
        except TypeError as exc:
            raise WorkflowError("non-scalar mapping key") from exc
        if duplicate:
            raise WorkflowError("duplicate or conflicting merged YAML key")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


WorkflowLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)


def _check_graph(value: Any, stack: set[int] | None = None, depth: int = 0,
                 visited: set[int] | None = None) -> None:
    if depth > 80:
        raise WorkflowError("YAML nesting exceeds the analysis limit")
    if not isinstance(value, (dict, list)):
        return
    stack = stack if stack is not None else set()
    visited = visited if visited is not None else set()
    if id(value) in stack:
        raise WorkflowError("recursive YAML alias")
    if id(value) in visited:
        return
    stack.add(id(value))
    children = value.values() if isinstance(value, dict) else value
    for child in children:
        _check_graph(child, stack, depth + 1, visited)
    stack.remove(id(value))
    visited.add(id(value))


def load_workflow(text: str) -> dict:
    if len(text.encode("utf-8")) > MAX_BYTES:
        raise WorkflowError("workflow exceeds the byte limit")
    try:
        aliases = 0
        for count, event in enumerate(yaml.parse(text, Loader=WorkflowLoader), 1):
            aliases += isinstance(event, yaml.events.AliasEvent)
            if count > MAX_EVENTS or aliases > MAX_ALIASES:
                raise WorkflowError("YAML complexity exceeds the analysis limit")
        data = yaml.load(text, Loader=WorkflowLoader)
        if not isinstance(data, dict):
            raise WorkflowError("workflow root must be a mapping")
        _check_graph(data)
        if not isinstance(data.get("jobs"), dict):
            raise WorkflowError("workflow has no jobs mapping")
        return data
    except (yaml.YAMLError, RecursionError) as exc:
        # Parser messages may contain original lines, including embedded secret literals.
        raise WorkflowError("invalid or unsupported YAML") from exc


def load_catalog(path=None) -> dict:
    text = path.read_text(encoding="utf-8") if path else files("awkeys").joinpath("catalog.json").read_text(encoding="utf-8")
    catalog = json.loads(text)
    if catalog.get("schema_version") != 1 or not isinstance(catalog.get("actions"), list):
        raise ValueError("unsupported catalog")
    for entry in catalog.get("cli_patterns", []):
        re.compile(entry["pattern"])
    return catalog


def strings(value: Any, visited: set[int] | None = None):
    visited = visited if visited is not None else set()
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        if id(value) in visited:
            return
        visited.add(id(value))
        for child in value.values():
            yield from strings(child, visited)
    elif isinstance(value, list):
        if id(value) in visited:
            return
        visited.add(id(value))
        for child in value:
            yield from strings(child, visited)


def triggers(data: dict) -> list[str]:
    on = data.get("on")
    if isinstance(on, str):
        return [on]
    if isinstance(on, list):
        return sorted(str(x) for x in on)
    if isinstance(on, dict):
        return sorted(str(x) for x in on)
    return []


def agent_matches(step: dict, catalog: dict) -> list[str]:
    uses = str(step.get("uses", "")).lower().split("@", 1)[0]
    found = {x["id"] for x in catalog["actions"] if uses == x["uses"].lower()}
    # Ignore full-line shell comments and step labels. CLI matching remains heuristic.
    command = "\n".join(line for line in str(step.get("run", "")).splitlines() if not line.lstrip().startswith("#"))
    for entry in catalog.get("cli_patterns", []):
        if re.search(entry["pattern"], command):
            found.add(entry["id"])
    return sorted(found)


def permissions(data: dict, job: dict) -> dict:
    value = job["permissions"] if "permissions" in job else data.get("permissions")
    source = "job" if "permissions" in job else "workflow" if "permissions" in data else "inherited"
    if value is None:
        return {"source": source, "mode": "unknown", "write_scopes": [], "declared_write": "unknown", "oidc": "unknown"}
    if value == "write-all":
        return {"source": source, "mode": value, "write_scopes": ["*"], "declared_write": "present", "oidc": "present"}
    if value == "read-all":
        return {"source": source, "mode": value, "write_scopes": [], "declared_write": "absent", "oidc": "absent"}
    if (isinstance(value, dict) and all(v in ("read", "write", "none") for v in value.values())
            and value.get("id-token") != "read"):
        scopes = sorted(str(k) for k, v in value.items() if v == "write")
        writes = [x for x in scopes if x != "id-token"]
        return {"source": source, "mode": "explicit", "write_scopes": scopes,
                "declared_write": "present" if writes else "absent",
                "oidc": "present" if "id-token" in scopes else "absent"}
    return {"source": source, "mode": "dynamic_or_invalid", "write_scopes": [], "declared_write": "unknown", "oidc": "unknown"}


def secret_category(name: str) -> str:
    n = name.upper()
    groups = [
        ("model", r"OPENAI|ANTHROPIC|CLAUDE|GEMINI|GOOGLE_AI|AZURE_OPENAI|LLM"),
        ("android_signing", r"KEYSTORE|ANDROID.*(?:KEY|SIGN)|SIGNING_KEY"),
        ("apple_signing", r"P12|MATCH_PASSWORD|APPLE.*CERT|IOS.*CERT|MACOS.*CERT"),
        ("store_publishing", r"APP_STORE|APPSTORE|PLAY_STORE|PLAYSTORE|STEAM|FASTLANE|ITUNES|ASC_"),
        ("cloud", r"AWS_|AZURE_|GOOGLE_CLOUD|GCP_|SERVICE_ACCOUNT"),
        ("engine_license", r"UNITY_|UNREAL_|UE_LICENSE"),
        ("registry_or_repository", r"GITHUB|GH_TOKEN|GH_PAT|NPM_|PYPI|DOCKER|REGISTRY|ARTIFACTORY|PAT"),
    ]
    for category, pattern in groups:
        if re.search(pattern, n):
            return category
    return "other_or_ambiguous"


def secret_refs(value: Any) -> dict:
    names = set()
    dynamic = False
    for s in strings(value):
        names.update(a or b for a, b in SECRET.findall(s))
        cleaned = SECRET.sub("", s)
        if re.search(r"\bsecrets\b", cleaned) and ("${{" in cleaned or s == "inherit"):
            dynamic = True
    return {"names": sorted(names), "categories": sorted({secret_category(x) for x in names}),
            "dynamic": dynamic}


def action_refs(steps: list[dict]) -> list[dict]:
    result = []
    for index, step in enumerate(steps):
        ref = step.get("uses")
        if not isinstance(ref, str):
            continue
        if ref.startswith("./"):
            kind, pinned = "local", None
        elif ref.startswith("docker://"):
            kind, pinned = "container", bool(re.search(r"@sha256:[0-9a-fA-F]{64}$", ref))
        elif "${{" in ref:
            kind, pinned = "dynamic", None
        else:
            kind, pinned = "remote", bool(SHA.fullmatch(ref.rsplit("@", 1)[-1])) if "@" in ref else False
        # No original run/prompt/environment content is included in scanner output.
        result.append({"step_index": index, "kind": kind, "pinned": pinned})
    return result


def runner_type(value: Any) -> str:
    labels = [value] if isinstance(value, str) else value if isinstance(value, list) else []
    if any(isinstance(x, str) and x.lower() == "self-hosted" for x in labels):
        return "self_hosted_lifecycle_unknown"
    if labels and all(isinstance(x, str) and re.fullmatch(r"(?:ubuntu|windows|macos)-[a-zA-Z0-9.-]+", x) for x in labels):
        return "github_hosted_label"
    return "unknown"


def engine_markers(paths: list[str]) -> list[str]:
    result = set()
    for path in paths:
        p = PurePosixPath(path)
        if p.name == "ProjectVersion.txt" and p.parent.name == "ProjectSettings":
            result.add("unity")
        if p.suffix.lower() == ".uproject":
            result.add("unreal")
        if p.name == "project.godot":
            result.add("godot")
    return sorted(result)


def scan_workflow(text: str, *, repository_id: str, path: str, catalog: dict | None = None,
                  commit: str | None = None, engines: list[str] | None = None,
                  engine_tree_complete: bool = False) -> list[dict]:
    data = load_workflow(text)
    catalog = catalog or load_catalog()
    events = triggers(data)
    records = []
    for job_id, job in data["jobs"].items():
        if not isinstance(job, dict):
            continue
        steps = job.get("steps", [])
        if not isinstance(steps, list) or any(not isinstance(s, dict) for s in steps):
            raise WorkflowError("job steps must be a list of mappings")
        matches = [(i, agent_matches(step, catalog)) for i, step in enumerate(steps)]
        agents = sorted({agent for _, values in matches for agent in values})
        if not agents:
            continue
        agent_steps = [steps[i] for i, values in matches if values]
        context = {"workflow_env": data.get("env", {}), "job": job}
        agent_text = "\n".join(strings(agent_steps))
        refs = secret_refs(context)
        step_refs = secret_refs(agent_steps)
        perm = permissions(data, job)
        explicit_text = bool(EVENT_TEXT.search(agent_text))
        untrusted_event = bool(set(events) & UNTRUSTED_EVENTS)
        # A trigger is an input opportunity, not evidence that its body reaches a prompt.
        input_indicator = "present" if explicit_text else "unknown"
        sensitive = "present" if refs["names"] or perm["oidc"] == "present" else "unknown"
        write = perm["declared_write"]
        triple = input_indicator == sensitive == write == "present"
        actions = action_refs(steps)
        unresolved = any(a["kind"] in ("local", "dynamic") for a in actions) or any("run" in s for s in steps)
        has_checkout = any(str(s.get("uses", "")).lower().startswith("actions/checkout@") for s in steps)
        condition = str(job.get("if", "")) + "\n" + "\n".join(str(s.get("if", "")) for s in agent_steps)
        notes = [
            "Secret names are references, not proof of runtime availability.",
            "Token declarations are not effective runtime permissions.",
            "Egress and credential reachability require runtime validation.",
            "Third-party actions and repository content can introduce additional input and authority.",
        ]
        if set(events) & {"pull_request", "pull_request_review", "pull_request_review_comment"}:
            notes.append("Fork policy, approvals and repository settings may withhold secrets or downgrade tokens.")
        if "pull_request_target" in events:
            notes.append("Account for June 2026 checkout and cache restrictions, action versions, and explicit opt-outs.")
        if unresolved:
            notes.append("Local actions, shell scripts, matrix expansion and transitive behavior are not resolved.")
        records.append({
            "schema_version": 1, "record_kind": "configuration_observation",
            "repository_id": repository_id, "workflow_path": path, "job_id": str(job_id),
            "commit": commit, "workflow_sha256": sha256(text.encode("utf-8")),
            "catalog_sha256": sha256(json.dumps(catalog, sort_keys=True).encode()),
            "agents": agents, "agent_step_indices": [i for i, values in matches if values],
            "events": events, "untrusted_trigger_opportunity": untrusted_event,
            "event_text_reference_in_agent_step": explicit_text,
            "a_input_indicator": input_indicator, "b_sensitive_indicator": sensitive,
            "c_declared_repository_write": write,
            "triple_indicator_candidate": triple, "permissions": perm,
            "referenced_secret_names": refs["names"], "secret_categories": refs["categories"],
            "agent_step_secret_categories": step_refs["categories"],
            "dynamic_secret_reference": refs["dynamic"] or job.get("secrets") == "inherit",
            "model_secret_reference": "model" in refs["categories"],
            "non_model_secret_reference": any(x != "model" for x in refs["categories"]),
            "runner": runner_type(job.get("runs-on")),
            "runner_ephemerality": "unknown", "checkout_present": has_checkout,
            "checkout_persist_credentials_disabled": any(
                str(s.get("uses", "")).lower().startswith("actions/checkout@")
                and isinstance(s.get("with"), dict) and s["with"].get("persist-credentials") is False for s in steps),
            "visible_actor_condition": bool(re.search(r"github\.(?:actor|triggering_actor)|author_association", condition)),
            "actor_condition_validated": False,
            "tool_restriction_configuration_seen": bool(re.search(r"allowed.tools|allowedTools|sandbox|allowed_tools", agent_text)),
            "tool_restriction_enforced": "unknown", "egress_enforcement": "unknown",
            "cache_action_seen": any(str(s.get("uses", "")).lower().startswith("actions/cache") for s in steps),
            "action_references": actions,
            "engines": engines or [], "engine_detection_complete": engine_tree_complete,
            "limitations": notes,
        })
    return records
