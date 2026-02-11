import argparse

from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from client.rag.embeddings import get_embedding_model
from client.utils.settings import FILE_PATH, VECTORSTORE_PATH


def load_pdf():
    loader = PyPDFLoader(FILE_PATH)
    docs = loader.load()

    return docs


def chunking(docs):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500, chunk_overlap=100, separators=["\n\n", "\n", ".", " ", ""]
    )

    chunked_docs = []

    for doc in docs:
        page = doc.metadata.get("page", None)

        splits = splitter.split_text(doc.page_content)

        for i, chunk in enumerate(splits):
            start = doc.page_content.find(chunk)
            end = start + len(chunk)

            chunked_docs.append(
                {
                    "text": chunk,
                    "metadata": {
                        "page": page,
                        "chunk_id": f"p{page}_c{i}",
                        "source": FILE_PATH.name,
                        "char_start": start,
                        "char_end": end,
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
