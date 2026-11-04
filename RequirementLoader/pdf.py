from langchain_community.document_loaders import PyPDFLoader
import tempfile
import os

def load_pdf(uploaded_file):

    # Save uploaded PDF temporarily
    with tempfile.NamedTemporaryFile(
        delete=False, suffix=".pdf"
    ) as temp_file:

        temp_file.write(uploaded_file.getvalue())
        temp_path = temp_file.name

    try:
        # Load PDF
        loader = PyPDFLoader(temp_path)
        documents = loader.load()

        return documents

    finally:
        # Delete temporary file
        os.remove(temp_path)