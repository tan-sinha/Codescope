from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.utils.storage import get_inventory
from app.utils.graph_builder import build_import_graph, build_rooted_call_graph

router = APIRouter()


@router.get("/graph/{owner}/{repo}")
def get_graph(
    owner: str,
    repo: str,
    type: str = Query(..., description="'imports' or 'calls'"),
    root: Optional[str] = Query(None, description="Root node for call graph (e.g. 'Flask.route')"),
    depth: int = Query(3, ge=1, le=10, description="BFS depth for call graph"),
):
    repo_key = f"{owner}/{repo}"
    data = get_inventory(repo_key)

    if not data:
        raise HTTPException(status_code=404, detail="Repository not indexed")

    if type == "imports":
        return build_import_graph(data)

    if type == "calls":
        if not root:
            raise HTTPException(
                status_code=400,
                detail="'root' parameter is required for type=calls",
            )
        result = build_rooted_call_graph(data, root, depth)
        if not result["nodes"]:
            raise HTTPException(
                status_code=404,
                detail=f"No call graph found for root '{root}'",
            )
        return result

    raise HTTPException(
        status_code=400,
        detail="'type' must be 'imports' or 'calls'",
    )
