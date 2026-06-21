"""
validate.py — Run all 4 AST extractors against Flask and print diagnostics.

Usage:
    python validate.py                         # clones Flask to /tmp/codescope/flask
    python validate.py /path/to/local/repo     # use existing local repo

Requirements:
    pip install tree-sitter tree-sitter-python
"""

import os
import sys
import subprocess
from collections import defaultdict
from pathlib import Path

import tree_sitter_python as tspython
from tree_sitter import Language, Parser

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

PY_LANGUAGE = Language(tspython.language())
parser = Parser(PY_LANGUAGE)

REPO_PATH = sys.argv[1] if len(sys.argv) > 1 else "/tmp/codescope/flask"

SKIP_DIRS = {".git", "__pycache__", "node_modules", ".tox", ".eggs", "*.egg-info"}
MAX_FILE_SIZE = 50_000  # skip files over 50KB


def clone_if_needed(path: str):
    if os.path.exists(path):
        print(f"[setup] Using existing repo at {path}")
        return
    print(f"[setup] Cloning Flask to {path}...")
    subprocess.run(
        ["git", "clone", "--depth", "1", "https://github.com/pallets/flask.git", path],
        check=True,
        capture_output=True,
    )
    print(f"[setup] Clone complete.")


def collect_python_files(root: str) -> list[str]:
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for f in filenames:
            if f.endswith(".py"):
                full = os.path.join(dirpath, f)
                if os.path.getsize(full) <= MAX_FILE_SIZE:
                    files.append(full)
    return sorted(files)


def rel(filepath: str) -> str:
    """Return path relative to repo root."""
    return os.path.relpath(filepath, REPO_PATH)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

class FunctionInfo:
    __slots__ = (
        "name", "qualified_name", "file", "line_start", "line_end",
        "signature", "docstring", "parameters", "return_type",
        "class_name", "decorators", "calls", "called_by",
    )

    def __init__(self):
        self.name = ""
        self.qualified_name = ""
        self.file = ""
        self.line_start = 0
        self.line_end = 0
        self.signature = ""
        self.docstring = ""
        self.parameters = []
        self.return_type = ""
        self.class_name = ""
        self.decorators = []
        self.calls = []       # list of raw callee strings
        self.called_by = []   # filled in Stage 3 (reverse graph)


class ClassInfo:
    __slots__ = ("name", "qualified_name", "file", "line_start", "line_end",
                 "docstring", "bases", "methods")

    def __init__(self):
        self.name = ""
        self.qualified_name = ""
        self.file = ""
        self.line_start = 0
        self.line_end = 0
        self.docstring = ""
        self.bases = []
        self.methods = []


class ImportInfo:
    __slots__ = ("module", "names", "is_relative")

    def __init__(self, module="", names=None, is_relative=False):
        self.module = module
        self.names = names or []
        self.is_relative = is_relative


# ---------------------------------------------------------------------------
# Extractor 1: Functions
# ---------------------------------------------------------------------------

def extract_docstring(block_node, source: bytes) -> str:
    """Check if the first statement in a block is a docstring."""
    if not block_node or not block_node.children:
        return ""
    first = block_node.children[0]
    if first.type == "expression_statement" and first.children:
        expr = first.children[0]
        if expr.type == "string":
            raw = source[expr.start_byte:expr.end_byte].decode("utf-8", errors="replace")
            # Strip triple quotes
            for q in ('"""', "'''"):
                if raw.startswith(q) and raw.endswith(q):
                    return raw[3:-3].strip()
            return raw.strip("\"'").strip()
    return ""


def extract_parameters(params_node, source: bytes) -> list[dict]:
    """Extract parameter names, types, and defaults."""
    if not params_node:
        return []
    results = []
    PARAM_TYPES = {
        "identifier",
        "typed_parameter",
        "typed_default_parameter",
        "default_parameter",
        "list_splat_pattern",
        "dictionary_splat_pattern",
    }
    for child in params_node.children:
        if child.type in PARAM_TYPES:
            text = source[child.start_byte:child.end_byte].decode("utf-8", errors="replace")
            if text != "self" and text != "cls":
                results.append({"text": text, "type": child.type})
    return results


