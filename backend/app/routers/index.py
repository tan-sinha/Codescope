from fastapi import APIRouter, HTTPException

from models.requests import IndexRequest
from utils.git_utils import clone_repo
from utils.inventory import build_python_inventory
from utils.storage import save_inventory
from utils.status import set_status

router = APIRouter()


@router.post("/index")
def index_repo(request: IndexRequest):

    repo_key = f"{request.owner}/{request.repo}"

    try:
        set_status(repo_key, "indexing")

        repo_path = clone_repo(
            request.owner,
            request.repo
        )

        files = build_python_inventory(repo_path)

        save_inventory(repo_key, files)

        set_status(repo_key, "ready")

        return {
            "owner": request.owner,
            "repo": request.repo,
            "file_count": len(files),
            "files": files
        }

    except Exception as e:
        set_status(repo_key, "not_indexed")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )