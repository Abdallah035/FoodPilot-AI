from langchain_core.documents import Document

def recipe_to_document(recipe: dict) -> Document:
    """
    Converts a single recipe dict into a LangChain Document.
    page_content holds everything as text so the embedder can
    understand the full context. Metadata is kept separate for
    structured filtering (e.g. filter by category).
    """
    def format_ingredient(ing):
        if isinstance(ing, dict):
            if "ingredient" in ing or "amount" in ing:
                return f"  - {ing.get('ingredient', 'Unknown')}: {ing.get('amount', '')}"
            if len(ing) == 1:
                name, amount = next(iter(ing.items()))
                return f"  - {name}: {amount}"
            return f"  - {ing}"
        return f"  - {ing}"

    ingredients_text = "\n".join(
        format_ingredient(ing)
        for ing in recipe.get("ingredients", [])
    )
    instructions_text = "\n".join(
        f"  {i+1}. {step}"
        for i, step in enumerate(recipe.get("instructions", []))
    )
    tips_text = "\n".join(
        f"  - {tip}"
        for tip in recipe.get("chef_tips_and_cultural_notes", [])
    )

    page_content = f"""
Dish Name: {recipe['name']}
Description: {recipe['description']}

Category: {recipe['metadata']['category']}
Prep Time: {recipe['metadata']['prep_time']}
Cook Time: {recipe['metadata']['cook_time']}
Servings: {recipe['metadata']['servings']}

Ingredients:
{ingredients_text}

Instructions:
{instructions_text}

Chef Tips & Cultural Notes:
{tips_text}
""".strip()

    return Document(
        page_content=page_content,
        metadata={
            "id": recipe["id"],
            "name": recipe["name"],
            "category": recipe["metadata"]["category"],
            "prep_time": recipe["metadata"]["prep_time"],
            "cook_time": recipe["metadata"]["cook_time"],
        }
    )

from Data_loader import recipes

docs = [recipe_to_document(r) for r in recipes]

