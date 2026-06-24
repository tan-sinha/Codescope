from app.utils.search.tokenizer import code_tokenize, split_camel_case


class TestSplitCamelCase:
    def test_simple_camel(self):
        assert split_camel_case("camelCase") == ["camel", "Case"]

    def test_pascal_case(self):
        assert split_camel_case("MyClassName") == ["My", "Class", "Name"]

    def test_all_upper(self):
        assert split_camel_case("HTTP") == ["HTTP"]

    def test_single_word(self):
        assert split_camel_case("simple") == ["simple"]

    def test_empty(self):
        assert split_camel_case("") == []


class TestCodeTokenize:
    def test_splits_on_dots(self):
        tokens = code_tokenize("os.path.join")
        assert "os" in tokens
        assert "path" in tokens
        assert "join" in tokens

    def test_lowercases(self):
        tokens = code_tokenize("ParseRequest")
        assert "parse" in tokens
        assert "request" in tokens

    def test_splits_underscores(self):
        tokens = code_tokenize("build_call_graph")
        assert "build" in tokens
        assert "call" in tokens
        assert "graph" in tokens

    def test_strips_punctuation(self):
        tokens = code_tokenize("def foo(x, y):")
        assert "def" in tokens
        assert "foo" in tokens
        assert "x" in tokens
        assert "y" in tokens

    def test_empty_string(self):
        assert code_tokenize("") == []

    def test_mixed(self):
        tokens = code_tokenize("parseHTTPRequest")
        assert "parse" in tokens
        assert "http" in tokens
        assert "request" in tokens
