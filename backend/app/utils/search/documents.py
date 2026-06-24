from pathlib import Path

from app.utils.parsers.call_graph_extractor import is_test_file

MAX_DOC_CHARS = 1500


def build_search_documents(modules, functions_index, classes_index, call_graph):
    documents = []
    mapping = []

    reverse_graph = {}
    for edge in call_graph["edges"]:
        reverse_graph.setdefault(edge.callee, []).append(edge.caller)

    for identifier, fn in functions_index.items():
        file_path = identifier.split("::")[0]
        if is_test_file(file_path):
            continue

        module_summary = modules[file_path].summary if file_path in modules else ""
        calls = [
            edge.callee
            for edge in call_graph["edges"]
            if edge.caller == identifier
        ]
        called_by = reverse_graph.get(identifier, [])

        doc = build_function_document(
            function=fn,
            file_path=file_path,
            module_summary=module_summary,
            calls=calls,
            called_by=called_by,
        )
        documents.append(doc)
        mapping.append(identifier)

    for identifier, cls in classes_index.items():
        file_path = identifier.split("::")[0]
        if is_test_file(file_path):
            continue

        module_summary = modules[file_path].summary if file_path in modules else ""

        doc = build_class_document(cls, file_path, module_summary)
        documents.append(doc)
        mapping.append(identifier)

        for method in cls.methods:
            method_key = f"{identifier}.{method.name}"
            method_doc = build_method_document(cls.name, method, file_path)
            documents.append(method_doc)
            mapping.append(method_key)

    return documents, mapping


def _path_tokens(file_path: str) -> str:
    parts = Path(file_path).with_suffix("").parts
    return " ".join(parts * 3)


def build_function_document(function, file_path, module_summary, calls, called_by):
    parts = [
        _path_tokens(file_path),
        function.name,
        function.summary or "",
        function.docstring or "",
        " ".join(p.name for p in function.parameters),
        module_summary,
        " ".join(calls),
        " ".join(called_by),
        function.source_code,
    ]
    doc = " ".join(p for p in parts if p)
    return doc[:MAX_DOC_CHARS]


def build_class_document(cls, file_path, module_summary):
    parts = [
        _path_tokens(file_path),
        cls.name,
        cls.docstring or "",
        " ".join(cls.base_classes),
        " ".join(m.name for m in cls.methods),
        module_summary,
    ]
    doc = " ".join(p for p in parts if p)
    return doc[:MAX_DOC_CHARS]


def build_method_document(class_name, method, file_path):
    parts = [
        _path_tokens(file_path),
        f"{class_name}.{method.name}",
        method.name,
        " ".join(method.parameters),
        method.return_type or "",
    ]
    doc = " ".join(p for p in parts if p)
    return doc[:MAX_DOC_CHARS]
