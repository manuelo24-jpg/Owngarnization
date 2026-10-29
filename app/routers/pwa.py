from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import FileResponse, JSONResponse

BASE_DIR = Path(__file__).resolve().parent.parent

router = APIRouter(tags=["PWA"])

MANIFEST_DATA = {
    "name": "Owngarnization — App Móvil",
    "short_name": "Owngarnization",
    "description": "Aplicación móvil minimalista de gestión de tareas y calendario con tablero de post-its.",
    "start_url": "/m?source=pwa",
    "scope": "/",
    "display": "standalone",
    "background_color": "#FAF8F5",
    "theme_color": "#111111",
    "lang": "es",
    "orientation": "portrait-primary",
    "icons": [
        {
            "src": "/static/img/icons/icon-192.png?v=4",
            "sizes": "192x192",
            "type": "image/png",
            "purpose": "any"
        },
        {
            "src": "/static/img/icons/icon-512.png?v=4",
            "sizes": "512x512",
            "type": "image/png",
            "purpose": "any"
        },
        {
            "src": "/static/img/icons/maskable-512.png?v=4",
            "sizes": "512x512",
            "type": "image/png",
            "purpose": "maskable"
        }
    ]
}


@router.get("/manifest.webmanifest")
def get_manifest():
    """Sirve el Web App Manifest desde la raíz."""
    return JSONResponse(
        content=MANIFEST_DATA,
        media_type="application/manifest+json"
    )


@router.get("/sw.js")
def get_service_worker():
    """Sirve el Service Worker desde la raíz con scope global y sin caché."""
    sw_path = BASE_DIR / "static" / "sw.js"
    return FileResponse(
        path=str(sw_path),
        media_type="application/javascript",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Service-Worker-Allowed": "/"
        }
    )

