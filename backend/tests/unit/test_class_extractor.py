from app.utils.parsers.class_extractor import extract_classes


class TestExtractClasses:
    def test_simple_class(self, parse):
        root, src = parse("class Foo: pass")
        classes = extract_classes(root, src)
        assert len(classes) == 1
        assert classes[0].name == "Foo"

    def test_class_with_base(self, parse):
        root, src = parse("class Dog(Animal): pass")
        classes = extract_classes(root, src)
        assert classes[0].base_classes == ["Animal"]

    def test_class_with_multiple_bases(self, parse):
        root, src = parse("class C(A, B): pass")
        classes = extract_classes(root, src)
        assert set(classes[0].base_classes) == {"A", "B"}

    def test_class_with_docstring(self, parse):
        src = '''
class Documented:
    """A documented class."""
    pass
'''
        root, src_bytes = parse(src)
        classes = extract_classes(root, src_bytes)
        assert "A documented class." in classes[0].docstring

    def test_class_with_plain_method(self, parse):
        src = '''
class MyClass:
    def my_method(self):
        pass
'''
        root, src_bytes = parse(src)
        classes = extract_classes(root, src_bytes)
        assert len(classes) == 1
        method_names = [m.name for m in classes[0].methods]
        assert "my_method" in method_names

    def test_class_with_decorated_method(self, parse):
        src = '''
class MyClass:
    @property
    def value(self) -> int:
        return 42
'''
        root, src_bytes = parse(src)
        classes = extract_classes(root, src_bytes)
        method_names = [m.name for m in classes[0].methods]
        assert "value" in method_names

    def test_class_with_mixed_methods(self, parse):
        src = '''
class Service:
    def plain(self): pass

    @staticmethod
    def static_method(): pass

    @classmethod
    def from_config(cls): pass
'''
        root, src_bytes = parse(src)
        classes = extract_classes(root, src_bytes)
        assert len(classes) == 1
        method_names = [m.name for m in classes[0].methods]
        assert "plain" in method_names
        assert "static_method" in method_names
        assert "from_config" in method_names

    def test_method_return_type(self, parse):
        src = '''
class C:
    def get(self) -> str:
        return ""
'''
        root, src_bytes = parse(src)
        classes = extract_classes(root, src_bytes)
        method = classes[0].methods[0]
        assert method.return_type == "str"

    def test_method_parameters(self, parse):
        src = '''
class C:
    def add(self, x, y):
        return x + y
'''
        root, src_bytes = parse(src)
        classes = extract_classes(root, src_bytes)
        method = classes[0].methods[0]
        assert "self" in method.parameters
        assert "x" in method.parameters
        assert "y" in method.parameters

    def test_line_numbers(self, parse):
        src = "\nclass Foo:\n    pass\n"
        root, src_bytes = parse(src)
        classes = extract_classes(root, src_bytes)
        assert classes[0].start_line == 2

    def test_multiple_classes(self, parse):
        src = "class A: pass\nclass B: pass"
        root, src_bytes = parse(src)
        classes = extract_classes(root, src_bytes)
        assert len(classes) == 2
        assert {c.name for c in classes} == {"A", "B"}

    def test_empty_module(self, parse):
        root, src = parse("")
        assert extract_classes(root, src) == []
