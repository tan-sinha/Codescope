# app/utils/parsers/function_extractor.py

from typing import List

from app.data.function import FunctionInfo, Parameter


def extract_functions(root, file_bytes: bytes) -> List[FunctionInfo]:
    functions = []

    def walk(node):
        if node.type == "function_definition":
            functions.append(
                _extract_function(node, file_bytes)
            )

        for child in node.children:
            walk(child)

    walk(root)
    return functions


def _extract_function(node, file_bytes: bytes) -> FunctionInfo:
    name = None
    parameters = []
    return_type = None
    docstring = None
    decorators = []

    # -------------------------
    # Name
    # -------------------------
    identifier = node.child_by_field_name("name")
    if identifier:
        name = _node_text(identifier, file_bytes)

    # -------------------------
    # Parameters
    # -------------------------
    params_node = node.child_by_field_name("parameters")
    if params_node:
        parameters = _extract_parameters(
            params_node,
            file_bytes
        )

    # -------------------------
    # Return Type
    # -------------------------
    return_node = node.child_by_field_name(
        "return_type"
    )

    if return_node:
        return_type = _node_text(
            return_node,
            file_bytes
        )

    # -------------------------
    # Docstring
    # -------------------------
    body = node.child_by_field_name("body")
    if body:
        docstring = _extract_docstring(
            body,
            file_bytes
        )

    # -------------------------
    # Decorators
    # -------------------------
    decorators = _extract_decorators(
        node,
        file_bytes
    )

    # -------------------------
    # Source code
    # -------------------------
    source_code = file_bytes[
        node.start_byte: node.end_byte
    ].decode("utf-8")

    return FunctionInfo(
        name=name,
        parameters=parameters,
        return_type=return_type,
        docstring=docstring,
        decorators=decorators,
        source_code=source_code,
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
    )


def _extract_parameters(
    params_node,
    file_bytes: bytes
):
    params = []

    for child in params_node.children:

        if child.type in (
            "identifier",
            "typed_parameter",
            "default_parameter",
            "typed_default_parameter",
        ):
            param = _extract_single_parameter(
                child,
                file_bytes
            )
            if param:
                params.append(param)

    return params


def _extract_single_parameter(
    node,
    file_bytes: bytes,
):
    # x
    if node.type == "identifier":
        return Parameter(
            name=_node_text(node, file_bytes)
        )

    # x: str
    if node.type == "typed_parameter":
        name_node = node.child_by_field_name("name")
        type_node = node.child_by_field_name("type")

        if not name_node:
            return None

        return Parameter(
            name=_node_text(name_node, file_bytes),
            annotation=(
                _node_text(type_node, file_bytes)
                if type_node
                else None
            ),
        )

    # x=5
    if node.type == "default_parameter":
        name_node = node.child_by_field_name("name")

        if not name_node:
            return None

        return Parameter(
            name=_node_text(name_node, file_bytes)
        )

    # x: str = "abc"
    if node.type == "typed_default_parameter":
        name_node = node.child_by_field_name("name")
        type_node = node.child_by_field_name("type")

        if not name_node:
            return None

        return Parameter(
            name=_node_text(name_node, file_bytes),
            annotation=(
                _node_text(type_node, file_bytes)
                if type_node
                else None
            ),
        )

    return None


def _extract_docstring(
    body_node,
    file_bytes: bytes,
):
    if not body_node.children:
        return None

    first = body_node.children[0]

    if first.type != "expression_statement":
        return None

    if not first.children:
        return None

    expr = first.children[0]

    if expr.type == "string":
        text = _node_text(
            expr,
            file_bytes
        )

        return text.strip("\"'")

    return None


def _extract_decorators(
    node,
    file_bytes: bytes,
):
    decorators = []

    prev = node.prev_named_sibling

    while prev and prev.type == "decorator":
        decorators.insert(
            0,
            _node_text(prev, file_bytes)
        )
        prev = prev.prev_named_sibling

    return decorators


def _node_text(
    node,
    file_bytes: bytes
):
    return file_bytes[
        node.start_byte: node.end_byte
    ].decode("utf-8")