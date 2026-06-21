from fastapi import FastAPI

from routers.index import router as index_router

app = FastAPI(title="Code Knowledge API")

app.include_router(index_router)

@app.get("/")
def health():
    return {"status": "ok"}