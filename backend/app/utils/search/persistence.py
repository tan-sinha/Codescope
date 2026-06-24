import pickle
from pathlib import Path

import faiss
from rank_bm25 import BM25Okapi


def repo_dir(owner, repo):
    path = Path("data") / f"{owner}_{repo}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_indexes(owner, repo, faiss_index, bm25_corpus, id_mapping):
    path = repo_dir(owner, repo)

    faiss.write_index(faiss_index, str(path / "faiss.index"))

    with open(path / "bm25_corpus.pkl", "wb") as f:
        pickle.dump(bm25_corpus, f)

    with open(path / "mapping.pkl", "wb") as f:
        pickle.dump(id_mapping, f)


def load_indexes(owner, repo):
    path = repo_dir(owner, repo)

    faiss_path = path / "faiss.index"
    bm25_path = path / "bm25_corpus.pkl"
    mapping_path = path / "mapping.pkl"

    if not (faiss_path.exists() and bm25_path.exists() and mapping_path.exists()):
        return None

    faiss_index = faiss.read_index(str(faiss_path))

    with open(bm25_path, "rb") as f:
        corpus = pickle.load(f)

    with open(mapping_path, "rb") as f:
        mapping = pickle.load(f)

    bm25 = BM25Okapi(corpus)

    return {
        "faiss_index": faiss_index,
        "bm25": bm25,
        "mapping": mapping,
    }
