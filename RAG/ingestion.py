import os
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma

# CONFIGURACIÓN
DATA_PATH = "./RAG/data/"
CHROMA_PATH = "./chroma_db"
COLLECTION_NAME = "escalada_total"

def _metadatos_seguros(metadata: dict) -> dict:
    """Asegura que todos los metadatos sean tipos compatibles con ChromaDB."""
    clean = {}
    for k, v in metadata.items():
        if v is None:
            clean[k] = ""
        elif isinstance(v, (int, float, bool)):
            clean[k] = v
        else:
            clean[k] = str(v)
    return clean

def cargar_pdfs():
    # 1. CARGA DE PDFs
    if not os.path.exists(DATA_PATH):
        print(f"Error: La ruta {DATA_PATH} no existe.")
        return

    print(f"\n── Cargando PDFs desde {DATA_PATH} ──")
    # Cargamos todos los PDFs en la carpeta
    pdf_loader = DirectoryLoader(DATA_PATH, glob="./*.pdf", loader_cls=PyPDFLoader)
    docs_pdf = pdf_loader.load()

    if not docs_pdf:
        print("No se encontraron archivos PDF para indexar.")
        return

    # Añadimos metadatos extra para identificar el origen
    for doc in docs_pdf:
        doc.metadata.update({"type": "manual_pdf", "tipo_pagina": "manual"})
        doc.metadata = _metadatos_seguros(doc.metadata)

    print(f"   ✓ {len(docs_pdf)} páginas cargadas.")

    # 2. CHUNKING (Fragmentación)
    # Dividimos el texto en trozos para que el modelo pueda procesarlos mejor
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )
    chunks = splitter.split_documents(docs_pdf)
    print(f"   ✓ Creados {len(chunks)} fragmentos.")

    # 3. VECTORIZACIÓN E INGESTA EN CHROMADB
    print(f"\n── Indexando en ChromaDB: {CHROMA_PATH} ──")
    embeddings = OllamaEmbeddings(
        model="mxbai-embed-large"
    )
    
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=CHROMA_PATH,
        collection_name=COLLECTION_NAME
    )
    
    print(f"\n✅ BASE DE DATOS CREADA EXITOSAMENTE CON LOS PDFS")

if __name__ == "__main__":
    cargar_pdfs()