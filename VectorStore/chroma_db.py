from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma


# Initialize embedding model
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)


def create_vectorstore(chunks):

    # Create vector database from PDF chunks
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name="testanix_requirements",
        persist_directory="chroma_db"
    )

    return vectorstore


def get_retriever(vectorstore):

    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 4}
    )

    return retriever
