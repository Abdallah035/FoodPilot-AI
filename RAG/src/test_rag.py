from rag import rag_chain

def ask(question: str) -> str:
    print(f"\n{'='*60}")
    print(f"Question: {question}")
    print('='*60)
    answer = rag_chain.invoke(question)
    print(f"Answer:\n{answer}")
    return answer

# Examples
ask("What are the ingredients for Koshari?")
ask("Which dishes are good for breakfast?")
ask("How do I make crispy onions for street food dishes?")
ask("What vegetarian Egyptian dishes can I make?")
ask("what do you know about ful medames?")