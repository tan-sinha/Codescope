from fastapi import FastAPI

from app.routers.index import router as index_router
from app.routers.explore import router as explore_router
from app.routers.search import router as search_router
from app.routers.graph import router as graph_router

app = FastAPI(title="Code Knowledge API")

app.include_router(index_router)
app.include_router(explore_router)
app.include_router(search_router)
app.include_router(graph_router)

@app.get("/")
def health():
    return {"status": "ok"}