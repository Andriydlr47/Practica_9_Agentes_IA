# RockBot Planner 🧗

**RockBot Planner** es una aplicación inteligente (Agente IA) diseñada para ayudar a los escaladores deportivos a planificar salidas seguras. Este proyecto permite conversar con un guía experto (RockBot), consultar información meteorológica y manuales técnicos, buscar vías de escalada y crear planes interactivos que se visualizan en un mapa interactivo en la interfaz.

## Características Principales

*   **Agente Conversacional (RockBot)**: Construido con Langchain y un modelo LLM local a través de Ollama. Implementa un ciclo **ReAct** (Reasoning + Acting) para decidir qué herramientas usar.
*   **Robustez y Manejo de Errores**: El sistema incluye lógica personalizada para recuperar respuestas en caso de errores de formato del modelo (Parsing Errors), garantizando una experiencia de usuario fluida.
*   **Búsqueda RAG (Retrieval-Augmented Generation)**: Capacidad para consultar un manual técnico local extraído de PDFs y webs scrapeadas almacenado en ChromaDB.
*   **Consulta del Clima**: Obtiene información meteorológica en tiempo real usando la API de OpenWeather.
*   **Planes de Escalada**: Generación y almacenamiento local en SQLite de planes con coordenadas, dificultad de vías, notas y estado meteorológico.
*   **Interfaz Moderna**: Aplicación React interactiva con paneles dedicados para el mapa (Leaflet), los planes guardados y un **chat con historial persistente** (localStorage).

## Requisitos Previos

Antes de ejecutar la aplicación, asegúrate de tener instalados:

*   [Python 3.9 o superior](https://www.python.org/)
*   [Node.js](https://nodejs.org/) (v18+)
*   [Ollama](https://ollama.com/) con los modelos:
    *   LLM: `gemma4:26b` (o el configurado en `API/agent.py`)
    *   Embeddings: `mxbai-embed-large` (para el sistema RAG)

## Configuración del Entorno

1.  **Clonar el repositorio**.
2.  **Configurar Variables de Env**:
    Crea un archivo `.env` en la raíz del proyecto:
    ```env
    OPENWEATHER_API_KEY=tu_api_key_aqui
    ```

## Ejecución del Proyecto

### 1. Iniciar el Backend (FastAPI)

```bash
# Instalar dependencias de Python
pip install -r requirements.txt

# Ejecutar el servidor
python -m API.main
```
> El backend corre en `http://localhost:8000`. Incluye manejo avanzado de errores de agente para evitar fallos por alucinaciones de formato.

### 2. Iniciar el Frontend (React / Vite)

```bash
cd frontend
# Instalar dependencias de Node
npm install
# Iniciar desarrollo
npm run dev
```
> La interfaz se abrirá en `http://localhost:5173`.

## Uso de la Aplicación

1.  **Conversación**: Pregunta sobre zonas de escalada o técnicas. El agente buscará en el manual local o en el CSV de vías.
2.  **Clima**: Solicita el clima de una zona específica. RockBot extraerá las coordenadas y consultará la API.
3.  **Gestión de Planes**: Una vez decidas las vías, pide "Guarda este plan". El plan aparecerá automáticamente en el panel derecho y se marcará en el mapa.
4.  **Persistencia**: Puedes cerrar el navegador; tus planes están en SQLite y tu chat en localStorage.

## Estructura del Proyecto

*   `/API/`: Backend FastAPI, lógica del agente (`agent.py`), herramientas (`tools.py`) y base de datos SQLite.
*   `/RAG/`: Sistema de ingestión de documentos y base de datos vectorial ChromaDB.
*   `/frontend/`: Interfaz React con Leaflet y componentes interactivos.

¡Disfruta de tus escaladas de forma segura con RockBot! 🧗‍♂️
