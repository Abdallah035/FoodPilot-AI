import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from Reranker import reranking_retriever

load_dotenv()

groq_key = os.getenv("GROQ_API_KEY")
if groq_key:
    os.environ["GROQ_API_KEY"] = groq_key
else:
    raise EnvironmentError("GROQ_API_KEY is not set. Please set the environment variable or add it to .env before running rag.py.")

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.4,
)

prompt = ChatPromptTemplate.from_template("""You are a precise culinary assistant specializing in Egyptian cuisine.
Use the following pieces of retrieved context to answer the question at the end.

STRICT RULES:
1. If the user asks for a specific category of food (e.g., 'breakfast'), ONLY list dishes whose category explicitly includes that meal or whose description directly states it is traditionally eaten for that meal.
2. Absolutely DO NOT include lunch or dinner dishes unless they are explicitly cross-listed as suitable for the requested meal.
3. If a dish doesn't explicitly match, skip it entirely. Do not guess or assume.
4. focus on the metadata which includes the category, preparation time, serving, cooking time.

Context:
{context}

Question: {question}

Answer:
""")

def format_docs(docs):
    """Join retrieved chunks into a single context string."""
    return "\n\n---\n\n".join(
        f"[{doc.metadata['name']}]\n{doc.page_content}"
        for doc in docs
    )

rag_chain = (
    {
        "context": reranking_retriever | format_docs,
        "question": RunnablePassthrough(),
    }
    | prompt
    | llm
    | StrOutputParser()
)