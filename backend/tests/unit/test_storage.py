import pytest
from app.utils.storage import save_inventory, get_inventory, knowledge_store


@pytest.fixture(autouse=True)
def clear_store():
    knowledge_store.clear()
    yield
    knowledge_store.clear()


class TestStorage:
    def test_save_and_retrieve(self):
        payload = {"files": ["a.py"], "functions": {}}
        save_inventory("owner/repo", payload)
        result = get_inventory("owner/repo")
        assert result == payload

    def test_missing_key_returns_none(self):
        assert get_inventory("nobody/nothing") is None

    def test_overwrite(self):
        save_inventory("owner/repo", {"v": 1})
        save_inventory("owner/repo", {"v": 2})
        assert get_inventory("owner/repo")["v"] == 2

    def test_multiple_repos_isolated(self):
        save_inventory("a/x", {"data": "x"})
        save_inventory("b/y", {"data": "y"})
        assert get_inventory("a/x")["data"] == "x"
        assert get_inventory("b/y")["data"] == "y"

    def test_stored_directly_not_wrapped(self):
        payload = {"functions": {"f": object()}, "classes": {}}
        save_inventory("owner/repo", payload)
        result = get_inventory("owner/repo")
        assert "functions" in result
        assert "classes" in result
