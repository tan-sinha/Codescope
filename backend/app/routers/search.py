from fastapi import APIRouter, HTTPException

from app.models.requests import SearchRequest

from app.utils.storage import get_inventory
from app.utils.search.persistence import load_indexes
from app.utils.search.search_engine import hybrid_search

router = APIRouter()


@router.post("/search")
def search(request: SearchRequest):
    repo_key = (
        f"{request.owner}/{request.repo}"
    )

    knowledge_store = get_inventory(
        repo_key
    )

    if not knowledge_store:
        raise HTTPException(
            status_code=404,
            detail="Repository not indexed",
        )

    indexes = load_indexes(
        request.owner,
        request.repo,
    )

    if not indexes:
        raise HTTPException(
            status_code=404,
            detail="Search indexes not found",
        )

    results = hybrid_search(
        query=request.query,
        limit=request.limit,
        mode=request.mode,
        knowledge_store=knowledge_store,
        **indexes,
    )

    return {
        "results": results
    }