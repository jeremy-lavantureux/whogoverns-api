from fastapi import APIRouter, Query, HTTPException
from app.db import get_conn

router = APIRouter()

@router.get("/events")
def events(
    iso3: str = Query(..., min_length=3, max_length=3),
    year: int = Query(..., ge=1800, le=2100),
    limit: int = Query(default=50, ge=1, le=200),
    lang: str = Query(default="en", pattern="^(en|fr)$"),
):
    iso3 = iso3.upper()

    with get_conn() as conn:
        exists = conn.execute(
            "select 1 from public.countries where iso3 = %(iso3)s",
            {"iso3": iso3},
        ).fetchone()
        if not exists:
            raise HTTPException(status_code=404, detail="Unknown country ISO3")

        rows = conn.execute(
            """
            select id, country_iso3, year, title, description, event_date, source_id
            from public.country_events
            where country_iso3 = %(iso3)s and year = %(year)s
            order by event_date nulls last, id
            limit %(limit)s
            """,
            {"iso3": iso3, "year": year, "limit": limit},
        ).fetchall()

    return {
        "iso3": iso3,
        "year": year,
        "count": len(rows),
        "events": rows,
    }
