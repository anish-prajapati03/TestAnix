from langchain_huggingface import HuggingFaceEmbeddings

print("Loading embedding model...")

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

print("Model loaded successfully!")

result = embeddings.embed_query(
    "Generate test cases for login functionality"
)

print("Embedding generated!")
print("Vector length:", len(result))