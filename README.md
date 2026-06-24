# Codescope

Code intelligence API — index GitHub repos and search/explore their structure via AST parsing, semantic embeddings, and call graph analysis.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/index` | Clone and index a GitHub repo |
| GET | `/explore/{owner}/{repo}` | List all indexed files, functions, classes |
| GET | `/explore/{owner}/{repo}/function/{name}` | Get function details |
| GET | `/explore/{owner}/{repo}/class/{name}` | Get class details |
| GET | `/explore/{owner}/{repo}/module/{path}` | Get module info |
| GET | `/explore/{owner}/{repo}/file/{path}` | Get all symbols in a file |
| POST | `/search` | Hybrid semantic + keyword search |
| GET | `/graph/{owner}/{repo}?type=imports` | Import dependency graph |
| GET | `/graph/{owner}/{repo}?type=calls&root=X&depth=N` | Call graph rooted at X |

## Search Modes

`POST /search` accepts `mode`: `"hybrid"` (default), `"bm25"`, or `"faiss"`.

## Search Quality Evaluation

Evaluated against **pallets/flask** (30 golden queries: 10 exact-match, 10 conceptual, 10 location).

### Overall Metrics

| Mode   | P@5  | R@10 | MRR  |
|--------|------|------|------|
| hybrid | —    | —    | —    |
| bm25   | —    | —    | —    |
| faiss  | —    | —    | —    |

### By Category (P@5)

| Category    | hybrid | bm25 | faiss |
|-------------|--------|------|-------|
| exact_match | —      | —    | —     |
| conceptual  | —      | —    | —     |
| location    | —      | —    | —     |

### Call Graph Quality (pallets/flask)

| Metric            | Value |
|-------------------|-------|
| Functions sampled | 10    |
| Total edges       | —     |
| Resolved edges    | —     |
| Resolution rate   | —%    |

_Run `python eval/run_eval.py` with Flask indexed to populate these numbers._

## Running

```bash
cd backend
source ../codescope-venv/bin/activate
uvicorn app.main:app --reload
```

## Tests

```bash
cd backend
pytest tests/ -q
```

## Evaluation

```bash
# Index Flask first
curl -X POST http://localhost:8000/index -H "Content-Type: application/json" \
  -d '{"owner":"pallets","repo":"flask"}'

# Run eval
python eval/run_eval.py
```
