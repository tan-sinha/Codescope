from fastapi import (
    APIRouter,
    HTTPException,
)

from app.utils.storage import (
    get_inventory,
)

router = APIRouter()


@router.get("/explore/{owner}/{repo}")
def explore_repo(owner: str, repo: str):
    repo_key = f"{owner}/{repo}"

    data = get_inventory(repo_key)

    if not data:
        raise HTTPException(
            status_code=404,
            detail="Repository not indexed",
        )

    return {
        "files": data["files"],
        "function_count": len(data["functions"]),
        "class_count": len(data["classes"]),
        "functions": list(data["functions"].keys()),
        "classes": list(data["classes"].keys()),
    }


@router.get(
    "/explore/{owner}/{repo}/function/{name}"
)
def explore_function(
    owner: str,
    repo: str,
    name: str,
):
    repo_key = f"{owner}/{repo}"

    data = get_inventory(
        repo_key
    )

    if not data:
        raise HTTPException(
            status_code=404,
            detail="Repository not indexed",
        )

    for key, fn in (
        data["functions"].items()
    ):
        if fn.name == name:
            return fn

    raise HTTPException(
        status_code=404,
        detail="Function not found",
    )

@router.get(
    "/explore/{owner}/{repo}/class/{name}"
)
def explore_class(
    owner: str,
    repo: str,
    name: str,
):
    repo_key = f"{owner}/{repo}"

    data = get_inventory(
        repo_key
    )

    if not data:
        raise HTTPException(
            status_code=404,
            detail="Repository not indexed",
        )

    for key, cls in (
        data["classes"].items()
    ):
        if cls.name == name:
            return cls

    raise HTTPException(
        status_code=404,
        detail="Class not found",
    )

@router.get(
    "/explore/{owner}/{repo}/module/{path:path}"
)
def explore_module(
    owner: str,
    repo: str,
    path: str,
):
    repo_key = f"{owner}/{repo}"

    data = get_inventory(
        repo_key
    )

    if not data:
        raise HTTPException(
            status_code=404,
            detail="Repository not indexed",
        )

    module = (
        data["modules"]
        .get(path)
    )

    if not module:
        raise HTTPException(
            status_code=404,
            detail="Module not found",
        )

    return module

@router.get(
    "/explore/{owner}/{repo}/file/{path:path}"
)
def explore_file(
    owner: str,
    repo: str,
    path: str,
):
    repo_key = f"{owner}/{repo}"

    data = get_inventory(
        repo_key
    )

    if not data:
        raise HTTPException(
            status_code=404,
            detail="Repository not indexed",
        )

    module = (
        data["modules"]
        .get(path)
    )

    if not module:
        raise HTTPException(
            status_code=404,
            detail="File not found",
        )

    functions = []

    for key, fn in (
        data["functions"].items()
    ):
        if key.startswith(
            f"{path}::"
        ):
            functions.append(fn)

    classes = []

    for key, cls in (
        data["classes"].items()
    ):
        if key.startswith(
            f"{path}::"
        ):
            classes.append(cls)

    return {
        "module": module,
        "functions": functions,
        "classes": classes,
        "imports": data[
            "imports"
        ].get(path, []),
    }