from app.utils.module_builder import build_module
from app.data.function import FunctionInfo, Parameter
from app.data.class_info import ClassInfo
from app.data.import_info import ImportInfo


def _fn(name):
    return FunctionInfo(name=name)


def _cls(name):
    return ClassInfo(name=name)


def _imp(module):
    return ImportInfo(module=module)


class TestBuildModule:
    def test_path_stored(self):
        m = build_module("src/foo.py", [], [], [])
        assert m.path == "src/foo.py"

    def test_function_names_collected(self):
        fns = [_fn("foo"), _fn("bar")]
        m = build_module("f.py", fns, [], [])
        assert m.functions == ["foo", "bar"]

    def test_class_names_collected(self):
        classes = [_cls("A"), _cls("B")]
        m = build_module("f.py", [], classes, [])
        assert m.classes == ["A", "B"]

    def test_import_modules_collected(self):
        imports = [_imp("os"), _imp("sys")]
        m = build_module("f.py", [], [], imports)
        assert "os" in m.imports
        assert "sys" in m.imports

    def test_empty_file(self):
        m = build_module("empty.py", [], [], [])
        assert m.functions == []
        assert m.classes == []
        assert m.imports == []
