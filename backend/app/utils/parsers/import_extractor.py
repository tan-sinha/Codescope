from pathlib import Path
import os
from app.data.import_info import ImportInfo

names = []
aliases = {}
module = ""
is_relative = False
relative_level = 0


def extract_imports(
    root,
    file_bytes,
    file_path,
):
    imports = []

    def walk(node):
        if node.type in (
            "import_statement",
            "import_from_statement",
        ):
            imports.append(
                _extract_import(
                    node,
                    file_bytes,
                    file_path,
                )
            )

        for child in node.children:
            walk(child)

    walk(root)
    return imports

def _extract_import(
    node,
    file_bytes,
    file_path,
):
    if node.type == "import_statement":
        return _extract_import_statement(
            node,
            file_bytes,
            file_path,
        )

    return _extract_import_from(
        node,
        file_bytes,
        file_path,
    )

def _extract_import_statement(
    node,
    file_bytes,
    file_path,
):
    names = []

    for child in node.children:

        if child.type == "relative_import":
            is_relative = True
            relative_level = len(
                _text(child, file_bytes)
            )

        elif child.type == "aliased_import":
            _extract_aliased_import(
                child,
                file_bytes,
                names,
                aliases,
            )

        elif child.type == "dotted_name":
            value = _text(
                child,
                file_bytes,
            )

            if value != module:
                names.append(value)

        elif child.type == "identifier":
            value = _text(
                child,
                file_bytes,
            )

            if value not in (
                "from",
                "import",
            ):
                names.append(value)

    return ImportInfo(
        module=names[0],
        names=names,
        is_relative=False,
    )

def _extract_import_from(
    node,
    file_bytes,
    file_path,
):
    module = ""
    names = []
    is_relative = False

    module_node = node.child_by_field_name(
        "module_name"
    )

    if module_node:
        module = _text(
            module_node,
            file_bytes,
        )

    for child in node.children:
        if child.type == "relative_import":
            is_relative = True

        if child.type == "dotted_name":
            names.append(
                _text(child, file_bytes)
            )

        if child.type == "identifier":
            value = _text(
                child,
                file_bytes
            )

            if value not in (
                "from",
                "import",
            ):
                names.append(value)

    resolved = None

    if is_relative:
        resolved = resolve_relative_import(
            file_path,
            module,
        )

    return ImportInfo(
        module=module,
        names=names,
        aliases=aliases,
        is_relative=is_relative,
        relative_level=relative_level,
        resolved_path=resolved,
    )

def _extract_aliased_import(
    node,
    file_bytes,
    names,
    aliases,
):
    original = None
    alias = None

    for child in node.children:
        if child.type == "dotted_name":
            original = _text(
                child,
                file_bytes,
            )

        elif child.type == "identifier":
            alias = _text(
                child,
                file_bytes,
            )

    if original:
        names.append(original)

    if original and alias:
        aliases[alias] = original

def resolve_relative_import(
    file_path: str,
    module: str,
    relative_level: int,
):
    current = Path(file_path).parent

    for _ in range(relative_level - 1):
        current = current.parent

    if module:
        current = current / module.replace(".", "/")

    py_file = current.with_suffix(".py")
    init_file = current / "__init__.py"

    if py_file.exists():
        return str(py_file)

    if init_file.exists():
        return str(init_file)

    return str(current)


def _text(node, file_bytes):
    return file_bytes[
        node.start_byte:node.end_byte
    ].decode("utf-8")