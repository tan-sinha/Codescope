from pathlib import Path

from fastapi import APIRouter, HTTPException
from tree_sitter import Parser, Language
import tree_sitter_python as tspython

from app.models.requests import IndexRequest

from app.utils.git_utils import clone_repo
from app.utils.inventory import build_python_inventory
from app.utils.storage import save_inventory
from app.utils.status import set_status

from app.utils.parsers.function_extractor import extract_functions
from app.utils.parsers.class_extractor import extract_classes
from app.utils.parsers.import_extractor import extract_imports
from app.utils.parsers.call_graph_extractor import build_call_graph

from app.utils.search.documents import build_search_documents
from app.utils.search.faiss_index import build_faiss_index
from app.utils.search.bm25_index import build_bm25_index
from app.utils.search.persistence import save_indexes

from app.utils.module_builder import build_module
from app.utils.summarizer import (
    generate_module_summary,
    generate_function_summaries,
)

router = APIRouter()

_python_parser = Parser(Language(tspython.language()))


def _parse_file(path: Path):
    file_bytes = path.read_bytes()
    tree = _python_parser.parse(file_bytes)
    return tree, file_bytes


@router.post("/index")
def index_repo(request: IndexRequest):
    repo_key = f"{request.owner}/{request.repo}"

    try:
        set_status(repo_key, "indexing")

        repo_path = clone_repo(
            request.owner,
            request.repo,
        )

        files = build_python_inventory(repo_path)

        file_trees = {}
        modules = {}
        functions_index = {}
        classes_index = {}
        imports_index = {}

        for file_path in files:
            tree, file_bytes = _parse_file(repo_path / file_path)

            file_trees[file_path] = {
                "tree": tree,
                "bytes": file_bytes,
            }

            functions = extract_functions(tree.root_node, file_bytes)
            classes = extract_classes(tree.root_node, file_bytes)
            imports = extract_imports(tree.root_node, file_bytes, file_path)

            generate_function_summaries(functions)

            module = build_module(file_path, functions, classes, imports)
            generate_module_summary(module)

            modules[file_path] = module
            imports_index[file_path] = imports

            for fn in functions:
                functions_index[f"{file_path}::{fn.name}"] = fn

            for cls in classes:
                classes_index[f"{file_path}::{cls.name}"] = cls

        call_graph = build_call_graph(file_trees, functions_index, imports_index)

        save_inventory(
            repo_key,
            {
                "repo_key": repo_key,
                "files": files,
                "modules": modules,
                "functions": functions_index,
                "classes": classes_index,
                "imports": imports_index,
                "call_graph": call_graph,
            },
        )



        set_status(repo_key, "ready")

        #Build documents and save FAISS + BM25 indexes
      
        documents, mapping = build_search_documents(
            modules,
            functions_index,
            classes_index,
            call_graph,
        )
        faiss_index = build_faiss_index(documents)
        bm25, corpus = build_bm25_index(documents)
        save_indexes(request.owner, request.repo, faiss_index, corpus, mapping)


        return {
            "owner": request.owner,
            "repo": request.repo,
            "status": "ready",
            "file_count": len(files),
            "function_count": len(functions_index),
            "class_count": len(classes_index),
        }

    except Exception as e:
        set_status(repo_key, "not_indexed")
        raise HTTPException(status_code=500, detail=str(e))
