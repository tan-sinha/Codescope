from pydantic import BaseModel

class IndexRequest(BaseModel):
    owner:str
    repo:str

class SearchRequest(BaseModel):
    owner: str
    repo: str
    query: str