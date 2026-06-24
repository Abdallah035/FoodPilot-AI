from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers.ensemble import EnsembleRetriever
from Embed_store import vectorstore
from Chunking import chunks

bm25_retriever = BM25Retriever.from_documents(chunks)
bm25_retriever.k = 10   

semantic_retriever = vectorstore.as_retriever(
    search_type="similarity",
    search_kwargs={"k": 10},
)


hybrid_retriever = EnsembleRetriever(
    retrievers=[bm25_retriever, semantic_retriever],
    weights=[0.7, 0.3],
)