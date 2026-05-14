import os
import re
import time
import json
import requests
import cloudscraper
import pandas as pd
from bs4 import BeautifulSoup
from langchain.tools import tool
from langchain_core.tools import tool
from dotenv import load_dotenv
from RAG.vectorstore import EscaladaVectorStore
from API.database import get_connection, inicializar_db, insertar_plan_completo
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

# TOOL 1: Consultar manual técnico (RAG)

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


# TOOL 2: Obtener clima (actual + pronóstico 5 días)

@tool
def obtener_clima(coordenadas: str) -> str:
    """
    Consulta el clima actual y el pronóstico de 5 días usando LATITUD y LONGITUD.
    El parámetro de entrada DEBE ser un string con el formato exacto: "latitud,longitud" (ejemplo: "36.916960,-4.757770").
    Nunca inventes las coordenadas, extráelas de los resultados de buscar_vias_local.
    """
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        return "Error: Falta OPENWEATHER_API_KEY en el archivo .env"

    try:
        # Limpiar espacios y separar por coma
        lat, lon = [coord.strip() for coord in coordenadas.split(",")]
    except ValueError:
        return "Error de formato. El Action Input para el clima DEBE ser 'latitud,longitud'."

    # URLs actualizadas para usar latitud y longitud
    url_actual = (
        f"http://api.openweathermap.org/data/2.5/weather"
        f"?lat={lat}&lon={lon}&appid={api_key}&units=metric&lang=es"
    )
    url_forecast = (
        f"http://api.openweathermap.org/data/2.5/forecast"
        f"?lat={lat}&lon={lon}&appid={api_key}&units=metric&lang=es&cnt=40"
    )

    try:
        # Clima actual 
        r = requests.get(url_actual, timeout=10)
        data = r.json()
        
        if data.get("cod") != 200:
            return f"No se encontró información climática para las coordenadas: {lat}, {lon}."

        # OpenWeather suele devolver el nombre de la zona más cercana
        nombre_zona = data.get("name", f"las coordenadas ({lat}, {lon})")
        
        temp     = data["main"]["temp"]
        temp_min = data["main"]["temp_min"]
        temp_max = data["main"]["temp_max"]
        humedad  = data["main"]["humidity"]
        desc     = data["weather"][0]["description"].capitalize()
        viento   = data["wind"]["speed"]
        lluvia   = data.get("rain", {}).get("1h", 0)

        resumen = (
            f"🌤️ Clima actual en {nombre_zona}:\n"
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

        # Pronóstico 
        r2 = requests.get(url_forecast, timeout=10)
        fc = r2.json()
        if str(fc.get("cod")) == "200":
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


# TOOL 3: Guardar plan de escalada en BD

@tool
def guardar_plan_escalada(plan_json: str) -> str:
    """
    Guarda un plan de escalada completo en la base de datos SQL.
    El input DEBE ser un string JSON válido con los datos del plan y las vías.
    """
    try:
        # 1. Limpieza de posibles etiquetas de Markdown que el LLM a veces incluye
        plan_json = plan_json.strip()
        if "```json" in plan_json:
            plan_json = plan_json.split("```json")[1].split("```")[0].strip()
        elif "```" in plan_json:
            plan_json = plan_json.split("```")[1].split("```")[0].strip()

        # 2. Parseo del JSON a diccionario
        try:
            data = json.loads(plan_json)
        except json.JSONDecodeError:
            # Reintento simple por si hay comillas simples
            data = json.loads(plan_json.replace("'", '"'))

        # 3. Preparar los datos para la inserción
        # Extraemos información de la primera vía si no viene en el root del JSON
        vias = data.get("vias", [])
        
        # Intentamos autorellenar ciudad/comunidad si no vienen en el root pero sí en las vías
        if not data.get("comunidad_autonoma") and len(vias) > 0 and isinstance(vias[0], dict):
            data["comunidad_autonoma"] = vias[0].get("comunidad_autonoma", "")
        if not data.get("ciudad") and len(vias) > 0 and isinstance(vias[0], dict):
            data["ciudad"] = vias[0].get("ciudad", "")

        # 4. Llamada a la lógica de base de datos (importada de database.py)
        # Esta función ya maneja la apertura/cierre de conexión y la transacción
        resultado = insertar_plan_completo(data)
        
        return resultado

    except Exception as e:
        return f"Error crítico al intentar guardar el plan: {str(e)}"


# TOOL 4: Buscar vías en el CSV local

@tool
def buscar_vias_local(query: str) -> str:
    """
    Busca vías de escalada en la base de datos local (CSV).
    Input: "Lugar, Grado" (ej: "Aragón, 6a" o "Málaga, 5c"). 
    El 'Lugar' puede ser una Comunidad Autónoma, Ciudad, Zona (Crag) o Sector.
    """
    # 1. Rutas
    directorio_actual = os.path.dirname(os.path.abspath(__file__))
    ruta_csv = os.path.normpath(os.path.join(directorio_actual, "..", "RAG", "vias_espania_8anu_limpio.csv"))

    if not os.path.exists(ruta_csv):
        return "Error: El archivo CSV de vías no existe. Ejecuta el notebook de limpieza primero."

    # 2. Parseo de la query (Lugar, Grado)
    partes = [p.strip() for p in query.split(",")]
    lugar_buscado = partes[0]
    grado_buscado = partes[1] if len(partes) > 1 else None

    try:
        df = pd.read_csv(ruta_csv)
        
        # --- LÓGICA DE PRIORIDAD GEOGRÁFICA ---
        
        # Prioridad 1: Coincidencia en ubicación REAL (Comunidad Autónoma o Ciudad)
        filtro_geo = df[
            df['comunidad_autonoma'].str.contains(lugar_buscado, case=False, na=False) |
            df['ciudad'].str.contains(lugar_buscado, case=False, na=False)
        ].copy()

        # Prioridad 2: Coincidencia en nombre del sitio (Crag o Sector)
        filtro_nombre = df[
            df['crag'].str.contains(lugar_buscado, case=False, na=False) |
            df['sector'].str.contains(lugar_buscado, case=False, na=False)
        ].copy()

        # Combinamos: Los de la región real van PRIMERO. 
        # drop_duplicates() elimina los que coincidan en ambos filtros.
        filtro = pd.concat([filtro_geo, filtro_nombre]).drop_duplicates().reset_index(drop=True)
        
        if filtro.empty:
            return f"No encontré resultados para el lugar: '{lugar_buscado}'."

        # 3. Filtro opcional por grado (sobre los resultados ya priorizados)
        if grado_buscado:
            filtro = filtro[filtro['grado'].str.contains(grado_buscado, case=False, na=False)]
            if filtro.empty:
                return f"No encontré vías de grado '{grado_buscado}' en '{lugar_buscado}'."

        # 4. Limpieza de ascensos para ordenar las mejores dentro de la selección
        filtro['ascensos_num'] = pd.to_numeric(filtro['ascensos'].astype(str).str.replace(' ', ''), errors='coerce')
        
        # Tomamos las 15 primeras. Al haber concatenado antes el filtro_geo, 
        # las de la comunidad autónoma correcta saldrán arriba.
        top_vias = filtro.head(15)
        
        # 5. Formatear respuesta
        resumen = f"🧗 Vías encontradas en '{lugar_buscado}':\n"
        for _, row in top_vias.iterrows():
            # Mostramos explícitamente Ciudad y CCAA para que el Agente sepa dónde está cada cosa
            resumen += (
                f"- Vía: '{row['nombre']}' | Grado: {row['grado']} | "
                f"Ubicación: {row['sector']} ({row['crag']}), {row['ciudad']}, {row['comunidad_autonoma']} | "
                f"Estrellas: {row['estrellas']} | Lat/Lon: {row['lat']},{row['lon']}\n"
            )
        return resumen

    except Exception as e:
        return f"Error al procesar la búsqueda local: {str(e)}"