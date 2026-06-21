from typing import Dict

repo_status: Dict[str, str] = {}


def set_status(key: str, value: str):
    repo_status[key] = value


def get_status(key: str):
    return repo_status.get(key, "not_indexed")