def extract_decorators(decorated_node, source: bytes) -> list[str]:
    """Extract decorator names from a decorated_definition node."""
    decorators = []
    for child in decorated_node.children:
        if child.type == "decorator":
            text = source[child.start_byte:child.end_byte].decode("utf-8", errors="replace")
            decorators.append(text.lstrip("@").strip())
    return decorators


def extract_functions(root_node, source: bytes, filepath: str) -> list[FunctionInfo]:
    """Extract all functions/methods from a file's AST."""
    functions = []

    def _process_func(func_node, class_name="", decorators=None):
        info = FunctionInfo()
        info.file = rel(filepath)
        info.class_name = class_name

        # Name
        name_node = func_node.child_by_field_name("name")
        if name_node:
            info.name = source[name_node.start_byte:name_node.end_byte].decode()
        else:
            return None

        # Qualified name
        if class_name:
            info.qualified_name = f"{info.file}::{class_name}.{info.name}"
        else:
            info.qualified_name = f"{info.file}::{info.name}"

        # Lines
        info.line_start = func_node.start_point[0] + 1  # 1-indexed
        info.line_end = func_node.end_point[0] + 1

        # Signature
        sig_end = func_node.child_by_field_name("body")
        if sig_end:
            sig_bytes = source[func_node.start_byte:sig_end.start_byte]
            info.signature = sig_bytes.decode("utf-8", errors="replace").strip().rstrip(":")
        else:
            info.signature = source[func_node.start_byte:func_node.end_byte].decode()[:120]

        # Parameters
        params_node = func_node.child_by_field_name("parameters")
        info.parameters = extract_parameters(params_node, source)

        # Return type
        ret_node = func_node.child_by_field_name("return_type")
        if ret_node:
            info.return_type = source[ret_node.start_byte:ret_node.end_byte].decode()

        # Docstring
        body_node = func_node.child_by_field_name("body")
        info.docstring = extract_docstring(body_node, source)

        # Decorators
        info.decorators = decorators or []

        functions.append(info)
        return info

    def _walk(node, class_name=""):
        for child in node.children:
            if child.type == "function_definition":
                _process_func(child, class_name=class_name)

            elif child.type == "decorated_definition":
                decos = extract_decorators(child, source)
                # Find the actual function or class inside
                for sub in child.children:
                    if sub.type == "function_definition":
                        _process_func(sub, class_name=class_name, decorators=decos)
                    elif sub.type == "class_definition":
                        _process_class(sub, decorators=decos)

            elif child.type == "class_definition":
                _process_class(child)

    def _process_class(class_node, decorators=None):
        name_node = class_node.child_by_field_name("name")
        if name_node:
            cname = source[name_node.start_byte:name_node.end_byte].decode()
            body = class_node.child_by_field_name("body")
            if body:
                _walk(body, class_name=cname)

    _walk(root_node)
    return functions


# ---------------------------------------------------------------------------
# Extractor 2: Classes
# ---------------------------------------------------------------------------

def extract_classes(root_node, source: bytes, filepath: str) -> list[ClassInfo]:
    """Extract all classes from a file's AST."""
    classes = []

    def _process(node, decorators=None):
        info = ClassInfo()
        info.file = rel(filepath)

        name_node = node.child_by_field_name("name")
        if name_node:
            info.name = source[name_node.start_byte:name_node.end_byte].decode()
        else:
            return
        info.qualified_name = f"{info.file}::{info.name}"
        info.line_start = node.start_point[0] + 1
        info.line_end = node.end_point[0] + 1

        # Base classes
        superclasses = node.child_by_field_name("superclasses")
        if superclasses:
            for child in superclasses.children:
                if child.type in ("identifier", "attribute"):
                    info.bases.append(source[child.start_byte:child.end_byte].decode())

        # Docstring
        body = node.child_by_field_name("body")
        info.docstring = extract_docstring(body, source)

        # Methods (just names)
        if body:
            for child in body.children:
                if child.type == "function_definition":
                    mn = child.child_by_field_name("name")
                    if mn:
                        info.methods.append(source[mn.start_byte:mn.end_byte].decode())
                elif child.type == "decorated_definition":
                    for sub in child.children:
                        if sub.type == "function_definition":
                            mn = sub.child_by_field_name("name")
                            if mn:
                                info.methods.append(source[mn.start_byte:mn.end_byte].decode())

        classes.append(info)

    def _walk(node):
        for child in node.children:
            if child.type == "class_definition":
                _process(child)
            elif child.type == "decorated_definition":
                for sub in child.children:
                    if sub.type == "class_definition":
                        decos = extract_decorators(child, source)
                        _process(sub, decorators=decos)

    _walk(root_node)
    return classes


