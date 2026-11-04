import tempfile
import os
from langchain_community.document_loaders import PyPDFLoader


def load_pdf(uploaded_file):

    temp_path = None

    try:
        # Save uploaded PDF temporarily
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".pdf"
        ) as temp_file:

            temp_file.write(uploaded_file.getvalue())
            temp_path = temp_file.name

        # Extract PDF pages
        loader = PyPDFLoader(temp_path)
        documents = loader.load()

        if not documents:
            raise ValueError("No content found in PDF.")

        return documents

    finally:
        # Remove temporary PDF
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
