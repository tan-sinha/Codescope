from rank_bm25 import BM25Okapi

from app.utils.search.tokenizer import (
    code_tokenize,
)


def build_bm25_index(
    documents,
):
    corpus = [
        code_tokenize(doc)
        for doc in documents
    ]

    bm25 = BM25Okapi(
        corpus
    )

    return bm25, corpus