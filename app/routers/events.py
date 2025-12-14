from fastapi import APIRouter, Query, HTTPException
from app.db import get_conn

router = APIRouter()

POLITICAL_TYPES = {
    "election",
    "government_change",
    "referendum",
    "constitutional_change",
    "institutional_crisis",
    "other_political",
}

@router.get("/events")
def events(
    iso3: str = Query(..., min_length=3, max_length=3),
    year: int = Query(..., ge=1800, le=2100),
    # si vide -> tous les types politiques
    event_types: str | None = Query(default=None, description="Comma-separated list of political event types"),
    limit: int = Query(default=50, ge=1, le=200),
):
    iso3 = iso3.upper()

    selected_types = None
    if event_types:
        parts = [p.strip() for p in event_types.split(",") if p.strip()]
        bad = [p for p in parts if p not in POLITICAL_TYPES]
        if bad:
            raise HTTPException(status_code=400, detail=f"Invalid event_types: {bad}")
        selected_types = parts

    with get_conn() as conn:
        exists = conn.execute(
            "select 1 from public.countries where iso3 = %(iso3)s",
            {"iso3": iso3},
        ).fetchone()
        if not exists:
            raise HTTPException(status_code=404, detail="Unknown country ISO3")

        if selected_types:
            rows = conn.execute(
                """
                select id, country_iso3, year, event_type, title, description, event_date, source_id
                from public.country_events
                where country_iso3 = %(iso3)s
                  and year = %(year)s
                  and event_type = any(%(types)s)
                order by event_date nulls last, id
                limit %(limit)s
                """,
                {"iso3": iso3, "year": year, "types": selected_types, "limit": limit},
            ).fetchall()
        else:
            rows = conn.execute(
                """
                select id, country_iso3, year, event_type, title, description, event_date, source_id
                from public.country_events
                where country_iso3 = %(iso3)s
                  and year = %(year)s
                  and event_type = any(%(types)s)
                order by event_date nulls last, id
                limit %(limit)s
                """,
                {"iso3": iso3, "year": year, "types": list(POLITICAL_TYPES), "limit": limit},
            ).fetchall()

    return {"iso3": iso3, "year": year, "count": len(rows), "events": rows, "allowed_types": sorted(POLITICAL_TYPES)}
