import pytest
from app.utils.parsers.function_extractor import extract_functions


class TestExtractFunctions:
    def test_simple_function(self, parse):
        root, src = parse("def foo(): pass")
        fns = extract_functions(root, src)
        assert len(fns) == 1
        assert fns[0].name == "foo"

    def test_function_with_typed_params(self, parse):
        root, src = parse("def add(x: int, y: int) -> int: return x + y")
        fns = extract_functions(root, src)
        assert len(fns) == 1
        fn = fns[0]
        assert fn.name == "add"
        assert fn.return_type == "int"
        param_names = [p.name for p in fn.parameters]
        assert "x" in param_names
        assert "y" in param_names
        assert fn.parameters[0].annotation == "int"

    def test_function_with_default_param(self, parse):
        root, src = parse("def greet(name, greeting='Hello'): pass")
        fns = extract_functions(root, src)
        assert len(fns) == 1
        param_names = [p.name for p in fns[0].parameters]
        assert "name" in param_names
        assert "greeting" in param_names

    def test_function_with_typed_default_param(self, parse):
        root, src = parse('def f(x: str = "a"): pass')
        fns = extract_functions(root, src)
        assert len(fns) == 1
        p = fns[0].parameters[0]
        assert p.name == "x"
        assert p.annotation == "str"

    def test_function_with_args_kwargs(self, parse):
        root, src = parse("def f(*args, **kwargs): pass")
        fns = extract_functions(root, src)
        assert len(fns) == 1
        param_names = [p.name for p in fns[0].parameters]
        assert "*args" in param_names
        assert "**kwargs" in param_names

    def test_function_with_docstring(self, parse):
        src = '''
def described():
    """Does something useful."""
    pass
'''
        root, src_bytes = parse(src)
        fns = extract_functions(root, src_bytes)
        assert len(fns) == 1
        assert fns[0].docstring == "Does something useful."

    def test_function_with_decorator(self, parse):
        src = '''
@staticmethod
def helper(): pass
'''
        root, src_bytes = parse(src)
        fns = extract_functions(root, src_bytes)
        assert len(fns) == 1
        assert any("staticmethod" in d for d in fns[0].decorators)

    def test_extracts_source_code(self, parse):
        src = "def foo(): pass"
        root, src_bytes = parse(src)
        fns = extract_functions(root, src_bytes)
        assert "def foo" in fns[0].source_code

    def test_captures_line_numbers(self, parse):
        src = "\ndef foo(): pass\n"
        root, src_bytes = parse(src)
        fns = extract_functions(root, src_bytes)
        assert fns[0].start_line == 2

    def test_multiple_functions(self, parse):
        src = "def a(): pass\ndef b(): pass\ndef c(): pass"
        root, src_bytes = parse(src)
        fns = extract_functions(root, src_bytes)
        assert len(fns) == 3
        names = {f.name for f in fns}
        assert names == {"a", "b", "c"}

    def test_nested_function_extracted(self, parse):
        src = '''
def outer():
    def inner():
        pass
'''
        root, src_bytes = parse(src)
        fns = extract_functions(root, src_bytes)
        names = {f.name for f in fns}
        assert "outer" in names
        assert "inner" in names

    def test_empty_module(self, parse):
        root, src = parse("")
        assert extract_functions(root, src) == []
