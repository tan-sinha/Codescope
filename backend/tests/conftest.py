import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from tree_sitter import Parser, Language
import tree_sitter_python as tspython


@pytest.fixture(scope="session")
def py_parser():
    return Parser(Language(tspython.language()))


@pytest.fixture
def parse(py_parser):
    def _parse(source: str):
        src_bytes = source.encode("utf-8")
        tree = py_parser.parse(src_bytes)
        return tree.root_node, src_bytes
    return _parse
