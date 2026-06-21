from typing import Dict, Any

knowledge_store: Dict[str, Any] = {}


def save_inventory(repo_key: str, files):
    knowledge_store[repo_key] = {
        "files": files
    }


def get_inventory(repo_key: str):
    return knowledge_store.get(repo_key)