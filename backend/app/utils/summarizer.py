from app.data.function import FunctionInfo
import re

BATCH_SIZE=5


def generate_function_summaries(
    functions: list[FunctionInfo],
    llm_client=None,
):
    undocumented = []

    for fn in functions:
        summary, source = _docstring_summary(fn)

        if summary:
            fn.summary = summary
            fn.summary_source = source
        else:
            undocumented.append(fn)

    if llm_client:
        _generate_llm_summaries(
            undocumented,
            llm_client,
        )
    else:
        _generate_rule_based_summaries(
            undocumented,
        )

def _docstring_summary(
    fn: FunctionInfo,
):
    if not fn.docstring:
        return None, None

    text = " ".join(
        fn.docstring.split()
    )

    word_count = len(
        text.split()
    )

    if word_count > 10:
        return (
            _first_sentences(text, 2),
            "docstring",
        )

    return (
        text + " (auto-extracted)",
        "docstring_short",
    )


def _first_sentences(
    text: str,
    max_sentences: int = 2,
):
    sentences = re.split(
        r"(?<=[.!?])\s+",
        text,
    )

    sentences = [
        s.strip()
        for s in sentences
        if s.strip()
    ]

    return " ".join(
        sentences[:max_sentences]
    )

def _generate_rule_based_summaries(
    functions,
):
    for fn in functions:
        params = [
            p.name
            for p in fn.parameters
        ]

        param_text = (
            ", ".join(params)
            if params
            else "no parameters"
        )

        ret = (
            fn.return_type
            if fn.return_type
            else "unknown"
        )

        fn.summary = (
            f"{fn.name}: accepts "
            f"{param_text}, "
            f"returns {ret}."
        )

        fn.summary_source = (
            "rule_based"
        )

def _generate_llm_summaries(
    functions,
    llm_client,
):
    for i in range(
        0,
        len(functions),
        BATCH_SIZE,
    ):
        batch = functions[
            i:i + BATCH_SIZE
        ]

        prompt = (
            _build_prompt(batch)
        )

        response = (
            llm_client.generate(
                prompt
            )
        )

        summaries = (
            response.json()
        )

        for fn in batch:
            summary = summaries.get(
                fn.name
            )

            if summary:
                fn.summary = summary
                fn.summary_source = "llm"
            else:
                fn.summary = (
                    f"{fn.name}: no summary available."
                )
                fn.summary_source = (
                    "fallback"
                )

def _build_prompt(
    functions,
):
    lines = []

    lines.append(
        "Given these Python functions, "
        "write a one-line summary "
        "for each."
    )

    lines.append(
        'Return JSON: '
        '{"function_name":"summary"}'
    )

    for i, fn in enumerate(
        functions,
        start=1,
    ):
        lines.append(
            f"\nFunction {i}:"
        )
        lines.append(
            fn.source_code
        )

    return "\n".join(lines)


def generate_module_summary(
    module,
):
    module.summary = (
        f"Defines "
        f"{len(module.functions)} functions, "
        f"{len(module.classes)} classes, "
        f"and imports "
        f"{len(module.imports)} modules."
    )

    module.summary_source = (
        "rule_based"
    )