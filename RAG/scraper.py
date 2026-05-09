import asyncio
import csv
import argparse
import logging
from dataclasses import dataclass, asdict
from urllib.parse import urljoin
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("8anu")

@dataclass
class Via:
    nombre: str = ""
    grado: str = ""
    sector: str = ""
    crag: str = ""
    ascensos: str = ""
    estrellas: str = ""
    url: str = ""
    lat: str = ""  # Nuevo campo
    lon: str = ""  # Nuevo campo

class Parser:
    @staticmethod
    def extraer_links_crags(html: str, base_url: str) -> list[dict]:
        soup = BeautifulSoup(html, "html.parser")
        crags = []
        encontrados = set()
        
        for a in soup.find_all("a", href=True):
            href = a["href"].split("?")[0].rstrip("/")
            partes = [p for p in href.split("/") if p]
            
            if "crags" in partes and len(partes) >= 4:
                if any(x in href for x in ["/map", "/filter", "/edit", "/users"]):
                    continue
                
                url_limpia = href.replace("/routes", "")
                
                if url_limpia not in encontrados:
                    encontrados.add(url_limpia)
                    nombre = a.get_text(strip=True)
                    if not nombre or len(nombre) < 2: 
                        nombre = partes[-1].replace("-", " ").title()
                    
                    crags.append({
                        "nombre": nombre,
                        "url": urljoin(base_url, url_limpia)
                    })
        return crags

    @staticmethod
    def desde_html(html: str, crag_nombre: str, lat: str, lon: str) -> list[Via]:
        vias = []
        soup = BeautifulSoup(html, "html.parser")
        filas = soup.select("table.zlags-table tbody tr")
        
        for fila in filas:
            try:
                nombre_tag = fila.select_one("td.col-name a.body1-bold")
                grado_tag = fila.select_one("td.col-grade .grade")
                
                sub_links = fila.select("p.sub-link a")
                sector = sub_links[1].get_text(strip=True) if len(sub_links) > 1 else "General"
                
                estrellas_tag = fila.select_one("td.col-rating .inner")
                estrellas = "0"
                if estrellas_tag:
                    estrellas = estrellas_tag.get_text(strip=True).split()[0]

                ascents_tds = fila.select("td.col-ascents.number")
                ascensos = "0"
                if ascents_tds:
                    ascensos = ascents_tds[-1].get_text(strip=True) or "0"

                if nombre_tag:
                    vias.append(Via(
                        nombre=nombre_tag.get_text(strip=True),
                        grado=grado_tag.get_text(strip=True) if grado_tag else "",
                        sector=sector,
                        crag=crag_nombre,
                        ascensos=ascensos,
                        estrellas=estrellas,
                        url=urljoin("https://www.8a.nu", nombre_tag['href']),
                        lat=lat,
                        lon=lon
                    ))
            except Exception:
                continue
        return vias

class Scraper8anu:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.vias_total = []

    async def extraer_coordenadas(self, page) -> tuple[str, str]:
        """Intenta extraer la latitud y longitud de la página principal del crag."""
        try:
            # Esperamos hasta 5 segundos a que aparezca el div con las coordenadas
            coords_div = await page.wait_for_selector("div.coords", timeout=5000)
            if coords_div:
                texto = await coords_div.inner_text()
                if "," in texto:
                    lat, lon = [x.strip() for x in texto.split(",", 1)]
                    return lat, lon
        except Exception:
            # Si no hay coordenadas o se agota el tiempo, devolvemos vacío
            pass
        return "", ""

    async def run(self, url_base: str, max_pages: int = 500):
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            # Bucle de paginación
            for page_num in range(1, max_pages + 1):
                # Construir URL con paginación
                url_actual = f"{url_base}?page={page_num}" if page_num > 1 else url_base
                
                log.info(f"📄 --- PROCESANDO PÁGINA {page_num} --- ({url_actual})")
                await page.goto(url_actual, wait_until="networkidle")
                await asyncio.sleep(2)
                
                html_lista = await page.content()
                links_crags = Parser.extraer_links_crags(html_lista, "https://www.8a.nu")
                
                if not links_crags:
                    log.info("🏁 No se encontraron más zonas. Fin de la paginación.")
                    break
                
                log.info(f"✅ {len(links_crags)} zonas detectadas en la página {page_num}.")

                for i, link in enumerate(links_crags, 1):
                    # 1. Visitar la página principal de la zona para extraer coordenadas
                    url_crag_overview = link["url"]
                    log.info(f"[{i}/{len(links_crags)}] 📍 Zona: {link['nombre']}")
                    
                    try:
                        await page.goto(url_crag_overview, wait_until="domcontentloaded", timeout=30000)
                        lat, lon = await self.extraer_coordenadas(page)
                        if lat and lon:
                            log.info(f"   🗺️ Coordenadas encontradas: {lat}, {lon}")
                        else:
                            log.info("   🗺️ Sin coordenadas disponibles.")

                        # 2. Visitar la página de rutas de esa misma zona
                        url_crag_routes = f"{url_crag_overview}/routes"
                        await page.goto(url_crag_routes, wait_until="domcontentloaded", timeout=30000)
                        
                        try:
                            await page.wait_for_selector("table.zlags-table", timeout=8000)
                        except:
                            pass # Puede que no haya tabla de rutas
                        
                        await page.evaluate("window.scrollBy(0, 1000)")
                        await asyncio.sleep(2)

                        # Parsear las rutas pasándole lat y lon
                        vias_zona = Parser.desde_html(await page.content(), link['nombre'], lat, lon)
                        
                        if vias_zona:
                            log.info(f"   ✨ {len(vias_zona)} vías guardadas.")
                            self.vias_total.extend(vias_zona)
                        else:
                            log.warning("   ❌ No se encontraron vías.")

                    except Exception as e:
                        log.error(f"   ❌ Error procesando {link['nombre']}: {e}")
                    
                    await asyncio.sleep(1) # Pausa por cortesía

                # Guardado periódico tras completar cada página principal
                self.guardar_csv()

            await browser.close()

    def guardar_csv(self):
        if self.vias_total:
            archivo = "todas_las_vias_8anu.csv"
            with open(archivo, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=asdict(self.vias_total[0]).keys())
                writer.writeheader()
                for v in self.vias_total: writer.writerow(asdict(v))
            log.info(f"📊 GUARDADO DE SEGURIDAD: {len(self.vias_total)} vías en {archivo}")

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True, help="Ej: https://www.8a.nu/crags/sportclimbing")
    parser.add_argument("--headless", type=str, default="false")
    parser.add_argument("--pages", type=int, default=500, help="Límite máximo de páginas a iterar")
    args = parser.parse_args()
    
    scraper = Scraper8anu(headless=(args.headless.lower() == "true"))
    await scraper.run(args.url, max_pages=args.pages)

if __name__ == "__main__":
    asyncio.run(main())