# ---------------------------------------------------------------------------
# Extractor 3: Imports
# ---------------------------------------------------------------------------

def extract_imports(root_node, source: bytes) -> list[ImportInfo]:
    """Extract all import statements from a file's AST."""
    imports = []

    for child in root_node.children:
        if child.type == "import_statement":
            # import X, Y
            for sub in child.children:
                if sub.type == "dotted_name":
                    module = source[sub.start_byte:sub.end_byte].decode()
                    imports.append(ImportInfo(module=module, names=[module.split(".")[-1]]))

        elif child.type == "import_from_statement":
            # from X import Y, Z
            module = ""
            names = []
            is_relative = False

            for sub in child.children:
                if sub.type == "dotted_name":
                    if not module:
                        module = source[sub.start_byte:sub.end_byte].decode()
                    else:
                        names.append(source[sub.start_byte:sub.end_byte].decode())
                elif sub.type == "relative_import":
                    is_relative = True
                    module = source[sub.start_byte:sub.end_byte].decode()
                elif sub.type == "identifier" and module:
                    # individual name after import keyword
                    name = source[sub.start_byte:sub.end_byte].decode()
                    if name not in ("import", "from"):
                        names.append(name)
                elif sub.type == "wildcard_import":
                    names.append("*")

            if module:
                imports.append(ImportInfo(module=module, names=names, is_relative=is_relative))

    return imports


# ---------------------------------------------------------------------------
# Extractor 4: Call Graph
# ---------------------------------------------------------------------------

def extract_calls_from_body(body_node, source: bytes) -> list[dict]:
    """Recursively find all function calls within a node subtree."""
    calls = []

    def _walk(node):
        if node.type == "call":
            func_node = node.children[0] if node.children else None
            if func_node:
                call_info = _resolve_call_target(func_node, source)
                if call_info:
                    calls.append(call_info)
        for child in node.children:
            _walk(child)

    _walk(body_node)
    return calls


def _resolve_call_target(func_node, source: bytes) -> dict | None:
    """Determine what's being called from the call's function node."""
    if func_node.type == "identifier":
        name = source[func_node.start_byte:func_node.end_byte].decode()
        return {"raw": name, "type": "simple"}

    elif func_node.type == "attribute":
        obj_node = func_node.child_by_field_name("object")
        attr_node = func_node.child_by_field_name("attribute")
        if obj_node and attr_node:
            obj_text = source[obj_node.start_byte:obj_node.end_byte].decode()
            attr_text = source[attr_node.start_byte:attr_node.end_byte].decode()
            return {
                "raw": f"{obj_text}.{attr_text}",
                "object": obj_text,
                "method": attr_text,
                "type": "method",
            }

    return None


