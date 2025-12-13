from fastapi import APIRouter, Query
from app.db import get_conn

router = APIRouter()

CONTINENTS = [
    {"code": "AF", "name_en": "Africa",         "name_fr": "Afrique"},
    {"code": "AN", "name_en": "Antarctica",     "name_fr": "Antarctique"},
    {"code": "AS", "name_en": "Asia",           "name_fr": "Asie"},
    {"code": "EU", "name_en": "Europe",         "name_fr": "Europe"},
    {"code": "NA", "name_en": "North America",  "name_fr": "Amérique du Nord"},
    {"code": "OC", "name_en": "Oceania",        "name_fr": "Océanie"},
    {"code": "SA", "name_en": "South America",  "name_fr": "Amérique du Sud"},
]

@router.get("/metadata")
def metadata(lang: str = Query(default="en", pattern="^(en|fr)$")):
    with get_conn() as conn:
        cov = conn.execute(
            """
            select coverage_status, count(*)::int as count
            from public.countries
            group by coverage_status
            order by coverage_status
            """
        ).fetchall()

        coverage = {row["coverage_status"]: row["count"] for row in cov}

        groups = conn.execute(
            """
            select code, name_en, name_fr
            from public.country_groups
            order by code
            """
        ).fetchall()

    return {
        "years": {"min": 1945, "max": 2025},
        "continents": CONTINENTS,
        "groups": [
            {"code": g["code"], "name": g["name_en"] if lang == "en" else (g["name_fr"] or g["name_en"])}
            for g in groups
        ],
        "coverage": {
            "available": coverage.get("available", 0),
            "in_progress": coverage.get("in_progress", 0),
            "planned": coverage.get("planned", 0),
        },
    }
