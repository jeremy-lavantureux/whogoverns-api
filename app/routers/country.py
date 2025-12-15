from fastapi import APIRouter, Query, HTTPException
from app.db import get_conn

router = APIRouter()

@router.get("/country/{iso3}")
def country_page(
    iso3: str,
    year: int = Query(default=2020, ge=1945, le=2025),
    from_year: int = Query(default=1945, alias="from", ge=1800, le=2100),
    to_year: int = Query(default=2025, alias="to", ge=1800, le=2100),
    lang: str = Query(default="en", pattern="^(en|fr)$"),
):
    iso3 = iso3.upper()
    if from_year > to_year:
        raise HTTPException(status_code=400, detail="'from' must be <= 'to'")

    with get_conn() as conn:
        # Country
        c = conn.execute(
            """
            select iso3,
                   case when %(lang)s='fr' then coalesce(name_fr, name_en) else name_en end as name,
                   continent,
                   coverage_status
            from public.countries
            where iso3 = %(iso3)s
            """,
            {"iso3": iso3, "lang": lang},
        ).fetchone()

        if not c:
            raise HTTPException(status_code=404, detail="Unknown country ISO3")

        # Timeline (ruling_by_year)
        rows = conn.execute(
            """
            select r.year,
                   r.coalition,
                   r.confidence,
                   r.source_id,
                   r.leader_name,
                   p.id as party_id,
                   p.name as party_name,
                   p.abbreviation as party_abbr
            from public.ruling_by_year r
            left join public.parties p on p.id = r.main_party_id
            where r.country_iso3 = %(iso3)s
              and r.year between %(from)s and %(to)s
            order by r.year
            """,
            {"iso3": iso3, "from": from_year, "to": to_year},
        ).fetchall()

    # Build a compact year->power mapping
    by_year = {}
    for r in rows:
        by_year[r["year"]] = {
            "leader_name": r["leader_name"],
            "main_party": None if r["party_id"] is None else {
                "id": r["party_id"],
                "name": r["party_name"],
                "abbr": r["party_abbr"],
            },
            "coalition": r["coalition"],
            "confidence": r["confidence"],
            "source_id": r["source_id"],
        }

    selected = by_year.get(year)

    return {
        "country": {
            "iso3": c["iso3"],
            "name": c["name"],
            "continent": c["continent"],
            "coverage_status": c["coverage_status"],
        },
        "range": {"from": from_year, "to": to_year},
        "selected_year": year,
        "selected": selected,
        "by_year": by_year,  # front can build mini timeline from this
    }
