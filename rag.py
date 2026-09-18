import os
import shutil

from dotenv import load_dotenv
from google import genai

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_core.documents import Document

from pdf_processor import extract_pdf_pages
from chatbot_config import SYSTEM_PROMPT


# =========================================================
# ENVIRONMENT
# =========================================================

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.1-flash-lite"
)

EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "models/gemini-embedding-001"
)


if not GEMINI_API_KEY:
    raise ValueError(
        "GEMINI_API_KEY is missing. "
        "Please add GEMINI_API_KEY to your .env file."
    )


client = genai.Client(
    api_key=GEMINI_API_KEY
)


# =========================================================
# EMBEDDINGS
# =========================================================

embeddings = GoogleGenerativeAIEmbeddings(
    model=EMBEDDING_MODEL,
    google_api_key=GEMINI_API_KEY,
    output_dimensionality=768
)


# =========================================================
# TEXT SPLITTER
# =========================================================

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1200,
    chunk_overlap=200,
    separators=[
        "\n\n",
        "\n",
        ". ",
        " ",
        ""
    ]
)


# =========================================================
# VECTOR DATABASE
# =========================================================

VECTOR_DB_PATH = "vector_db"

COLLECTION_NAME = "querydoc_documents"


vector_store = Chroma(
    collection_name=COLLECTION_NAME,
    embedding_function=embeddings,
    persist_directory=VECTOR_DB_PATH
)


# =========================================================
# DELETE VECTOR DATABASE
# =========================================================

def clear_vector_database():

    global vector_store

    try:
        # Delete current collection
        vector_store.delete_collection()

    except Exception as e:
        print(
            "Vector collection delete warning:",
            str(e)
        )

    # Remove complete Chroma folder
    if os.path.exists(VECTOR_DB_PATH):

        try:
            shutil.rmtree(VECTOR_DB_PATH)

        except Exception as e:
            print(
                "Vector DB folder delete warning:",
                str(e)
            )

    # Recreate empty folder
    os.makedirs(
        VECTOR_DB_PATH,
        exist_ok=True
    )

    # Create fresh Chroma store
    vector_store = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=VECTOR_DB_PATH
    )


# =========================================================
# INDEX PDF
# =========================================================

def index_pdf(pdf_path, document_name):

    pages = extract_pdf_pages(pdf_path)

    documents = []
    ids = []

    for page_data in pages:

        page_number = page_data["page"]

        page_text = page_data["text"]

        if not page_text.strip():
            continue

        chunks = text_splitter.split_text(
            page_text
        )

        for chunk_index, chunk in enumerate(chunks):

            if not chunk.strip():
                continue

            document = Document(
                page_content=chunk,
                metadata={
                    "page": page_number,
                    "document": document_name,
                    "chunk_index": chunk_index
                }
            )

            documents.append(document)

            chunk_id = (
                f"{document_name}_"
                f"{page_number}_"
                f"{chunk_index}"
            )

            ids.append(chunk_id)

    if documents:

        vector_store.add_documents(
            documents=documents,
            ids=ids
        )

    return {
        "pages": len(pages),
        "chunks": len(documents)
    }


# =========================================================
# SEARCH DOCUMENT
# =========================================================

def search_document(question, top_k=5):

    retriever = vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={
            "k": top_k
        }
    )

    retrieved_documents = retriever.invoke(
        question
    )

    retrieved = []

    for document in retrieved_documents:

        retrieved.append({
            "text": document.page_content,
            "page": document.metadata.get("page"),
            "document": document.metadata.get("document")
        })

    return retrieved


# =========================================================
# GENERATE ANSWER
# =========================================================

def generate_answer(question):

    retrieved_chunks = search_document(
        question,
        top_k=5
    )

    if not retrieved_chunks:

        return {
            "answer": (
                "I couldn't find this information "
                "in the uploaded document."
            ),
            "sources": []
        }


    context_parts = []

    for item in retrieved_chunks:

        context_parts.append(
            f"""
DOCUMENT: {item['document']}

PAGE: {item['page']}

CONTENT:

{item['text']}
"""
        )


    context = "\n\n".join(
        context_parts
    )


    prompt = f"""
{SYSTEM_PROMPT}

You are QueryDoc AI, a document-grounded
RAG assistant.

Use ONLY the retrieved document context
provided below.

STRICT RULES:

1. Answer ONLY using the uploaded document.

2. Do NOT use outside knowledge.

3. Do NOT invent or guess information.

4. If the information is not available,
say:

"I couldn't find this information
in the uploaded document."

5. Give clear and accurate answers.

6. Preserve numerical values exactly
as they appear in the document.

7. For comparison questions, use only
values available in the document.

8. Mention relevant page numbers.

9. Do not answer unrelated questions.

10. Do not pretend to know information
that is not present in the document.

RETRIEVED DOCUMENT CONTEXT:

{context}

USER QUESTION:

{question}

Answer using ONLY the retrieved
document context.

At the end include:

Sources:
- Page X
- Page Y
"""


    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt
    )


    sources = []

    for item in retrieved_chunks:

        source = {
            "document": item["document"],
            "page": item["page"]
        }

        if source not in sources:

            sources.append(source)


    return {
        "answer": response.text,
        "sources": sources
    }
