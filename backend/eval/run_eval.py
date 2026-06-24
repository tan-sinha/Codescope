#!/usr/bin/env python3
"""
Search quality + call graph evaluator for Codescope.

Usage (Flask must be indexed first):
  python eval/run_eval.py
  python eval/run_eval.py --base-url http://localhost:8000 --owner pallets --repo flask
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import httpx

BASE_URL = "http://127.0.0.1:8000"
OWNER = "pallets"
REPO = "flask"

CALL_GRAPH_TARGETS = [
    "Flask.dispatch_request",
    "Flask.full_dispatch_request",
    "Flask.wsgi_app",
    "Flask.add_url_rule",
    "Flask.register_blueprint",
    "RequestContext.push",
    "RequestContext.match_request",
    "render_template",
    "ScriptInfo.load_app",
    "Flask.handle_exception",
]


# ---------------------------------------------------------------------------
# Metric helpers
# ---------------------------------------------------------------------------

def flatten_results(grouped: list, limit: int = 10) -> list[str]:
    flat = []
    for group in grouped:
        for item in group["items"]:
            flat.append(item["name"])
    return flat[:limit]


def precision_at_k(names: list[str], relevant: set, k: int) -> float:
    return sum(1 for n in names[:k] if n in relevant) / k


def recall_at_k(names: list[str], relevant: set, k: int) -> float:
    if not relevant:
        return 0.0
    return sum(1 for n in names[:k] if n in relevant) / len(relevant)


def mrr(names: list[str], relevant: set) -> float:
    return next((1.0 / (i + 1) for i, n in enumerate(names) if n in relevant), 0.0)


def avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


# ---------------------------------------------------------------------------
# Search evaluation
# ---------------------------------------------------------------------------

def run_search_eval(client: httpx.Client, dataset: list, modes: list[str], owner: str, repo: str) -> dict:
    """Run all queries for all modes, return nested metrics dict."""
    categories = sorted({q["category"] for q in dataset})
    results: dict = {mode: {"all": [], "by_category": {c: [] for c in categories}} for mode in modes}

    for q in dataset:
        query = q["query"]
        relevant = set(q["relevant_functions"])
        cat = q["category"]

        for mode in modes:
            try:
                resp = client.post(
                    "/search",
                    json={"owner": owner, "repo": repo, "query": query, "limit": 10, "mode": mode},
                    timeout=30,
                )
                resp.raise_for_status()
                grouped = resp.json().get("results", [])
            except Exception as e:
                print(f"  WARN: {mode} / '{query}' failed: {e}", file=sys.stderr)
                grouped = []

            names = flatten_results(grouped, limit=10)
            metrics = {
                "p5":  precision_at_k(names, relevant, 5),
                "r10": recall_at_k(names, relevant, 10),
                "mrr": mrr(names, relevant),
            }
            results[mode]["all"].append(metrics)
            results[mode]["by_category"][cat].append(metrics)

    return results


def aggregate(metric_list: list[dict]) -> dict:
    return {
        "p5":  avg([m["p5"]  for m in metric_list]),
        "r10": avg([m["r10"] for m in metric_list]),
        "mrr": avg([m["mrr"] for m in metric_list]),
    }


# ---------------------------------------------------------------------------
# Call graph evaluation
# ---------------------------------------------------------------------------

def run_call_graph_eval(client: httpx.Client, owner: str, repo: str) -> dict:
    total = resolved = unresolved = not_found = 0

    for target in CALL_GRAPH_TARGETS:
        try:
            resp = client.get(
                f"/graph/{owner}/{repo}",
                params={"type": "calls", "root": target, "depth": 1},
                timeout=30,
            )
            if resp.status_code == 404:
                not_found += 1
                continue
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"  WARN: call graph for '{target}' failed: {e}", file=sys.stderr)
            not_found += 1
            continue

        edges = data.get("edges", [])
        total += len(edges)
        for edge in edges:
            to_node = next((n for n in data["nodes"] if n["id"] == edge["to"]), None)
            if to_node and to_node["type"] != "external":
                resolved += 1
            else:
                unresolved += 1

    return {
        "functions_evaluated": len(CALL_GRAPH_TARGETS),
        "not_found": not_found,
        "total_edges": total,
        "resolved_edges": resolved,
        "unresolved_edges": unresolved,
        "resolution_rate": round(resolved / total * 100, 1) if total else 0.0,
    }


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------

def render_report(search_results: dict, cg_stats: dict, modes: list[str], owner: str, repo: str) -> str:
    lines = [
        f"## Codescope Search Quality Evaluation — {owner}/{repo}",
        f"_Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}_",
        "",
        "### Overall Metrics (30 queries)",
        "",
        "| Mode   | P@5  | R@10 | MRR  |",
        "|--------|------|------|------|",
    ]

    for mode in modes:
        agg = aggregate(search_results[mode]["all"])
        lines.append(f"| {mode:<6} | {agg['p5']:.2f} | {agg['r10']:.2f} | {agg['mrr']:.2f} |")

    lines += ["", "### By Category (P@5)", ""]
    categories = sorted(search_results[modes[0]]["by_category"].keys())
    header = "| Category    | " + " | ".join(f"{m} P@5" for m in modes) + " |"
    sep    = "|-------------|" + "|".join("-" * (len(m) + 6) for m in modes) + "|"
    lines += [header, sep]

    for cat in categories:
        row = f"| {cat:<11} | "
        row += " | ".join(
            f"{aggregate(search_results[m]['by_category'][cat])['p5']:.2f}{'':>{len(m)+2}}"
            for m in modes
        )
        row += " |"
        lines.append(row)

    lines += [
        "",
        "### Call Graph Quality",
        "",
        "| Metric                | Value |",
        "|-----------------------|-------|",
        f"| Functions evaluated   | {cg_stats['functions_evaluated']} |",
        f"| Not found in index    | {cg_stats['not_found']} |",
        f"| Total edges           | {cg_stats['total_edges']} |",
        f"| Resolved edges        | {cg_stats['resolved_edges']} |",
        f"| Unresolved edges      | {cg_stats['unresolved_edges']} |",
        f"| Resolution rate       | {cg_stats['resolution_rate']}% |",
    ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=BASE_URL)
    parser.add_argument("--owner", default=OWNER)
    parser.add_argument("--repo", default=REPO)
    args = parser.parse_args()

    owner = args.owner
    repo = args.repo

    dataset_path = Path(__file__).parent / "golden_dataset.json"
    dataset = json.loads(dataset_path.read_text())

    modes = ["hybrid", "bm25", "faiss"]

    print(f"Evaluating search quality against {owner}/{repo} ({len(dataset)} queries, {len(modes)} modes)...")

    with httpx.Client(base_url=args.base_url) as client:
        check = client.get(f"/explore/{owner}/{repo}")
        if check.status_code != 200:
            print(f"ERROR: {owner}/{repo} is not indexed. Run POST /index first.", file=sys.stderr)
            sys.exit(1)

        print("Running search evaluation...")
        search_results = run_search_eval(client, dataset, modes, owner, repo)

        print("Running call graph evaluation...")
        cg_stats = run_call_graph_eval(client, owner, repo)

    report = render_report(search_results, cg_stats, modes, owner, repo)

    print("\n" + report)

    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = results_dir / f"report_{ts}.md"
    report_path.write_text(report)
    print(f"\nReport saved to {report_path}")


if __name__ == "__main__":
    main()
