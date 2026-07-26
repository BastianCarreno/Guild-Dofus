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
        # CONEXIÓN REMOTA: En lugar de lanzar Chromium localmente, usamos el navegador en la nube
        browser = await p.chromium.connect(BROWSER_URL)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            await page.goto(url, wait_until="domcontentloaded")
            html_content = await page.content()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error al cargar la página: {str(e)}")
        finally:
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
