from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import metadata, map as map_router

app = FastAPI(title="WhoGoverns API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

app.include_router(metadata.router, prefix="/v1", tags=["metadata"])
app.include_router(map_router.router, prefix="/v1", tags=["map"])