def build_call_graph(
    all_functions: list[FunctionInfo],
    all_classes: dict[str, ClassInfo],
    file_imports: dict[str, list[ImportInfo]],
    file_source: dict[str, bytes],
) -> tuple[dict, dict, dict]:
    """
    Build forward and reverse call graphs.

    Returns:
        forward_graph: {qualified_name: [callee_qualified_names]}
        reverse_graph: {qualified_name: [caller_qualified_names]}
        resolution_stats: {"resolved_self": N, "resolved_import": N, "unresolved": N}
    """
    # Build lookup indexes for resolution
    # 1. All known function names → qualified name
    name_to_qualified = defaultdict(list)
    for func in all_functions:
        # short name → qualified
        name_to_qualified[func.name].append(func.qualified_name)
        # Class.method → qualified
        if func.class_name:
            name_to_qualified[f"{func.class_name}.{func.name}"].append(func.qualified_name)

    # 2. Import-based lookup: for each file, what names are imported and from where
    imported_names = {}  # (file, name) → source module
    for filepath, imps in file_imports.items():
        for imp in imps:
            for name in imp.names:
                imported_names[(filepath, name)] = imp.module

    forward_graph = {}
    stats = {"resolved_self": 0, "resolved_import": 0, "unresolved": 0}

    for func in all_functions:
        # Re-parse the function to extract calls from its body
        source = file_source.get(func.file)
        if source is None:
            continue

        tree = parser.parse(source)

        # Find this function's node in the tree by line range
        func_body = _find_function_body(tree.root_node, func.name, func.line_start - 1)
        if func_body is None:
            continue

        raw_calls = extract_calls_from_body(func_body, source)
        resolved_calls = []

        for call in raw_calls:
            resolved = _try_resolve(call, func, name_to_qualified, imported_names)
            resolved_calls.append(resolved)

            if resolved["resolution"] == "self":
                stats["resolved_self"] += 1
            elif resolved["resolution"] == "import":
                stats["resolved_import"] += 1
            else:
                stats["unresolved"] += 1

        func.calls = resolved_calls
        forward_graph[func.qualified_name] = resolved_calls

    # Build reverse graph
    reverse_graph = defaultdict(list)
    for caller_qname, callees in forward_graph.items():
        for callee in callees:
            if callee.get("resolved_to"):
                reverse_graph[callee["resolved_to"]].append(caller_qname)

    # Apply called_by to function objects
    for func in all_functions:
        func.called_by = reverse_graph.get(func.qualified_name, [])

    return forward_graph, dict(reverse_graph), stats


def _find_function_body(root_node, func_name: str, line_0indexed: int):
    """Find a function's body node by name and line number."""

    def _search(node):
        if node.type == "function_definition":
            name_node = node.child_by_field_name("name")
            if (name_node and
                node.start_point[0] == line_0indexed and
                node.source_text is not None or True):
                # Check name matches
                # We can't easily read the name without source, but we have line match
                body = node.child_by_field_name("body")
                return body

        for child in node.children:
            result = _search(child)
            if result:
                return result
        return None

    # Alternative approach: walk ALL function_definitions, match by line
    def _search_by_line(node):
        if node.type == "function_definition" and node.start_point[0] == line_0indexed:
            return node.child_by_field_name("body")
        for child in node.children:
            result = _search_by_line(child)
            if result:
                return result
        return None

    return _search_by_line(root_node)


def _try_resolve(
    call: dict,
    caller_func: FunctionInfo,
    name_to_qualified: dict,
    imported_names: dict,
) -> dict:
    """Try to resolve a raw call to a qualified function name."""
    result = {**call, "resolution": "unresolved", "resolved_to": ""}

    if call["type"] == "simple":
        # Simple call like create_app() or Flask()
        raw_name = call["raw"]

        # Check if it's an imported name
        import_source = imported_names.get((caller_func.file, raw_name))
        if import_source:
            # Check if we have a function with this name from that module
            candidates = name_to_qualified.get(raw_name, [])
            for cand in candidates:
                if import_source.replace(".", "/") in cand:
                    result["resolution"] = "import"
                    result["resolved_to"] = cand
                    return result
            # Imported but can't resolve to our index (external library)
            result["resolution"] = "external"
            result["resolved_to"] = f"{import_source}.{raw_name}"
            return result

        # Check if it's a function defined in the same file
        candidates = name_to_qualified.get(raw_name, [])
        same_file = [c for c in candidates if c.startswith(caller_func.file + "::")]
        if same_file:
            result["resolution"] = "import"  # same-file resolution
            result["resolved_to"] = same_file[0]
            return result

        # Builtins — don't count as unresolved
        if raw_name in _PYTHON_BUILTINS:
            result["resolution"] = "builtin"
            result["resolved_to"] = f"builtin.{raw_name}"
            return result

    elif call["type"] == "method":
        obj = call.get("object", "")
        method = call.get("method", "")

        # Case 1: self.method() → resolve to enclosing class
        if obj == "self" and caller_func.class_name:
            target_name = f"{caller_func.class_name}.{method}"
            candidates = name_to_qualified.get(target_name, [])
            if candidates:
                # Prefer same file
                same_file = [c for c in candidates if c.startswith(caller_func.file + "::")]
                result["resolution"] = "self"
                result["resolved_to"] = same_file[0] if same_file else candidates[0]
                return result
            # Method might be inherited — still mark as self-resolved with class hint
            result["resolution"] = "self"
            result["resolved_to"] = f"{caller_func.file}::{target_name}"
            return result

        # Case 2: cls.method() (classmethods)
        if obj == "cls" and caller_func.class_name:
            target_name = f"{caller_func.class_name}.{method}"
            candidates = name_to_qualified.get(target_name, [])
            if candidates:
                same_file = [c for c in candidates if c.startswith(caller_func.file + "::")]
                result["resolution"] = "self"
                result["resolved_to"] = same_file[0] if same_file else candidates[0]
                return result

        # Case 3: super().method()
        if obj == "super()":
            result["resolution"] = "super"
            result["resolved_to"] = f"super.{method}"
            return result

        # Case 4: ImportedClass.method() — check if object name is an imported class
        import_source = imported_names.get((caller_func.file, obj))
        if import_source:
            target_name = f"{obj}.{method}"
            candidates = name_to_qualified.get(target_name, [])
            if candidates:
                result["resolution"] = "import"
                result["resolved_to"] = candidates[0]
                return result
            result["resolution"] = "external"
            result["resolved_to"] = f"{import_source}.{obj}.{method}"
            return result

    return result


