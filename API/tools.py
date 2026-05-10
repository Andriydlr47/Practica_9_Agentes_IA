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
        # ── Clima actual ──────────────────────────────────────
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

        # ── Pronóstico ────────────────────────────────────────
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


# ─────────────────────────────────────────────────────────────
# TOOL 3: Guardar plan de escalada en BD
# ─────────────────────────────────────────────────────────────
@tool
def guardar_plan_escalada(plan_json: str) -> str:
    """
    Guarda un plan de escalada completo. El input debe ser un JSON string.
    """
    try:
        # 1. Limpieza de markdown
        plan_json = plan_json.strip()
        if "```json" in plan_json:
            plan_json = plan_json.split("```json")[1].split("```")[0].strip()
        elif "```" in plan_json:
            plan_json = plan_json.split("```")[1].split("```")[0].strip()

        # 2. Parseo
        try:
            data = json.loads(plan_json)
        except:
            data = json.loads(plan_json.replace("'", '"'))

        conn = get_connection()
        cursor = conn.cursor()

        # 3. Insertar Plan
        cursor.execute('''
            INSERT INTO planes_escalada
            (nombre_plan, fecha, zona_principal, lat, lon, clima, temperatura, viento, dificultad_rango, notas)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get("nombre_plan", "Nuevo Plan"),
            data.get("fecha", "Pendiente"),
            data.get("zona_principal", "Desconocida"),
            data.get("lat"),
            data.get("lon"),
            data.get("clima", ""),
            data.get("temperatura"),
            data.get("viento"),
            data.get("dificultad_rango", ""),
            data.get("notas", ""),
        ))
        plan_id = cursor.lastrowid

        # 4. Insertar Vías (Manejo robusto de strings o dicts)
        vias = data.get("vias", [])
        for via in vias:
            if isinstance(via, str):
                # Si el modelo solo envió el nombre de la vía como texto
                nombre_v, sector_v, dif_v = via, "General", data.get("dificultad_rango", "")
                lat_v, lon_v = data.get("lat"), data.get("lon")
            else:
                # Si el modelo envió el objeto completo
                nombre_v = via.get("nombre_via", "Vía sin nombre")
                sector_v = via.get("sector", "")
                dif_v = via.get("dificultad", "")
                lat_v = via.get("lat", data.get("lat"))
                lon_v = via.get("lon", data.get("lon"))

            cursor.execute('''
                INSERT INTO vias_plan (plan_id, nombre_via, zona, sector, dificultad, lat, lon)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (plan_id, nombre_v, data.get("zona_principal"), sector_v, dif_v, lat_v, lon_v))

        conn.commit()
        conn.close()
        return f"✅ Plan '{data.get('nombre_plan')}' guardado con éxito (ID: {plan_id})."

    except Exception as e:
        return f"❌ Error en la base de datos: {str(e)}"


# ─────────────────────────────────────────────────────────────
# TOOL 4: Buscar vías en el CSV local
# ─────────────────────────────────────────────────────────────
@tool
def buscar_vias_local(query: str) -> str:
    """
    Busca vías de escalada en la base de datos local (CSV).
    Input: Puede ser solo la zona (ej: "El Chorro") o zona y grado (ej: "El Chorro, 6b").
    Devuelve las 10 mejores vías que coincidan con la búsqueda.
    """
    # 1. Rutas
    directorio_actual = os.path.dirname(os.path.abspath(__file__))
    ruta_csv = os.path.normpath(os.path.join(directorio_actual, "..", "RAG", "vias_espania_8anu_limpio.csv"))

    if not os.path.exists(ruta_csv):
        return "Error: El archivo CSV de vías no existe."

    # 2. Parseo de la query (Zona, Grado)
    partes = [p.strip() for p in query.split(",")]
    zona_buscada = partes[0]
    grado_buscado = partes[1] if len(partes) > 1 else None

    try:
        df = pd.read_csv(ruta_csv)
        
        # Filtro por zona o sector (usamos .copy() para evitar el SettingWithCopyWarning)
        filtro = df[df['crag'].str.contains(zona_buscada, case=False, na=False) | 
                    df['sector'].str.contains(zona_buscada, case=False, na=False)].copy()
        
        if filtro.empty:
            return f"No encontré vías en la zona o sector '{zona_buscada}'."

        # Filtro opcional por grado
        if grado_buscado:
            filtro = filtro[filtro['grado'].str.contains(grado_buscado, case=False, na=False)]
            if filtro.empty:
                return f"No encontré vías de grado '{grado_buscado}' en '{zona_buscada}'."

        # Limpieza de ascensos y ordenación
        filtro['ascensos_num'] = filtro['ascensos'].astype(str).str.replace(' ', '', regex=False).apply(pd.to_numeric, errors='coerce')
        top_vias = filtro.sort_values(by='ascensos_num', ascending=False).head(10)
        
        resumen = f"🧗 Vías encontradas en {zona_buscada} (Filtrado por '{grado_buscado}' si se especificó):\n"
        for _, row in top_vias.iterrows():
            resumen += (
                f"- Vía: '{row['nombre']}' | Grado: {row['grado']} | Sector: {row['sector']} | "
                f"Estrellas: {row['estrellas']} | Lat/Lon: {row['lat']},{row['lon']}\n"
            )
        return resumen

    except Exception as e:
        return f"Error al procesar el CSV local: {str(e)}"