"""
Integration tests for the full parse pipeline:
clone -> inventory -> parse -> index -> store
Runs against local fixture files — no network calls.
"""
import tempfile
from pathlib import Path

import pytest

from app.utils.inventory import build_python_inventory
from app.utils.parsers.function_extractor import extract_functions
from app.utils.parsers.class_extractor import extract_classes
from app.utils.parsers.import_extractor import extract_imports
from app.utils.parsers.call_graph_extractor import build_call_graph
from app.utils.module_builder import build_module
from app.utils.summarizer import generate_function_summaries, generate_module_summary
from tree_sitter import Parser, Language
import tree_sitter_python as tspython

PARSER = Parser(Language(tspython.language()))

FIXTURE_A = """\
import os
from pathlib import Path

def read_file(path: str) -> str:
    \"\"\"Read a file and return its contents.\"\"\"
    return Path(path).read_text()

def write_file(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)

class FileManager:
    \"\"\"Manages file operations.\"\"\"

    def __init__(self, base_dir: str):
        self.base_dir = base_dir

    @property
    def root(self) -> Path:
        return Path(self.base_dir)

    def read(self, name: str) -> str:
        return read_file(str(self.root / name))
"""

FIXTURE_B = """\
from .file_utils import read_file, FileManager

class CachedManager(FileManager):
    \"\"\"Extends FileManager with caching.\"\"\"

    def __init__(self, base_dir: str):
        super().__init__(base_dir)
        self._cache = {}

    def invalidate(self) -> None:
        self._cache.clear()

    def read(self, name: str) -> str:
        if name not in self._cache:
            self._cache[name] = super().read(name)
        return self._cache[name]

    def refresh(self, name: str) -> str:
        self.invalidate()
        return self.read(name)

def clear_cache(manager: CachedManager) -> None:
    manager._cache.clear()
"""


@pytest.fixture(scope="module")
def repo_path():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "pkg").mkdir()
        (root / "pkg" / "__init__.py").write_text("")
        (root / "pkg" / "file_utils.py").write_text(FIXTURE_A)
        (root / "pkg" / "cached.py").write_text(FIXTURE_B)
        yield root


@pytest.fixture(scope="module")
def indexed(repo_path):
    files = build_python_inventory(repo_path)

    file_trees = {}
    modules = {}
    functions_index = {}
    classes_index = {}
    imports_index = {}

    for file_path in files:
        raw = (repo_path / file_path).read_bytes()
        tree = PARSER.parse(raw)

        file_trees[file_path] = {"tree": tree, "bytes": raw}

        fns = extract_functions(tree.root_node, raw)
        classes = extract_classes(tree.root_node, raw)
        imports = extract_imports(tree.root_node, raw, file_path)

        generate_function_summaries(fns)
        module = build_module(file_path, fns, classes, imports)
        generate_module_summary(module)

        modules[file_path] = module
        imports_index[file_path] = imports

        for fn in fns:
            functions_index[f"{file_path}::{fn.name}"] = fn
        for cls in classes:
            classes_index[f"{file_path}::{cls.name}"] = cls

    call_graph = build_call_graph(file_trees, functions_index, imports_index)

    return {
        "files": files,
        "modules": modules,
        "functions": functions_index,
        "classes": classes_index,
        "imports": imports_index,
        "call_graph": call_graph,
    }


class TestInventory:
    def test_finds_python_files(self, repo_path):
        files = build_python_inventory(repo_path)
        names = {Path(f).name for f in files}
        assert "file_utils.py" in names
        assert "cached.py" in names

    def test_returns_relative_paths(self, repo_path):
        files = build_python_inventory(repo_path)
        for f in files:
            assert not Path(f).is_absolute()


