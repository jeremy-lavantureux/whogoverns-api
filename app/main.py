from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import metadata, map as map_router
from app.routers import country, events, articles
from app.routers import timeline
from app.routers import country_summary


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
app.include_router(country.router, prefix="/v1", tags=["country"])
app.include_router(events.router, prefix="/v1", tags=["events"])
app.include_router(articles.router, prefix="/v1", tags=["articles"])
app.include_router(timeline.router, prefix="/v1", tags=["timeline"])
app.include_router(country_summary.router, prefix="/v1", tags=["country"])
