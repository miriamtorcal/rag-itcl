import argparse
import shutil

import pymupdf4llm
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from client.rag.embeddings import get_embedding_model
from client.utils.settings import FILE_PATH, VECTORSTORE_PATH


def load_pdf():
    md_pages = pymupdf4llm.to_markdown(FILE_PATH, page_chunks=True)
    docs = []
    for i, page in enumerate(md_pages):
        # BUSCA ESTO EN TU LOG AL RE-INDEXAR
        if (
            page.get("metadata", {}).get("page") == 34
        ):  # pymupdf suele ser 0-indexed, 34 es la 35
            print(f"DEBUG: 📄 Contenido Página 35: {page['text'][:200]}")
        # Intentamos sacar la página de metadata, si no existe usamos el índice del bucle
        # pymupdf4llm a veces usa 'page' directamente dentro de 'metadata'
        metadata = page.get("metadata", {})
        page_num = metadata.get("page", i + 1)

        docs.append(
            Document(
                page_content=page.get("text", ""),
                metadata={"page": page_num, "source": str(FILE_PATH.name)},
            )
        )
    return docs


def chunking(docs):
    # Reducimos un poco el chunk_size para que las tablas no se corten a la mitad
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=2000,  # Aumentamos para no romper tablas pequeñas
        chunk_overlap=200,
        separators=["\n---", "\n\n", "\n", " "],  # Priorizamos cortes de página/sección
    )
    chunked_docs = []
    for doc in docs:
        page = doc.metadata.get("page", 0)  # Asegurar que hay un entero
        splits = splitter.split_text(doc.page_content)

        for i, chunk in enumerate(splits):
            chunked_docs.append(
                {
                    "text": chunk,
                    "metadata": {
                        "page": page
                        + 1,  # +1 porque PyPDFLoader empieza en 0 y los humanos en 1
                        "chunk_id": f"p{page}_c{i}",
                        "source": FILE_PATH.name,
                    },
                }
            )
    return chunked_docs


def index_exists():
    return VECTORSTORE_PATH.exists()


def load_index():
    embeddings = get_embedding_model()
    return Chroma(
        persist_directory=str(VECTORSTORE_PATH),
        embedding_function=embeddings,
    )


def create_index(chunks):
    embeddings = get_embedding_model()

    texts = [c["text"] for c in chunks]
    metadatas = [c["metadata"] for c in chunks]

    vectorstore = Chroma.from_texts(
        texts=texts,
        metadatas=metadatas,
        embedding=embeddings,
        persist_directory=str(VECTORSTORE_PATH),
    )

    return vectorstore


def build_index(force=False):
    if force and VECTORSTORE_PATH.exists():
        print(f"DEBUG: 🗑️ Borrando base de datos vieja en {VECTORSTORE_PATH}")
        shutil.rmtree(VECTORSTORE_PATH)

    if index_exists() and not force:
        return load_index()

    docs = load_pdf()
    chunks = chunking(docs)
    return create_index(chunks)


def main():
    parser = argparse.ArgumentParser(description="Herramientas RAG")

    parser.add_argument("--reindex", action="store_true", help="Reindexa el PDF")

    args = parser.parse_args()

    if args.reindex:
        build_index(force=True)
    else:
        build_index()


if __name__ == "__main__":
    main()
