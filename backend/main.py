from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.core.db import init_db
from fastapi.staticfiles import StaticFiles
from backend.routers import maps, nodes, aliases, edges, routes, admin

app = FastAPI(title="Indoor Wayfinder API", version="0.1.0")

# CORS dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve thư mục data/uploads dưới /static (để frontend load ảnh)
app.mount("/static", StaticFiles(directory="data"), name="static")
app.mount("/app", StaticFiles(directory="frontend"), name="app")


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}


# routers
app.include_router(maps.router, prefix="/maps", tags=["maps"])
app.include_router(nodes.router, prefix="/nodes", tags=["nodes"])
app.include_router(aliases.router, prefix="/aliases", tags=["aliases"])
app.include_router(edges.router, prefix="/edges", tags=["edges"])
app.include_router(routes.router, prefix="", tags=["route"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
