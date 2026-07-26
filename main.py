import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from curl_cffi import requests
from bs4 import BeautifulSoup

app = FastAPI(title="Ankama Profile Scraper API")

# Habilitamos CORS de forma global para tu GitHub Pages
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://bastiancarreno.github.io", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/profile/{profile_name}")
def get_profile(profile_name: str):
    url = f"https://ankama.com{profile_name}"
    
    try:
        # Usamos curl_cffi para suplantar la firma exacta de Chrome 120
        response = requests.get(
            url, 
            impersonate="chrome120", 
            timeout=15.0
        )
        
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="El perfil de Ankama especificado no existe.")
        elif response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=f"Ankama respondió con estado: {response.status_code}")
            
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error en la conexión segura con Ankama: {str(exc)}")

    # Procesamos el HTML obtenido
    soup = BeautifulSoup(response.text, "html.parser")
    all_td_elements = soup.find_all("td")
    
    if not all_td_elements:
        title = soup.title.string if soup.title else "Sin título"
        # Si Cloudflare lograra frenarnos, lo capturamos aquí de forma segura sin romper CORS
        if "Cloudflare" in title or "Just a moment" in title:
            raise HTTPException(status_code=403, detail="La solicitud fue interceptada por seguridad. Inténtalo de nuevo.")
        raise HTTPException(status_code=404, detail=f"No se encontraron personajes en este perfil. El perfil podría ser privado.")
        
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
