from app.utils.parsers.import_extractor import extract_imports


class TestAbsoluteImports:
    def test_simple_import(self, parse):
        root, src = parse("import os")
        imports = extract_imports(root, src, "myfile.py")
        assert len(imports) == 1
        assert imports[0].module == "os"
        assert imports[0].is_relative is False

    def test_multi_import(self, parse):
        root, src = parse("import os, sys")
        imports = extract_imports(root, src, "myfile.py")
        modules = {i.module for i in imports}
        assert "os" in modules
        assert "sys" in modules

    def test_dotted_import(self, parse):
        root, src = parse("import os.path")
        imports = extract_imports(root, src, "myfile.py")
        assert imports[0].module == "os.path"

    def test_aliased_import(self, parse):
        root, src = parse("import numpy as np")
        imports = extract_imports(root, src, "myfile.py")
        assert len(imports) == 1
        assert imports[0].module == "numpy"
        assert imports[0].aliases.get("np") == "numpy"


class TestFromImports:
    def test_from_import(self, parse):
        root, src = parse("from os import path")
        imports = extract_imports(root, src, "myfile.py")
        assert len(imports) == 1
        assert imports[0].module == "os"
        assert "path" in imports[0].names
        assert imports[0].is_relative is False

    def test_from_import_multiple_names(self, parse):
        root, src = parse("from os.path import join, exists")
        imports = extract_imports(root, src, "myfile.py")
        assert len(imports) == 1
        assert "join" in imports[0].names
        assert "exists" in imports[0].names

    def test_from_import_aliased(self, parse):
        root, src = parse("from typing import Optional as Opt")
        imports = extract_imports(root, src, "myfile.py")
        assert imports[0].aliases.get("Opt") == "Optional"

    def test_relative_import_single_dot(self, parse):
        root, src = parse("from . import utils")
        imports = extract_imports(root, src, "pkg/module.py")
        assert len(imports) == 1
        assert imports[0].is_relative is True
        assert imports[0].relative_level == 1

    def test_relative_import_double_dot(self, parse):
        root, src = parse("from .. import base")
        imports = extract_imports(root, src, "pkg/sub/module.py")
        assert imports[0].is_relative is True
        assert imports[0].relative_level == 2

    def test_relative_import_with_module(self, parse):
        root, src = parse("from .utils import helper")
        imports = extract_imports(root, src, "pkg/module.py")
        assert imports[0].is_relative is True
        assert "helper" in imports[0].names


class TestMixedImports:
    def test_multiple_statements(self, parse):
        src = "import os\nfrom sys import argv\nimport json"
        root, src_bytes = parse(src)
        imports = extract_imports(root, src_bytes, "myfile.py")
        modules = {i.module for i in imports}
        assert "os" in modules
        assert "sys" in modules
        assert "json" in modules

    def test_no_imports(self, parse):
        root, src = parse("x = 1\ny = 2")
        imports = extract_imports(root, src, "myfile.py")
        assert imports == []
