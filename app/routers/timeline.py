from fastapi import APIRouter, Query, HTTPException
from app.db import get_conn

router = APIRouter()

def _same_power(a: dict, b: dict) -> bool:
    # Compare what matters for timeline grouping
    return (
        a.get("party_id") == b.get("party_id")
        and a.get("coalition") == b.get("coalition")
    )

@router.get("/timeline/{iso3}")
def timeline(
    iso3: str,
    from_year: int = Query(default=1945, alias="from", ge=1800, le=2100),
    to_year: int = Query(default=2025, alias="to", ge=1800, le=2100),
    lang: str = Query(default="en", pattern="^(en|fr)$"),
    include_years: bool = Query(default=False),
):
    """
    Returns compressed timeline segments for a country:
    e.g. 2017-2021 LREM, 2022-2024 Renaissance.
    """
    iso3 = iso3.upper()
    if from_year > to_year:
        raise HTTPException(status_code=400, detail="'from' must be <= 'to'")

    with get_conn() as conn:
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

        rows = conn.execute(
            """
            select r.year,
                   r.coalition,
                   r.confidence,
                   r.source_id,
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

    # Build year records list (only years present in table)
    years = []
    for r in rows:
        years.append({
            "year": r["year"],
            "party_id": r["party_id"],
            "party": None if r["party_id"] is None else {
                "id": r["party_id"],
                "name": r["party_name"],
                "abbr": r["party_abbr"],
            },
            "coalition": r["coalition"],
            "confidence": r["confidence"],
            "source_id": r["source_id"],
        })

    # Compress consecutive years with same party+coalition
    segments = []
    if years:
        cur = years[0]
        seg_start = cur["year"]
        seg_end = cur["year"]

        for item in years[1:]:
            if item["year"] == seg_end + 1 and _same_power(cur, item):
                seg_end = item["year"]
            else:
                segments.append({
                    "start_year": seg_start,
                    "end_year": seg_end,
                    "main_party": cur["party"],
                    "coalition": cur["coalition"],
                    "confidence": cur["confidence"],
                    "source_id": cur["source_id"],
                })
                cur = item
                seg_start = item["year"]
                seg_end = item["year"]

        # last segment
        segments.append({
            "start_year": seg_start,
            "end_year": seg_end,
            "main_party": cur["party"],
            "coalition": cur["coalition"],
            "confidence": cur["confidence"],
            "source_id": cur["source_id"],
        })

    resp = {
        "country": {
            "iso3": c["iso3"],
            "name": c["name"],
            "continent": c["continent"],
            "coverage_status": c["coverage_status"],
        },
        "range": {"from": from_year, "to": to_year},
        "segments": segments,
    }

    if include_years:
        resp["years"] = years

    return resp
