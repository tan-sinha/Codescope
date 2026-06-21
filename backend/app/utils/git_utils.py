import subprocess
import tempfile 
from pathlib import Path

def clone_repo(owner:str , repo:str) -> Path:

    temp_dir=tempfile.mkdtemp()

    repo_url=f"https://github.com/{owner}/{repo}.git"

    subprocess.run(

        [
            "git",
            "clone",
            "--depth",
            "1",
            repo_url,
            temp_dir,
        ],
        check=True,
    )

    return Path(temp_dir)