class TestFunctionParsing:
    def test_extracts_top_level_functions(self, indexed):
        keys = list(indexed["functions"].keys())
        names = {k.split("::")[1] for k in keys}
        assert "read_file" in names
        assert "write_file" in names

    def test_function_has_params(self, indexed):
        fn = next(
            f for f in indexed["functions"].values() if f.name == "read_file"
        )
        assert any(p.name == "path" for p in fn.parameters)

    def test_function_has_return_type(self, indexed):
        fn = next(
            f for f in indexed["functions"].values() if f.name == "read_file"
        )
        assert fn.return_type == "str"

    def test_function_has_docstring(self, indexed):
        fn = next(
            f for f in indexed["functions"].values() if f.name == "read_file"
        )
        assert fn.docstring is not None
        assert "Read a file" in fn.docstring

    def test_function_has_summary(self, indexed):
        fn = next(
            f for f in indexed["functions"].values() if f.name == "read_file"
        )
        assert fn.summary is not None

    def test_function_has_source_code(self, indexed):
        fn = next(
            f for f in indexed["functions"].values() if f.name == "read_file"
        )
        assert "def read_file" in fn.source_code


class TestClassParsing:
    def test_extracts_classes(self, indexed):
        names = {k.split("::")[1] for k in indexed["classes"]}
        assert "FileManager" in names
        assert "CachedManager" in names

    def test_class_has_docstring(self, indexed):
        cls = next(
            c for c in indexed["classes"].values() if c.name == "FileManager"
        )
        assert cls.docstring is not None
        assert "Manages" in cls.docstring

    def test_class_base_classes(self, indexed):
        cls = next(
            c for c in indexed["classes"].values() if c.name == "CachedManager"
        )
        assert "FileManager" in cls.base_classes

    def test_class_plain_methods(self, indexed):
        cls = next(
            c for c in indexed["classes"].values() if c.name == "FileManager"
        )
        method_names = [m.name for m in cls.methods]
        assert "__init__" in method_names
        assert "read" in method_names

    def test_class_decorated_methods(self, indexed):
        cls = next(
            c for c in indexed["classes"].values() if c.name == "FileManager"
        )
        method_names = [m.name for m in cls.methods]
        assert "root" in method_names


class TestImportParsing:
    def test_absolute_imports_extracted(self, indexed):
        all_imports = [
            imp
            for imps in indexed["imports"].values()
            for imp in imps
        ]
        modules = {i.module for i in all_imports}
        assert "os" in modules

    def test_relative_imports_flagged(self, indexed):
        all_imports = [
            imp
            for imps in indexed["imports"].values()
            for imp in imps
        ]
        relative = [i for i in all_imports if i.is_relative]
        assert len(relative) > 0

    def test_from_import_names(self, indexed):
        all_imports = [
            imp
            for imps in indexed["imports"].values()
            for imp in imps
        ]
        path_imports = [i for i in all_imports if i.module == "pathlib"]
        assert any("Path" in i.names for i in path_imports)


class TestModuleInfo:
    def test_module_summary_generated(self, indexed):
        for module in indexed["modules"].values():
            assert module.summary is not None

    def test_module_lists_functions(self, indexed):
        file_utils_module = next(
            m for path, m in indexed["modules"].items()
            if "file_utils" in path
        )
        assert "read_file" in file_utils_module.functions
        assert "write_file" in file_utils_module.functions

    def test_module_lists_classes(self, indexed):
        file_utils_module = next(
            m for path, m in indexed["modules"].items()
            if "file_utils" in path
        )
        assert "FileManager" in file_utils_module.classes


class TestCallGraph:
    def test_call_graph_has_edges(self, indexed):
        assert len(indexed["call_graph"]["edges"]) > 0

    def test_call_graph_has_stats(self, indexed):
        stats = indexed["call_graph"]["stats"]
        assert "overall" in stats
        assert stats["overall"].total_calls >= 0

    def test_self_calls_resolved(self, indexed):
        edges = indexed["call_graph"]["edges"]
        # CachedManager.refresh calls self.invalidate() and self.read()
        self_resolved = [
            e for e in edges
            if e.resolved and "CachedManager" in (e.callee or "")
        ]
        assert len(self_resolved) > 0
