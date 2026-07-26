import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from bs4 import BeautifulSoup

app = FastAPI(title="Ankama Profile Scraper API")

# Cabeceras CORS configuradas correctamente
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://bastiancarreno.github.io", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/profile/{profile_name}")
async def get_profile(profile_name: str):
    url = f"https://account.ankama.com/en/ankama-profile/{profile_name}"
    
    # Headers optimizados para evitar bloqueos simulando un navegador orgánico
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache"
    }
    
    # Realizamos la petición HTTP asíncrona directa sin navegadores pesados
    async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
        try:
            response = await client.get(url, headers=headers)
            if response.status_code == 404:
                raise HTTPException(status_code=404, detail="El perfil de Ankama especificado no existe.")
            elif response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=f"Ankama respondió con estado: {response.status_code}")
        except httpx.RequestError as exc:
            raise HTTPException(status_code=500, detail=f"Error de conexión con Ankama: {str(exc)}")

    # Procesamos el HTML obtenido
    soup = BeautifulSoup(response.text, "html.parser")
    all_td_elements = soup.find_all("td")
    
    if not all_td_elements:
        title = soup.title.string if soup.title else "Sin título"
        # Si Cloudflare nos frena, lo sabremos por el título de la página
        if "Cloudflare" in title or "Just a moment" in title:
            raise HTTPException(status_code=403, detail="La solicitud fue interceptada por Cloudflare. Inténtalo más tarde.")
        raise HTTPException(status_code=404, detail=f"No se encontraron personajes en este perfil. Título: {title}")
        
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
            
    return {"profile": profile_name, "characters": characters}

@app.get("/")
def home():
    return {"status": "API de Ankama corriendo perfectamente 24/7 en Render"}
