import re

CAMEL_CASE_RE = re.compile(
    r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)"
)

STOPWORDS = {
    "what", "does", "do", "the", "is", "a", "an",
    "how", "why", "where", "when", "which", "for",
    "in", "of", "to", "and", "or", "not", "this",
    "i", "me", "my", "we", "it", "its", "be", "are",
    "was", "were", "has", "have", "had", "can", "will",
}


def split_camel_case(token: str):
    return CAMEL_CASE_RE.findall(token)


def code_tokenize(text: str):
    pieces = re.split(r"[._\s():,\[\]{}<>/=+-]+", text)

    tokens = []

    for piece in pieces:
        piece = piece.strip()

        if not piece:
            continue

        camel = split_camel_case(piece)

        if camel:
            tokens.extend(t.lower() for t in camel)
        else:
            tokens.append(piece.lower())

    return [t for t in tokens if t not in STOPWORDS]
