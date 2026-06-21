from pathlib import Path


def build_python_inventory(repo_path: Path):
    files = []

    for file in repo_path.rglob("*.py"):
        files.append(str(file.relative_to(repo_path)))

    return files