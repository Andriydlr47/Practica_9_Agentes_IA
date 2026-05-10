import os
import re
import time
import json
import requests
import cloudscraper
import pandas as pd
from bs4 import BeautifulSoup
from langchain.tools import tool
from dotenv import load_dotenv
from RAG.vectorstore import EscaladaVectorStore
from API.database import get_connection, inicializar_db
from langchain_ollama import ChatOllama
from langchain_core.documents import Document

load_dotenv()

# Inicializar BD al arrancar (por si no existe aún)
inicializar_db()

# RAG local
try:
    vector_db = EscaladaVectorStore()
except Exception as e:
    print(f"⚠️  No se pudo conectar con ChromaDB: {e}")
    vector_db = None

    # Función auxiliar para limpiar metadatos
def _metadatos_seguros(metadata: dict) -> dict:
    clean = {}
    for k, v in metadata.items():
        if v is None: clean[k] = ""
        elif isinstance(v, (int, float, bool)): clean[k] = v
        else: clean[k] = str(v)
    return clean

# ─────────────────────────────────────────────────────────────
# TOOL 1: Consultar manual técnico (RAG)
# ─────────────────────────────────────────────────────────────
@tool
def consultar_manual_tecnico(query: str) -> str:
    """
    Busca información técnica en la base de datos local (PDFs y theCrag scrapeado).
    Úsala para preguntas sobre nudos, tipos de roca, material (mosquetones, cuerdas),
    técnicas de seguridad, maniobras de escalada, zonas y vías ya indexadas.
    """
    if vector_db is None:
        return "La base de datos local no está disponible. Ejecuta ingestion.py primero."
    try:
        return vector_db.buscar_info(query)
    except Exception as e:
        return f"Error al consultar el manual local: {str(e)}"


# ─────────────────────────────────────────────────────────────
# TOOL 2: Obtener clima (actual + pronóstico 5 días)
# ─────────────────────────────────────────────────────────────
@tool
def obtener_clima(ciudad: str) -> str:
    """
    Consulta el clima actual y el pronóstico de los próximos 5 días para una ubicación.
    Esencial para planificar salidas de escalada y verificar si la roca estará seca.
    Devuelve temperatura, descripción, viento y pronóstico diario.
    """
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        return "Error: Falta OPENWEATHER_API_KEY en el archivo .env"

    # Clima actual
    url_actual = (
        f"http://api.openweathermap.org/data/2.5/weather"
        f"?q={ciudad}&appid={api_key}&units=metric&lang=es"
    )
    # Pronóstico 5 días
    url_forecast = (
        f"http://api.openweathermap.org/data/2.5/forecast"
        f"?q={ciudad}&appid={api_key}&units=metric&lang=es&cnt=40"
    )

    try:
        # ── Clima actual ──────────────────────────────────────
        r = requests.get(url_actual, timeout=10)
        data = r.json()
        if data.get("cod") != 200:
            return f"No se encontró información climática para: {ciudad}."

        temp     = data["main"]["temp"]
        temp_min = data["main"]["temp_min"]
        temp_max = data["main"]["temp_max"]
        humedad  = data["main"]["humidity"]
        desc     = data["weather"][0]["description"].capitalize()
        viento   = data["wind"]["speed"]
        lluvia   = data.get("rain", {}).get("1h", 0)

        resumen = (
            f"🌤️ Clima actual en {ciudad}:\n"
            f"  • {desc}\n"
            f"  • Temperatura: {temp}°C (mín {temp_min}°C / máx {temp_max}°C)\n"
            f"  • Humedad: {humedad}%\n"
            f"  • Viento: {viento} m/s\n"
            f"  • Lluvia última hora: {lluvia} mm\n"
        )

        # Evaluación para escalar
        if lluvia > 0 or "lluvia" in desc.lower() or "tormenta" in desc.lower():
            resumen += "\n⚠️ Condiciones NO recomendadas para escalar (humedad/lluvia)."
        elif viento > 10:
            resumen += "\n⚠️ Viento fuerte, precaución en vías expuestas."
        else:
            resumen += "\n✅ Condiciones favorables para escalar."

        # ── Pronóstico ────────────────────────────────────────
        r2 = requests.get(url_forecast, timeout=10)
        fc = r2.json()
        if fc.get("cod") == "200":
            dias = {}
            for item in fc["list"]:
                dia = item["dt_txt"].split(" ")[0]
                if dia not in dias:
                    dias[dia] = {
                        "desc": item["weather"][0]["description"].capitalize(),
                        "temp_max": item["main"]["temp_max"],
                        "temp_min": item["main"]["temp_min"],
                        "lluvia": item.get("rain", {}).get("3h", 0),
                    }
                else:
                    if item["main"]["temp_max"] > dias[dia]["temp_max"]:
                        dias[dia]["temp_max"] = item["main"]["temp_max"]
                    if item["main"]["temp_min"] < dias[dia]["temp_min"]:
                        dias[dia]["temp_min"] = item["main"]["temp_min"]
                    dias[dia]["lluvia"] += item.get("rain", {}).get("3h", 0)

            resumen += "\n\n📅 Próximos días:\n"
            for dia, info in list(dias.items())[:5]:
                icono = "🌧️" if info["lluvia"] > 1 else "☀️"
                resumen += (
                    f"  {icono} {dia}: {info['desc']}, "
                    f"{info['temp_min']:.0f}-{info['temp_max']:.0f}°C"
                    f"{', lluvia' if info['lluvia'] > 1 else ''}\n"
                )

        return resumen

    except Exception as e:
        return f"Error de conexión con el servicio meteorológico: {str(e)}"


