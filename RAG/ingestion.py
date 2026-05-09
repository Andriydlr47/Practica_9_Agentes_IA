import os
import time
import json
import requests
import random
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

# CONFIGURACIÓN
DATA_PATH = "./RAG/data/"
CHROMA_PATH = "./chroma_db"
COLLECTION_NAME = "escalada_total"

# Sustituimos URLs por Nombres de Zonas de interés
ZONAS_INTERES = [
    "Spain",
    "Argentina",
    "Brazil",
    "Canada",
    "Chad",
    "Chile",
    "China",
    "Congo",
    "Colombia",
    "Egypt",
    "Estonia",
    "France",
    "Germany",
    "Georgia",
    "Greece",
    "Iceland",
    "Iran",
    "Monaco"
]

def _metadatos_seguros(metadata: dict) -> dict:
    clean = {}
    for k, v in metadata.items():
        if v is None:
            clean[k] = ""
        elif isinstance(v, (int, float, bool)):
            clean[k] = v
        else:
            clean[k] = str(v)
    return clean

def obtener_datos_8anu(query: str):
    """Obtiene datos estructurados de 8a.nu para una zona."""
    base_url = "https://www.8a.nu/api"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Origin": "https://www.8a.nu",
        "Referer": "https://www.8a.nu/"
    }
    
    try:
        # 1. Buscar la zona para obtener el slug
        search_res = requests.get(f"{base_url}/search?query={query}", headers=headers, timeout=10)
        crags = search_res.json().get("crags", {}).get("items", [])
        if not crags: return None
        
        target = crags[0]
        slug = target.get("slug")
        
        # 2. Obtener sectores de esa zona
        sectors_res = requests.get(f"{base_url}/crags/{slug}/sectors", headers=headers, timeout=10)
        sectors = sectors_res.json().get("items", [])
        
        # 3. Construir contenido de texto para el RAG
        texto_contenido = f"ZONA DE ESCALADA: {target.get('name')}\n"
        texto_contenido += f"UBICACIÓN: {target.get('city')}, {target.get('country')}\n"
        texto_contenido += f"COORDENADAS: {target.get('latitude')}, {target.get('longitude')}\n\n"
        texto_contenido += "SECTORES Y VÍAS:\n"
        
        for s in sectors:
            texto_contenido += f"- Sector: {s['name']} | Vías: {s['routesCount']} | Grado: {s.get('gradeIndex', 'N/A')}\n"
        
        metadata = {
            "source": f"https://www.8a.nu/crags/climbing/{slug}",
            "type": "8a.nu",
            "tipo_pagina": "zona",
            "nombre": target.get("name"),
            "lat": target.get("latitude"),
            "lon": target.get("longitude")
        }
        
        return Document(page_content=texto_contenido, metadata=metadata)
    except Exception as e:
        print(f"Error procesando {query} en 8a.nu: {e}")
        return None

def cargar_todo():
    all_documents = []

    # 1. CARGA DE PDFs (Manuales técnicos)
    if os.path.exists(DATA_PATH):
        print(f"\n── Cargando PDFs desde {DATA_PATH} ──")
        pdf_loader = DirectoryLoader(DATA_PATH, glob="./*.pdf", loader_cls=PyPDFLoader)
        docs_pdf = pdf_loader.load()
        for doc in docs_pdf:
            doc.metadata.update({"type": "manual_pdf", "tipo_pagina": "manual"})
            doc.metadata = _metadatos_seguros(doc.metadata)
        all_documents.extend(docs_pdf)
        print(f"   ✓ {len(docs_pdf)} páginas de PDF cargadas.")

    # 2. CARGA DESDE 8A.NU (Sustituye al Scraper)
    print(f"\n── Obteniendo datos de 8a.nu para {len(ZONAS_INTERES)} zonas ──")
    for zona in ZONAS_INTERES:
        print(f"   Procesando: {zona}...")
        doc = obtener_datos_8anu(zona)
        if doc:
            doc.metadata = _metadatos_seguros(doc.metadata)
            all_documents.append(doc)
            print(f"      ✓ Datos obtenidos con éxito.")
        time.sleep(1) # Delay suave

    if not all_documents:
        print("No hay documentos para indexar.")
        return

    # 3. CHUNKING
    splitter = RecursiveCharacterTextSplitter(chunk_size=700, chunk_overlap=100)
    chunks = splitter.split_documents(all_documents)

    # 4. VECTORIZACIÓN
    print(f"\n── Indexando {len(chunks)} fragmentos en ChromaDB ──")
    embeddings = OllamaEmbeddings(model="mxbai-embed-large")
    
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=CHROMA_PATH,
        collection_name=COLLECTION_NAME
    )
    print(f"\n✅ BASE DE DATOS ACTUALIZADA CON 8A.NU")

if __name__ == "__main__":
    cargar_todo()