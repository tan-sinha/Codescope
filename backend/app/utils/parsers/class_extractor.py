# utils/parsers/class_extractor.py

from app.data.class_info import (
    ClassInfo,
    MethodSignature,
)


def extract_classes(root, file_bytes):
    classes = []

    def walk(node):
        if node.type == "class_definition":
            classes.append(
                _extract_class(
                    node,
                    file_bytes,
                )
            )

        for child in node.children:
            walk(child)

    walk(root)
    return classes


def _extract_class(
    node,
    file_bytes,
):
    name = ""
    base_classes = []
    methods = []
    docstring = None

    name_node = node.child_by_field_name(
        "name"
    )

    if name_node:
        name = _text(
            name_node,
            file_bytes,
        )

    # (Base1, Base2)
    superclasses = node.child_by_field_name(
        "superclasses"
    )

    if superclasses:
        for child in superclasses.children:
            if child.type in (
                "identifier",
                "attribute",
                "dotted_name",
            ):
                base_classes.append(
                    _text(
                        child,
                        file_bytes,
                    )
                )

    body = node.child_by_field_name(
        "body"
    )

    if body:
        docstring = _extract_docstring(
            body,
            file_bytes,
        )

        methods = _extract_methods(
            body,
            file_bytes,
        )

    return ClassInfo(
        name=name,
        base_classes=base_classes,
        docstring=docstring,
        methods=methods,
        start_line=node.start_point[0]
        + 1,
        end_line=node.end_point[0]
        + 1,
    )


def _extract_methods(
    body,
    file_bytes,
):
    methods = []

    for child in body.children:
        if child.type == "decorated_definition":
            fn = child.child_by_field_name("definition")
            if fn is None or fn.type != "function_definition":
                continue
            child = fn
        elif child.type != "function_definition":
            continue

        name_node = (
            child.child_by_field_name(
                "name"
            )
        )

        if not name_node:
            continue

        method_name = _text(
            name_node,
            file_bytes,
        )

        params = []
        return_type = None

        params_node = (
            child.child_by_field_name(
                "parameters"
            )
        )

        if params_node:
            for p in params_node.children:
                if p.type == "identifier":
                    params.append(
                        _text(
                            p,
                            file_bytes,
                        )
                    )

                elif p.type in (
                    "typed_parameter",
                    "typed_default_parameter",
                    "default_parameter",
                ):
                    name = (
                        p.child_by_field_name(
                            "name"
                        )
                    )

                    if name:
                        params.append(
                            _text(
                                name,
                                file_bytes,
                            )
                        )

        return_node = (
            child.child_by_field_name(
                "return_type"
            )
        )

        if return_node:
            return_type = _text(
                return_node,
                file_bytes,
            )

        methods.append(
            MethodSignature(
                name=method_name,
                parameters=params,
                return_type=return_type,
            )
        )

    return methods


def _extract_docstring(
    body,
    file_bytes,
):
    if not body.children:
        return None

    first = body.children[0]

    if (
        first.type
        != "expression_statement"
    ):
        return None

    if not first.children:
        return None

    expr = first.children[0]

    if expr.type != "string":
        return None

    return _text(
        expr,
        file_bytes,
    ).strip('"').strip("'")


def _text(
    node,
    file_bytes,
):
    return file_bytes[
        node.start_byte:
        node.end_byte
    ].decode("utf-8")