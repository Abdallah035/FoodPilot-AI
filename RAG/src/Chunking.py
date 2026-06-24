from langchain_text_splitters import RecursiveCharacterTextSplitter
from Document import docs

splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,        
    chunk_overlap=80,      
    separators=["\n\n", "\n", ". ", " ", ""],
)

chunks = docs
print(f"Split into {len(chunks)} chunks from {len(docs)} documents")
