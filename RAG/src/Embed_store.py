from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from Chunking import chunks

embedding_model = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    model_kwargs={"device": "cpu"},   # use "cpu" if no GPU
    encode_kwargs={"normalize_embeddings": True},
)

# Persist to disk so you don't re-embed every run
vectorstore = Chroma.from_documents(
    documents=chunks,
    embedding=embedding_model,
    persist_directory="./chroma_egyptian_dishes",
    collection_name="egyptian_dishes",
)

print(f"Stored {vectorstore._collection.count()} chunks in ChromaDB")