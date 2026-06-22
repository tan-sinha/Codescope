from pydantic import BaseModel

class IndexRequest(BaseModel):
    owner:str
    repo:str

