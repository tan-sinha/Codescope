from collections import defaultdict, deque
from pathlib import Path


def _split_identifier(identifier: str) -> tuple[str | None, str]:
    """'src/flask/app.py::Flask.route' → ('src/flask/app.py', 'Flask.route')"""
    parts = identifier.split("::", 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return None, identifier


def _node_type(name: str) -> str:
    return "method" if "." in name else "function"


# ---------------------------------------------------------------------------
# Import graph
# ---------------------------------------------------------------------------

def build_import_graph(knowledge_store: dict) -> dict:
    files = set(knowledge_store.get("files", []))
    imports_index = knowledge_store.get("imports", {})

    nodes: dict[str, dict] = {}
    seen_edges: set[tuple] = set()
    edges = []

    for f in files:
        nodes[f] = {"id": f, "type": "source", "file": f}

    for file_path, file_imports in imports_index.items():
        for imp in file_imports:
            target = _resolve_import_target(imp, files)

            if target is None:
                continue

            if target not in nodes:
                nodes[target] = {"id": target, "type": "external", "file": None}

            key = (file_path, target)
            if key not in seen_edges and file_path != target:
                seen_edges.add(key)
                edges.append({"from": file_path, "to": target, "type": "imports"})

    return {"nodes": list(nodes.values()), "edges": edges}


def _resolve_import_target(imp, files: set[str]) -> str | None:
    # Prefer resolved relative path — match against known files
    if imp.resolved_path:
        rp = imp.resolved_path.replace("\\", "/")
        for f in files:
            if rp.endswith(f) or f.endswith(rp):
                return f

    module = imp.module
    if not module:
        return None

    # Try to match module name to a known source file
    # e.g. "flask.ctx" → look for a file whose stem path matches
    module_as_path = module.replace(".", "/")
    for f in files:
        stem = Path(f).with_suffix("").as_posix()
        if stem.endswith(module_as_path):
            return f

    # External module
    return module


# ---------------------------------------------------------------------------
# Call graph (rooted BFS)
# ---------------------------------------------------------------------------

def build_rooted_call_graph(
    knowledge_store: dict,
    root: str,
    depth: int = 3,
) -> dict:
    call_graph = knowledge_store.get("call_graph", {})
    raw_edges = call_graph.get("edges", [])

    adjacency: dict[str, list] = defaultdict(list)
    for edge in raw_edges:
        adjacency[edge.caller].append(edge)

    start_callers = _find_root_callers(raw_edges, root)
    if not start_callers:
        return {"nodes": [], "edges": []}

    nodes: dict[str, dict] = {}
    seen_edges: set[tuple] = set()
    edges = []
    visited: set[str] = set()

    queue: deque[tuple[str, int]] = deque(
        (caller, 0) for caller in start_callers
    )

    while queue:
        caller, d = queue.popleft()
        if caller in visited:
            continue
        visited.add(caller)

        caller_file, caller_name = _split_identifier(caller)
        if caller not in nodes:
            nodes[caller] = {
                "id": caller_name,
                "type": _node_type(caller_name),
                "file": caller_file,
            }

        if d >= depth:
            continue

        for edge in adjacency[caller]:
            callee = edge.callee

            if edge.resolved:
                callee_file, callee_name = _split_identifier(callee)
                callee_node = {
                    "id": callee_name,
                    "type": _node_type(callee_name),
                    "file": callee_file,
                }
            else:
                callee_name = edge.raw_text or callee
                callee_node = {
                    "id": callee_name,
                    "type": "external",
                    "file": None,
                }
                callee = callee_name  # use as key for unresolved

            nodes.setdefault(callee, callee_node)

            edge_key = (caller_name, callee_name)
            if edge_key not in seen_edges:
                seen_edges.add(edge_key)
                edges.append({
                    "from": caller_name,
                    "to": callee_name,
                    "type": "calls",
                })

            if edge.resolved and callee not in visited:
                queue.append((callee, d + 1))

    return {"nodes": list(nodes.values()), "edges": edges}


def _find_root_callers(raw_edges, root: str) -> list[str]:
    """Find all caller identifiers that match the root query."""
    matched = set()

    for edge in raw_edges:
        _, name = _split_identifier(edge.caller)
        # Exact match on name part: "Flask.route" or "render_template"
        if name == root:
            matched.add(edge.caller)

    if matched:
        return list(matched)

    # Suffix match: "route" matches "Flask.route"
    for edge in raw_edges:
        _, name = _split_identifier(edge.caller)
        if name.endswith(f".{root}") or name == root:
            matched.add(edge.caller)

    return list(matched)
