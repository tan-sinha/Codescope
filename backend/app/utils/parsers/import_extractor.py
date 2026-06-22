from pathlib import Path
from app.data.import_info import ImportInfo


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
            result = _extract_import(
                node,
                file_bytes,
                file_path,
            )
            if isinstance(result, list):
                imports.extend(result)
            elif result is not None:
                imports.append(result)

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
        )

    return _extract_import_from(
        node,
        file_bytes,
        file_path,
    )


def _extract_import_statement(
    node,
    file_bytes,
):
    results = []

    for child in node.children:
        if child.type == "aliased_import":
            names = []
            aliases = {}
            _extract_aliased_import(
                child,
                file_bytes,
                names,
                aliases,
            )
            for name in names:
                results.append(ImportInfo(
                    module=name,
                    names=[name],
                    aliases=aliases,
                    is_relative=False,
                ))

        elif child.type == "dotted_name":
            name = _text(child, file_bytes)
            results.append(ImportInfo(
                module=name,
                names=[name],
                is_relative=False,
            ))

        elif child.type == "identifier":
            value = _text(child, file_bytes)
            if value not in ("from", "import"):
                results.append(ImportInfo(
                    module=value,
                    names=[value],
                    is_relative=False,
                ))

    return results


def _extract_import_from(
    node,
    file_bytes,
    file_path,
):
    module = ""
    names = []
    aliases = {}
    is_relative = False
    relative_level = 0

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
            relative_level = _text(
                child, file_bytes
            ).count(".")

        elif child.type == "aliased_import":
            _extract_aliased_import(
                child,
                file_bytes,
                names,
                aliases,
            )

        elif child.type == "dotted_name":
            names.append(
                _text(child, file_bytes)
            )

        elif child.type == "identifier":
            value = _text(child, file_bytes)
            if value not in ("from", "import"):
                names.append(value)

    resolved = None

    if is_relative:
        resolved = resolve_relative_import(
            file_path,
            module,
            relative_level,
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

    if current.name:
        py_file = current.with_suffix(".py")
        if py_file.exists():
            return str(py_file)

    init_file = current / "__init__.py"
    if init_file.exists():
        return str(init_file)

    return str(current)


def _text(node, file_bytes):
    return file_bytes[
        node.start_byte:node.end_byte
    ].decode("utf-8")