# ─────────────────────────────────────────────────────────────
# TOOL 3: Buscar zona/ruta en theCrag en tiempo real
# ─────────────────────────────────────────────────────────────
@tool
def buscar_en_8anu(query: str) -> str:
    """
    Busca zonas de escalada (crags) en 8a.nu. 
    Traduce automáticamente la consulta al inglés para mejorar resultados.
    Si la zona es nueva, la guarda en la base de datos local.
    """
    # 1. TRADUCCIÓN INTERNA (Español -> Inglés)
    # Usamos una instancia rápida de Ollama para asegurar que buscamos en inglés
    try:
        llm_translator = ChatOllama(model="gemma4:26b", temperature=0) # O el modelo que prefieras
        query_en = llm_translator.invoke(f"Translate only the location name to English: {query}").content.strip()
    except:
        query_en = query # Fallback si falla la traducción

    base_url = "https://www.8a.nu/api"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Origin": "https://www.8a.nu",
        "Referer": "https://www.8a.nu/"
    }

    try:
        # 2. BÚSQUEDA EN API
        response = requests.get(f"{base_url}/search?query={query_en}", headers=headers, timeout=10)
        data = response.json()
        crags = data.get("crags", {}).get("items", [])
        
        if not crags:
            return f"No se encontró información para '{query}' (buscado como '{query_en}') en 8a.nu."

        target = crags[0]
        slug = target.get("slug")
        
        # 3. OBTENER SECTORES
        s_resp = requests.get(f"{base_url}/crags/{slug}/sectors", headers=headers, timeout=10)
        sectors = s_resp.json().get("items", [])
        
        # 4. CONSTRUIR CONTENIDO
        texto_contenido = f"ZONA DE ESCALADA: {target.get('name')}\n"
        texto_contenido += f"UBICACIÓN: {target.get('city')}, {target.get('country')}\n"
        texto_contenido += "SECTORES:\n"
        for s in sectors:
            texto_contenido += f"- {s['name']} ({s['routesCount']} vías)\n"

        # 5. AUTO-INGESTA EN CHROMADB (Si tenemos conexión a vector_db)
        if vector_db:
            metadatos = _metadatos_seguros({
                "source": f"https://www.8a.nu/crags/climbing/{slug}",
                "type": "8a.nu",
                "nombre": target.get("name"),
                "lat": target.get("latitude"),
                "lon": target.get("longitude")
            })
            vector_db.añadir_documento(texto_contenido, metadatos)

        # 6. RETORNAR RESPUESTA AL AGENTE
        resumen = f"📍 Encontrado: **{target.get('name')}** en {target.get('country')}\n"
        resumen += f"Sectores principales: {', '.join([s['name'] for s in sectors[:5]])}\n"
        return resumen

    except Exception as e:
        return f"Error técnico en la búsqueda: {str(e)}"
    

