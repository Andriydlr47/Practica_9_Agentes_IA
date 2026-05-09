from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

CHROMA_PATH = "./chroma_db"
COLLECTION_NAME = "escalada_total"

class EscaladaVectorStore:
    def __init__(self):
        self.embeddings = OllamaEmbeddings(
            model="mxbai-embed-large",
            base_url="http://localhost:11434"
        )
        
        self.vectorstore = Chroma(
            persist_directory=CHROMA_PATH,
            collection_name=COLLECTION_NAME,
            embedding_function=self.embeddings
        )

    def buscar_info(self, query):
        # Busca los 5 fragmentos más relevantes
        docs = self.vectorstore.similarity_search(query, k=5)
        return "\n\n".join([doc.page_content for doc in docs])
    
    def añadir_documento(self, texto, metadatos):
        """Añade un nuevo fragmento de información a la base de datos vectorial."""
        doc = Document(page_content=texto, metadata=metadatos)
        self.vectorstore.add_documents([doc])
        print(f"Documento indexado en ChromaDB: {metadatos.get('nombre', 'Sin nombre')}")