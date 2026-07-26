import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

app = FastAPI(title="Ankama Profile Scraper API")

# Habilitamos CORS de forma global para tu GitHub Pages
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Render te permite guardar variables secretas de entorno. Aquí cargamos tu token de Browserless
BROWSER_URL = os.getenv("BROWSER_URL")

async def scrape_ankama_profile(profile_name: str):
    url = f"https://ankama.com{profile_name}"
    
    if not BROWSER_URL:
        raise HTTPException(status_code=500, detail="Falta configurar la variable BROWSER_URL en Render.")
        
    async with async_playwright() as p:
        # CORRECCIÓN: Usamos connect_over_cdp para que sea 100% compatible con Browserless
        try:
            browser = await p.chromium.connect_over_cdp(BROWSER_URL)
        except Exception as conn_error:
            raise HTTPException(status_code=500, detail=f"Error de conexión con el navegador en la nube: {str(conn_error)}")

        # Nota: connect_over_cdp ya trae un contexto por defecto del navegador remoto,
        # pero para inyectar el User-Agent limpio de Cloudflare, forzamos un contexto nuevo.
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            # Añadimos un tiempo límite (timeout) de 30 segundos por si Cloudflare se tarda
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            # Le damos 4 segundos en el navegador remoto para renderizar el Javascript de Ankama
            await asyncio.sleep(4) 
            
            html_content = await page.content()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error al extraer los datos de la página: {str(e)}")
        finally:
            await context.close()
            await browser.close()
            
    soup = BeautifulSoup(html_content, "html.parser")
    all_td_elements = soup.find_all("td")
    
    if not all_td_elements:
        title = soup.title.string if soup.title else "Sin título"
        raise HTTPException(status_code=404, detail=f"No se encontraron personajes. Página: {title}")
        
    td_texts = [td.get_text(strip=True) for td in all_td_elements]
    
    characters = []
    for i in range(0, len(td_texts), 5):
        if i + 4 < len(td_texts):
            row = td_texts[i:i+5]
            characters.append({
                "name": row[0],
                "class": row[1],
                "level": row[2],
                "server": row[3],
                "guild": row[4]
            })
            
    return characters


@app.get("/profile/{profile_name}")
async def get_profile(profile_name: str):
    data = await scrape_ankama_profile(profile_name)
    return {"profile": profile_name, "characters": data}

@app.get("/")
def home():
    return {"status": "API de Ankama corriendo perfectamente 24/7 en Render"}