# ─────────────────────────────────────────────────────────────
# TOOL 4: Guardar plan de escalada en BD
# ─────────────────────────────────────────────────────────────
@tool
def guardar_plan_escalada(plan_json: str) -> str:
    """
    Guarda un plan de escalada completo en la base de datos local SQLite.
    
    El argumento plan_json debe ser un JSON estructurado con datos obtenidos de 8a.nu y el clima:
    {
      "nombre_plan": "Escalada en Siurana",
      "fecha": "2024-05-20",
      "zona_principal": "Siurana",
      "lat": 41.258,
      "lon": 0.932,
      "clima": "Despejado",
      "temperatura": 22.0,
      "viento": 5.0,
      "dificultad_rango": "6b - 7a",
      "notas": "Llevar cuerda de 80m y muchas cintas.",
      "vias": [
        {
          "nombre_via": "L'Anella",
          "zona": "Siurana",
          "sector": "Esperó Primavera",
          "dificultad": "6b+",
          "longitud_m": 30,
          "num_chapas": 12,
          "lat": 41.259,
          "lon": 0.933,
          "advertencias": "Asegurar bien el primer aleje",
          "fotos_urls": "",
          "url_fuente": "https://www.8a.nu/crags/climbing/siurana/..."
        }
      ]
    }
    """
    try:
        # 1. Parsear y limpiar el JSON
        try:
            data = json.loads(plan_json)
        except json.JSONDecodeError:
            # Fallback por si el LLM envía comillas simples o formato mal formado
            data = json.loads(plan_json.replace("'", '"'))

        conn = get_connection() # Ya incluye el PRAGMA foreign_keys = ON
        cursor = conn.cursor()

        # 2. Insertar en la tabla 'planes_escalada'
        cursor.execute('''
            INSERT INTO planes_escalada
              (nombre_plan, fecha, zona_principal, lat, lon,
               clima, temperatura, viento, dificultad_rango, notas)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get("nombre_plan", "Nuevo Plan"),
            data.get("fecha", ""),
            data.get("zona_principal", ""),
            data.get("lat"),
            data.get("lon"),
            data.get("clima", ""),
            data.get("temperatura"),
            data.get("viento"),
            data.get("dificultad_rango", ""),
            data.get("notas", ""),
        ))
        plan_id = cursor.lastrowid

        # 3. Insertar las vías asociadas en 'vias_plan'
        vias = data.get("vias", [])
        for via in vias:
            # Manejo de fotos (si vienen en lista, convertir a string separado por ;)
            fotos = via.get("fotos_urls", "")
            if isinstance(fotos, list):
                fotos = ";".join(fotos)
            
            cursor.execute('''
                INSERT INTO vias_plan
                  (plan_id, nombre_via, zona, sector, dificultad,
                   longitud_m, num_chapas, lat, lon,
                   advertencias, fotos_urls, thecrag_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                plan_id,
                via.get("nombre_via", "Vía"),
                via.get("zona", data.get("zona_principal", "")),
                via.get("sector", ""),
                via.get("dificultad", ""),
                via.get("longitud_m"),
                via.get("num_chapas"),
                via.get("lat"),
                via.get("lon"),
                via.get("advertencias", ""),
                fotos,
                via.get("url_fuente", ""), # Mapeamos 'url_fuente' (8a.nu) al campo de la DB
            ))

        conn.commit()
        conn.close()

        resumen = f"✅ Plan '{data.get('nombre_plan')}' guardado con éxito (ID: {plan_id})."
        if vias:
            resumen += f" Se han registrado {len(vias)} vías para tu salida."
        
        return resumen

    except Exception as e:
        return f"❌ Error al guardar el plan en la base de datos: {str(e)}"
    

# ─────────────────────────────────────────────────────────────
# TOOL 5: Buscar vías en el CSV local
# ─────────────────────────────────────────────────────────────
@tool
def buscar_vias_local(zona: str) -> str:
    """
    Busca vías de escalada en la base de datos local (CSV) filtrando por zona (crag) o sector.
    Devuelve las 10 mejores vías de la zona ordenadas por popularidad.
    Úsala cuando el usuario pregunte por recomendaciones de vías o sectores en España.
    """
    ruta_csv = "vias_espania_8anu.csv"
    if not os.path.exists(ruta_csv):
        return "El archivo CSV de vías no existe en el sistema."

    try:
        # Leemos el CSV
        df = pd.read_csv(ruta_csv)
        
        # Filtramos por la zona (crag) ignorando mayúsculas/minúsculas
        filtro = df[df['crag'].str.contains(zona, case=False, na=False) | 
                    df['sector'].str.contains(zona, case=False, na=False)]
        
        if filtro.empty:
            return f"No se encontraron vías locales para la zona o sector '{zona}'."
        
        # Limpiamos la columna de ascensos (viene con espacios ej: "1 078") y la pasamos a número
        filtro['ascensos_num'] = filtro['ascensos'].astype(str).str.replace(' ', '', regex=False).apply(pd.to_numeric, errors='coerce')
        
        # Ordenamos para mostrar las más populares primero
        top_vias = filtro.sort_values(by='ascensos_num', ascending=False).head(10)
        
        # Construimos la respuesta para el bot
        resumen = f"🧗 Vías más populares encontradas en {zona} (CSV local):\n"
        for _, row in top_vias.iterrows():
            resumen += (
                f"- Vía: '{row['nombre']}' | Grado: {row['grado']} | Sector: {row['sector']} | "
                f"Estrellas: {row['estrellas']} | Lat/Lon: {row['lat']},{row['lon']}\n"
            )
        
        return resumen

    except Exception as e:
        return f"Error al procesar el CSV local: {str(e)}"