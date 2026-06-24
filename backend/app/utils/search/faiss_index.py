import faiss
import numpy as np


from sentence_transformers import (
    SentenceTransformer,
)

model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)

def build_faiss_index(
    documents,
):
    embeddings = model.encode(
        documents,
        normalize_embeddings=True,
        show_progress_bar=True,
    )

    embeddings = np.array(
        embeddings,
        dtype="float32",
    )

    dim = embeddings.shape[1]

    index = faiss.IndexFlatIP(
        dim
    )

    index.add(embeddings)

    return index