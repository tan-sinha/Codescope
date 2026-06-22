from collections import defaultdict

from app.data.graph import CallEdge , ResolutionStats

from pathlib import Path


def is_test_file(file_path: str):
    p = Path(file_path)

    parts = set(p.parts)

    if "tests" in parts:
        return True

    name = p.name

    return (
        name.startswith("test_")
        or name.endswith("_test.py")
    )

def extract_call_graph(
    root,
    file_bytes,
    file_path,
    function_index,
    import_index,
):
    edges = []

    _walk(
        root,
        file_bytes,
        file_path,
        function_index,
        import_index,
        edges,
        current_function=None,
        current_class=None,
    )

    return edges

def _walk(
    node,
    file_bytes,
    file_path,
    function_index,
    import_index,
    edges,
    current_function,
    current_class,
):
    if node.type == "class_definition":
        name = node.child_by_field_name("name")

        if name:
            current_class = _text(
                name,
                file_bytes,
            )

    if node.type == "function_definition":
        name = node.child_by_field_name("name")

        if name:
            fn_name = _text(
                name,
                file_bytes,
            )

            if current_class:
                current_function = (
                    f"{file_path}::"
                    f"{current_class}.{fn_name}"
                )
            else:
                current_function = (
                    f"{file_path}::{fn_name}"
                )

    if (
        node.type == "call"
        and current_function
    ):
        edge = _extract_call(
            node,
            file_bytes,
            file_path,
            current_function,
            current_class,
            function_index,
            import_index,
        )

        if edge:
            edges.append(edge)

    for child in node.children:
        _walk(
            child,
            file_bytes,
            file_path,
            function_index,
            import_index,
            edges,
            current_function,
            current_class,
        )

def _extract_call(
    call_node,
    file_bytes,
    file_path,
    caller,
    current_class,
    function_index,
    import_index,
):
    if not call_node.children:
        return None

    target = call_node.children[0]

    if target.type == "identifier":
        return _resolve_identifier_call(
            target,
            file_bytes,
            file_path,
            caller,
            function_index,
            import_index,
        )

    if target.type == "attribute":
        return _resolve_attribute_call(
            target,
            file_bytes,
            caller,
            current_class,
        )

    return None

def _resolve_identifier_call(
    node,
    file_bytes,
    file_path,
    caller,
    function_index,
    import_index,
):
    name = _text(
        node,
        file_bytes,
    )

    imports = import_index.get(
        file_path,
        []
    )

    for imp in imports:
        if name in imp.names:
            candidate = (
                f"{imp.module}::{name}"
            )

            if candidate in function_index:
                return CallEdge(
                    caller=caller,
                    callee=candidate,
                    resolved=True,
                )

    return CallEdge(
        caller=caller,
        callee=name,
        resolved=False,
        raw_text=name,
    )

def _resolve_attribute_call(
    node,
    file_bytes,
    caller,
    current_class,
):
    text = _text(
        node,
        file_bytes,
    )

    parts = text.split(".")

    if len(parts) != 2:
        return CallEdge(
            caller=caller,
            callee=text,
            resolved=False,
            raw_text=text,
        )

    obj, method = parts

    if obj == "self" and current_class:
        return CallEdge(
            caller=caller,
            callee=(
                f"{current_class}."
                f"{method}"
            ),
            resolved=True,
        )

    return CallEdge(
        caller=caller,
        callee=text,
        resolved=False,
        raw_text=text,
    )

def _text(
    node,
    file_bytes,
):
    return file_bytes[
        node.start_byte:
        node.end_byte
    ].decode("utf-8")

def build_reverse_graph(
    call_edges,
):
    called_by = defaultdict(list)

    for edge in call_edges:
        called_by[
            edge.callee
        ].append(
            edge.caller
        )

    return dict(called_by)

def build_call_graph(
    file_trees,
    function_index,
    repo_imports,
):
    call_edges = []

    overall = ResolutionStats()
    source_stats = ResolutionStats()
    test_stats = ResolutionStats()

    for file_path, data in file_trees.items():

        root = data["tree"].root_node
        file_bytes = data["bytes"]

        edges = extract_call_graph(
            root=root,
            file_bytes=file_bytes,
            file_path=file_path,
            function_index=function_index,
            import_index=repo_imports,
        )

        call_edges.extend(edges)

        is_test = is_test_file(
            file_path
        )

        for edge in edges:
            overall.total_calls += 1

            if edge.resolved:
                overall.resolved_calls += 1

            stats = (
                test_stats
                if is_test
                else source_stats
            )

            stats.total_calls += 1

            if edge.resolved:
                stats.resolved_calls += 1

    return {
        "edges": call_edges,
        "stats": {
            "overall": overall,
            "source": source_stats,
            "tests": test_stats,
        },
    }