_PYTHON_BUILTINS = {
    "print", "len", "range", "int", "str", "float", "bool", "list", "dict",
    "set", "tuple", "type", "isinstance", "issubclass", "hasattr", "getattr",
    "setattr", "delattr", "callable", "super", "property", "staticmethod",
    "classmethod", "enumerate", "zip", "map", "filter", "sorted", "reversed",
    "min", "max", "sum", "abs", "round", "repr", "hash", "id", "iter",
    "next", "open", "vars", "dir", "any", "all", "format", "input",
    "ValueError", "TypeError", "KeyError", "AttributeError", "RuntimeError",
    "NotImplementedError", "ImportError", "OSError", "StopIteration",
    "Exception", "BaseException", "object",
}


# ---------------------------------------------------------------------------
# Main — Run all extractors and print diagnostics
# ---------------------------------------------------------------------------

def main():
    clone_if_needed(REPO_PATH)

    py_files = collect_python_files(REPO_PATH)
    print(f"\n{'='*60}")
    print(f"REPO: {REPO_PATH}")
    print(f"Python files found: {len(py_files)}")
    print(f"{'='*60}\n")

    # Storage
    all_functions: list[FunctionInfo] = []
    all_classes_list: list[ClassInfo] = []
    all_classes_dict: dict[str, ClassInfo] = {}
    file_imports: dict[str, list[ImportInfo]] = {}
    file_source: dict[str, bytes] = {}
    file_function_count: dict[str, int] = {}

    # ── Pass 1: Extract functions, classes, imports ──
    for filepath in py_files:
        with open(filepath, "rb") as f:
            source = f.read()

        relpath = rel(filepath)
        file_source[relpath] = source
        tree = parser.parse(source)
        root = tree.root_node

        funcs = extract_functions(root, source, filepath)
        all_functions.extend(funcs)
        file_function_count[relpath] = len(funcs)

        clses = extract_classes(root, source, filepath)
        all_classes_list.extend(clses)
        for c in clses:
            all_classes_dict[c.name] = c

        imps = extract_imports(root, source)
        file_imports[relpath] = imps

    # ── Pass 2: Build call graph ──
    forward_graph, reverse_graph, call_stats = build_call_graph(
        all_functions, all_classes_dict, file_imports, file_source
    )

    # ══════════════════════════════════════════════════════════
    # CHECK 1: Function count
    # ══════════════════════════════════════════════════════════
    print("CHECK 1 — FUNCTION COUNT")
    print(f"  Total functions/methods: {len(all_functions)}")
    print(f"  Top 10 files by function count:")
    sorted_files = sorted(file_function_count.items(), key=lambda x: -x[1])
    for fpath, count in sorted_files[:10]:
        print(f"    {fpath:<55} {count:>3} functions")

    methods = [f for f in all_functions if f.class_name]
    top_level = [f for f in all_functions if not f.class_name]
    print(f"  Methods (inside classes): {len(methods)}")
    print(f"  Top-level functions:      {len(top_level)}")

    # Cross-validate hint
    print(f"\n  Cross-validate with:")
    print(f"    grep -rn 'def ' {REPO_PATH}/src/ | wc -l")
    print()

    # ══════════════════════════════════════════════════════════
    # CHECK 2: Class count
    # ══════════════════════════════════════════════════════════
    print("CHECK 2 — CLASS COUNT")
    print(f"  Total classes: {len(all_classes_list)}")
    sorted_classes = sorted(all_classes_list, key=lambda c: -len(c.methods))
    for cls in sorted_classes[:10]:
        bases = f" ({', '.join(cls.bases)})" if cls.bases else ""
        print(f"    {cls.name}{bases:<40} {len(cls.methods):>3} methods  [{cls.file}]")
    print()

    # ══════════════════════════════════════════════════════════
    # CHECK 3: Sample function detail
    # ══════════════════════════════════════════════════════════
    print("CHECK 3 — SAMPLE FUNCTION DETAIL")

    # Pick a function that likely has docstring, params, and calls
    # Try to find Flask.route or a well-known function
    sample = None
    for f in all_functions:
        if f.name == "route" and f.class_name:
            sample = f
            break
    if not sample:
        # Fallback: pick the function with the most calls
        sample = max(all_functions, key=lambda f: len(f.calls)) if all_functions else None

    if sample:
        print(f"  Name:        {sample.qualified_name}")
        print(f"  Signature:   {sample.signature}")
        print(f"  Lines:       {sample.line_start}-{sample.line_end}")
        print(f"  Class:       {sample.class_name or '(top-level)'}")
        print(f"  Return type: {sample.return_type or '(none)'}")
        print(f"  Docstring:   {sample.docstring[:120]}{'...' if len(sample.docstring) > 120 else ''}")
        print(f"  Parameters:  {[p['text'] for p in sample.parameters]}")
        print(f"  Decorators:  {sample.decorators}")
        print(f"  Calls ({len(sample.calls)}):")
        for c in sample.calls[:8]:
            res = c.get('resolution', '?')
            target = c.get('resolved_to', c.get('raw', '?'))
            print(f"    → {c.get('raw', '?'):<40} [{res}] → {target}")
        if len(sample.calls) > 8:
            print(f"    ... and {len(sample.calls) - 8} more")
        print(f"  Called by ({len(sample.called_by)}):")
        for cb in sample.called_by[:5]:
            print(f"    ← {cb}")
        if len(sample.called_by) > 5:
            print(f"    ... and {len(sample.called_by) - 5} more")
    else:
        print("  (no functions found)")
    print()

    # ══════════════════════════════════════════════════════════
    # CHECK 4: Import graph for one file
    # ══════════════════════════════════════════════════════════
    print("CHECK 4 — IMPORT GRAPH")

    # Pick a file with many imports
    target_file = max(file_imports.keys(), key=lambda k: len(file_imports[k])) if file_imports else None
    if target_file:
        imps = file_imports[target_file]
        print(f"  File: {target_file} ({len(imps)} import statements)")

        stdlib = []
        external = []
        internal = []

        # Simple heuristic: if the module starts with the repo's package name, it's internal
        pkg_names = set()
        src_dir = os.path.join(REPO_PATH, "src")
        if os.path.exists(src_dir):
            for d in os.listdir(src_dir):
                if os.path.isdir(os.path.join(src_dir, d)):
                    pkg_names.add(d)
        if not pkg_names:
            pkg_names = {"flask"}  # fallback

        for imp in imps:
            mod_root = imp.module.split(".")[0]
            if imp.is_relative or mod_root in pkg_names:
                internal.append(f"{imp.module} → {imp.names}")
            elif mod_root in _STDLIB_TOP:
                stdlib.append(f"{imp.module} → {imp.names}")
            else:
                external.append(f"{imp.module} → {imp.names}")

        print(f"  stdlib ({len(stdlib)}):")
        for s in stdlib[:8]:
            print(f"    {s}")
        print(f"  external ({len(external)}):")
        for s in external[:8]:
            print(f"    {s}")
        print(f"  internal ({len(internal)}):")
        for s in internal[:8]:
            print(f"    {s}")
    print()

    # ══════════════════════════════════════════════════════════
    # CHECK 5: Call graph sample
    # ══════════════════════════════════════════════════════════
    print("CHECK 5 — CALL GRAPH SAMPLE")

    # Find a function with both callers and callees
    interesting = [f for f in all_functions if f.calls and f.called_by]
    if interesting:
        sample_cg = sorted(interesting, key=lambda f: len(f.calls) + len(f.called_by), reverse=True)[0]
        print(f"  Function: {sample_cg.qualified_name}")
        print(f"  Calls ({len(sample_cg.calls)}):")
        for c in sample_cg.calls[:6]:
            res = c.get('resolution', '?')
            print(f"    → {c.get('raw','?'):<35} [{res}]  resolved: {c.get('resolved_to','')}")
        print(f"  Called by ({len(sample_cg.called_by)}):")
        for cb in sample_cg.called_by[:6]:
            print(f"    ← {cb}")
    else:
        print("  (no functions with both callers and callees found)")
    print()

    # ══════════════════════════════════════════════════════════
    # CHECK 6: Resolution stats
    # ══════════════════════════════════════════════════════════
    print("CHECK 6 — CALL GRAPH RESOLUTION STATS")
    total_edges = sum(call_stats.values())
    if total_edges > 0:
        print(f"  Total call edges:           {total_edges}")
        for key in ("resolved_self", "resolved_import", "unresolved"):
            count = call_stats[key]
            pct = count / total_edges * 100
            print(f"  {key:<30} {count:>5}  ({pct:.1f}%)")
    else:
        print("  No call edges found.")

    # Show most-called unresolved patterns
    unresolved_patterns = defaultdict(int)
    for func in all_functions:
        for call in func.calls:
            if call.get("resolution") == "unresolved":
                unresolved_patterns[call.get("raw", "?")] += 1

    if unresolved_patterns:
        print(f"\n  Top 10 unresolved call patterns:")
        for pattern, count in sorted(unresolved_patterns.items(), key=lambda x: -x[1])[:10]:
            print(f"    {pattern:<45} called {count}x")
    print()

    # ══════════════════════════════════════════════════════════
    # SUMMARY
    # ══════════════════════════════════════════════════════════
    print("=" * 60)
    print("SUMMARY")
    print(f"  Files:     {len(py_files)}")
    print(f"  Functions: {len(all_functions)}")
    print(f"  Classes:   {len(all_classes_list)}")
    print(f"  Call edges: {total_edges} ({call_stats.get('resolved_self',0) + call_stats.get('resolved_import',0)} resolved, {call_stats.get('unresolved',0)} unresolved)")

    with_docs = sum(1 for f in all_functions if f.docstring)
    without_docs = len(all_functions) - with_docs
    print(f"  Documented functions: {with_docs}")
    print(f"  Undocumented (need LLM): {without_docs}")
    if all_functions:
        print(f"  LLM cost estimate: ~${without_docs * 0.002:.2f} (at ~$0.002/function with GPT-4o-mini)")
    print("=" * 60)


_STDLIB_TOP = {
    "os", "sys", "io", "re", "json", "csv", "math", "random", "datetime",
    "time", "pathlib", "typing", "collections", "functools", "itertools",
    "contextlib", "abc", "dataclasses", "enum", "logging", "warnings",
    "hashlib", "hmac", "secrets", "copy", "pprint", "textwrap", "string",
    "struct", "codecs", "unicodedata", "difflib", "operator", "inspect",
    "importlib", "pkgutil", "threading", "multiprocessing", "subprocess",
    "socket", "http", "urllib", "email", "html", "xml", "sqlite3",
    "unittest", "doctest", "pytest", "tempfile", "shutil", "glob",
    "fnmatch", "stat", "zipfile", "tarfile", "gzip", "bz2", "lzma",
    "signal", "weakref", "array", "queue", "heapq", "bisect",
    "decimal", "fractions", "numbers", "cmath", "statistics",
    "traceback", "linecache", "tokenize", "ast", "dis", "compileall",
    "__future__", "types", "typing_extensions", "annotations", "t",
}


if __name__ == "__main__":
    main()