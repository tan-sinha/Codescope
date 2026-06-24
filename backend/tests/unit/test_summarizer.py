from app.utils.summarizer import (
    generate_function_summaries,
    generate_module_summary,
)
from app.data.function import FunctionInfo, Parameter
from app.data.module import ModuleInfo


def _fn(name, docstring=None, params=None, return_type=None):
    return FunctionInfo(
        name=name,
        docstring=docstring,
        parameters=params or [],
        return_type=return_type,
        source_code=f"def {name}(): pass",
    )


class TestFunctionSummaries:
    def test_docstring_used_when_present(self):
        fn = _fn("foo", docstring="Adds two numbers together and returns the result.")
        generate_function_summaries([fn])
        assert fn.summary is not None
        assert fn.summary_source in ("docstring", "docstring_short")

    def test_short_docstring_tagged(self):
        fn = _fn("foo", docstring="Short doc.")
        generate_function_summaries([fn])
        assert fn.summary_source == "docstring_short"
        assert "auto-extracted" in fn.summary

    def test_long_docstring_uses_first_sentences(self):
        fn = _fn(
            "foo",
            docstring="Parses the incoming HTTP request payload. Validates all fields against the schema. Returns a structured response object.",
        )
        generate_function_summaries([fn])
        assert "Parses" in fn.summary
        assert fn.summary_source == "docstring"

    def test_rule_based_fallback_when_no_docstring(self):
        fn = _fn("add", params=[Parameter("x"), Parameter("y")], return_type="int")
        generate_function_summaries([fn])
        assert fn.summary is not None
        assert fn.summary_source == "rule_based"
        assert "add" in fn.summary

    def test_rule_based_shows_params(self):
        fn = _fn("process", params=[Parameter("data"), Parameter("config")])
        generate_function_summaries([fn])
        assert "data" in fn.summary
        assert "config" in fn.summary

    def test_rule_based_no_params(self):
        fn = _fn("noop")
        generate_function_summaries([fn])
        assert "no parameters" in fn.summary

    def test_multiple_functions(self):
        fns = [_fn("a"), _fn("b"), _fn("c")]
        generate_function_summaries(fns)
        for fn in fns:
            assert fn.summary is not None


class TestModuleSummary:
    def test_summary_mentions_counts(self):
        m = ModuleInfo(
            path="foo.py",
            functions=["a", "b"],
            classes=["C"],
            imports=["os", "sys"],
        )
        generate_module_summary(m)
        assert "2" in m.summary
        assert "1" in m.summary
        assert m.summary_source == "rule_based"

    def test_empty_module_summary(self):
        m = ModuleInfo(path="empty.py")
        generate_module_summary(m)
        assert m.summary is not None
