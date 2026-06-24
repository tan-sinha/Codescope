from app.utils.search.bm25_index import build_bm25_index
from app.utils.search.documents import (
    build_function_document,
    build_class_document,
)
from app.data.function import FunctionInfo, Parameter
from app.data.class_info import ClassInfo, MethodSignature


def _fn(name, summary=None, docstring=None, params=None, source=""):
    return FunctionInfo(
        name=name,
        summary=summary,
        docstring=docstring,
        parameters=params or [],
        source_code=source,
    )


def _cls(name, methods=None, docstring=None):
    return ClassInfo(
        name=name,
        methods=methods or [],
        docstring=docstring,
    )


class TestBuildBm25Index:
    def test_returns_bm25_and_corpus(self):
        bm25, corpus = build_bm25_index(["hello world", "foo bar"])
        assert bm25 is not None
        assert len(corpus) == 2

    def test_score_relevant_doc_higher(self):
        docs = ["parse python functions", "build html templates", "render css styles"]
        bm25, corpus = build_bm25_index(docs)
        from app.utils.search.tokenizer import code_tokenize
        scores = bm25.get_scores(code_tokenize("parse python"))
        assert scores[0] > scores[1]
        assert scores[0] > scores[2]


class TestBuildFunctionDocument:
    def test_includes_name(self):
        fn = _fn("my_function")
        doc = build_function_document(fn, "src/utils.py", "", [], [])
        assert "my_function" in doc

    def test_includes_summary(self):
        fn = _fn("foo", summary="Parses a Python file.")
        doc = build_function_document(fn, "src/utils.py", "", [], [])
        assert "Parses" in doc

    def test_includes_params(self):
        fn = _fn("foo", params=[Parameter("x"), Parameter("y")])
        doc = build_function_document(fn, "src/utils.py", "", [], [])
        assert "x" in doc
        assert "y" in doc

    def test_includes_module_summary(self):
        fn = _fn("foo")
        doc = build_function_document(fn, "src/utils.py", "Handles authentication logic", [], [])
        assert "authentication" in doc

    def test_includes_calls(self):
        fn = _fn("foo")
        doc = build_function_document(fn, "src/utils.py", "", ["bar", "baz"], [])
        assert "bar" in doc

    def test_includes_called_by(self):
        fn = _fn("foo")
        doc = build_function_document(fn, "src/utils.py", "", [], ["main"])
        assert "main" in doc


class TestBuildClassDocument:
    def test_includes_name(self):
        cls = _cls("MyClass")
        doc = build_class_document(cls, "src/myclass.py", "")
        assert "MyClass" in doc

    def test_includes_docstring(self):
        cls = _cls("Foo", docstring="A useful data container.")
        doc = build_class_document(cls, "src/foo.py", "")
        assert "data container" in doc

    def test_includes_method_names(self):
        methods = [MethodSignature(name="parse", parameters=[]), MethodSignature(name="render", parameters=[])]
        cls = _cls("Foo", methods=methods)
        doc = build_class_document(cls, "src/foo.py", "")
        assert "parse" in doc
        assert "render" in doc
