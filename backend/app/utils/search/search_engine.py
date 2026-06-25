from collections import defaultdict
from pathlib import Path

from app.utils.search.faiss_index import model
from app.utils.search.tokenizer import code_tokenize

MIN_SCORE = 0.015          # fix 4: was 0.020
FAISS_WEIGHT = 2.0         # fix 1: FAISS weighted 2x over BM25 in RRF


def bm25_search(query, bm25, mapping, limit=20):
    query_tokens = code_tokenize(query)
    scores = bm25.get_scores(query_tokens)
    ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
    return [(mapping[idx], score) for idx, score in ranked[:limit]]


def faiss_search(query, faiss_index, mapping, limit=20):
    embedding = model.encode([query], normalize_embeddings=True)
    distances, indices = faiss_index.search(embedding.astype("float32"), limit)

    results = []
    for score, idx in zip(distances[0], indices[0]):
        if idx == -1:
            continue
        results.append((mapping[idx], float(score)))

    return results


def reciprocal_rank_fusion(bm25_results, faiss_results, k=60):
    # fix 1: FAISS contributes FAISS_WEIGHT× more than BM25
    scores = defaultdict(float)

    for rank, (doc_id, _) in enumerate(bm25_results):
        scores[doc_id] += 1.0 / (k + rank + 1)

    for rank, (doc_id, _) in enumerate(faiss_results):
        scores[doc_id] += FAISS_WEIGHT / (k + rank + 1)

    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


def _detect_file_stem(query: str) -> str | None:
    for token in query.split():
        if token.endswith(".py"):
            return token[:-3]
    return None


def _apply_file_boost(fused, file_stem: str, boost: float = 3.0):
    boosted = []
    for identifier, score in fused:
        file_path = identifier.split("::")[0]
        if Path(file_path).stem == file_stem:
            score *= boost
        boosted.append((identifier, score))
    return sorted(boosted, key=lambda x: x[1], reverse=True)


def _pin_exact_match(flat: list, query: str) -> list:
    # fix 2: if the query exactly matches a result's name, move it to position 0
    query_norm = query.strip().lower()
    for i, r in enumerate(flat):
        if r["name"].lower() == query_norm:
            return [flat[i]] + flat[:i] + flat[i + 1:]
    return flat


def _short_summary(text: str | None, max_chars: int = 300) -> str | None:
    if not text:
        return None
    first_para = text.split("\n\n")[0].strip()
    return first_para[:max_chars]


def build_result(identifier, score, knowledge_store, owner, repo):
    fn = knowledge_store["functions"].get(identifier)

    if fn:
        file_path = identifier.split("::")[0]
        preview = "\n".join(fn.source_code.splitlines()[:20])
        return {
            "type": "function",
            "name": fn.name,
            "file": file_path,
            "lines": [fn.start_line, fn.end_line],
            "signature": (
                f"{fn.name}("
                + ", ".join(p.name for p in fn.parameters)
                + ")"
            ),
            "summary": fn.summary,
            "source_preview": preview,
            "github_url": (
                f"https://github.com/{owner}/{repo}"
                f"/blob/main/{file_path}"
                f"#L{fn.start_line}-L{fn.end_line}"
            ),
            "relevance_score": round(score, 4),
        }

    cls = knowledge_store["classes"].get(identifier)

    if cls:
        file_path = identifier.split("::")[0]
        return {
            "type": "class",
            "name": cls.name,
            "file": file_path,
            "lines": [cls.start_line, cls.end_line],
            "summary": _short_summary(cls.docstring),
            "relevance_score": round(score, 4),
        }

    # Method key: file_path::ClassName.method_name
    parts = identifier.split("::", 1)
    if len(parts) == 2:
        file_path, rest = parts
        if "." in rest:
            class_name, method_name = rest.split(".", 1)
            class_key = f"{file_path}::{class_name}"
            cls = knowledge_store["classes"].get(class_key)
            if cls:
                method = next(
                    (m for m in cls.methods if m.name == method_name), None
                )
                if method:
                    return {
                        "type": "method",
                        "name": f"{class_name}.{method_name}",
                        "class": class_name,
                        "file": file_path,
                        "signature": (
                            f"{method_name}("
                            + ", ".join(method.parameters)
                            + ")"
                        ),
                        "return_type": method.return_type,
                        "github_url": (
                            f"https://github.com/{owner}/{repo}"
                            f"/blob/main/{file_path}"
                        ),
                        "relevance_score": round(score, 4),
                    }

    return None


def _deduplicate(results):
    """Drop method results that duplicate an already-present function with the same base name in the same file."""
    function_keys = {
        (r["file"], r["name"])
        for r in results
        if r["type"] == "function"
    }
    deduped = []
    for r in results:
        if r["type"] == "method":
            base = r["name"].split(".")[-1]
            if (r["file"], base) in function_keys:
                continue
        deduped.append(r)
    return deduped


def _group_by_file(results):
    """Group results by file, ordered by each file's highest relevance score.
    Items within each group are sorted by individual relevance_score descending."""  # fix 3
    groups: dict[str, list] = {}
    max_scores: dict[str, float] = {}

    for r in results:
        f = r["file"]
        groups.setdefault(f, []).append(r)
        max_scores[f] = max(max_scores.get(f, 0.0), r["relevance_score"])

    return [
        {
            "file": f,
            "relevance_score": round(max_scores[f], 4),
            "items": sorted(groups[f], key=lambda r: r["relevance_score"], reverse=True),  # fix 3
        }
        for f in sorted(groups, key=lambda f: max_scores[f], reverse=True)
    ]


def hybrid_search(query, knowledge_store, faiss_index, bm25, mapping, limit=10, mode="hybrid"):
    if mode == "bm25":
        fused = bm25_search(query, bm25, mapping, limit=limit * 2)
        apply_threshold = False
    elif mode == "faiss":
        fused = faiss_search(query, faiss_index, mapping, limit=limit * 2)
        apply_threshold = False
    else:
        bm25_results = bm25_search(query, bm25, mapping)
        faiss_results = faiss_search(query, faiss_index, mapping)
        fused = reciprocal_rank_fusion(bm25_results, faiss_results)
        apply_threshold = True

    file_stem = _detect_file_stem(query)
    if file_stem:
        fused = _apply_file_boost(fused, file_stem)

    repo_key = knowledge_store.get("repo_key", "/")
    owner, repo = repo_key.split("/", 1)

    flat = []
    for identifier, score in fused[:limit * 2]:
        if apply_threshold and score < MIN_SCORE:
            break
        result = build_result(identifier, score, knowledge_store, owner, repo)
        if result:
            flat.append(result)
            if len(flat) == limit:
                break

    flat = _pin_exact_match(flat, query)   # fix 2

    return _group_by_file(_deduplicate(flat))
