from fastapi import APIRouter, Query, HTTPException
from app.db import get_conn

router = APIRouter()

POLITICAL_TYPES = [
    "election",
    "government_change",
    "referendum",
    "constitutional_change",
    "institutional_crisis",
    "other_political",
]


@router.get("/country/{iso3}/summary")
def country_summary(
    iso3: str,
    year: int = Query(..., ge=1945, le=2025),
    from_year: int = Query(default=1945, alias="from", ge=1800, le=2100),
    to_year: int = Query(default=2025, alias="to", ge=1800, le=2100),
    lang: str = Query(default="en", pattern="^(en|fr)$"),
    events_limit: int = Query(default=20, ge=1, le=100),
    articles_limit: int = Query(default=10, ge=1, le=50),
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

        # Power for selected year
        power = conn.execute(
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
            where r.country_iso3 = %(iso3)s and r.year = %(year)s
            """,
            {"iso3": iso3, "year": year},
        ).fetchone()

        selected = None
        if power:
            selected = {
                "leader_name": power["leader_name"],
                "year": power["year"],
                "main_party": None if power["party_id"] is None else {
                    "id": power["party_id"],
                    "name": power["party_name"],
                    "abbr": power["party_abbr"],
                },
                "coalition": power["coalition"],
                "confidence": power["confidence"],
                "source_id": power["source_id"],
            }

        # Timeline years (only present years)
        years = conn.execute(
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

        # Events (political-only)
        ev = conn.execute(
            """
            select id, country_iso3, year, event_type, title, description, event_date, source_id
            from public.country_events
            where country_iso3 = %(iso3)s
              and year = %(year)s
              and event_type = any(%(types)s)
            order by event_date nulls last, id
            limit %(limit)s
            """,
            {"iso3": iso3, "year": year, "types": POLITICAL_TYPES, "limit": events_limit},
        ).fetchall()

        # Articles
        ar = conn.execute(
            """
            select id, slug, title, lang, country_iso3, year, tags, published_at, created_at
            from public.articles
            where lang = %(lang)s
              and country_iso3 = %(iso3)s
              and year = %(year)s
            order by published_at desc nulls last, created_at desc
            limit %(limit)s
            """,
            {"lang": lang, "iso3": iso3, "year": year, "limit": articles_limit},
        ).fetchall()

    # Compress timeline into segments (same logic as /v1/timeline)
    def same(a, b):
        return (
            a["party_id"] == b["party_id"]
            and a["coalition"] == b["coalition"]
            and a["leader_name"] == b["leader_name"]
        )

    segments = []
    if years:
        cur = years[0]
        start = cur["year"]
        end = cur["year"]

        for item in years[1:]:
            if item["year"] == end + 1 and same(cur, item):
                end = item["year"]
            else:
                segments.append({
                    "start_year": start,
                    "end_year": end,
                    "leader_name": cur["leader_name"],
                    "main_party": None if cur["party_id"] is None else {
                        "id": cur["party_id"],
                        "name": cur["party_name"],
                        "abbr": cur["party_abbr"],
                    },
                    "coalition": cur["coalition"],
                    "confidence": cur["confidence"],
                    "source_id": cur["source_id"],
                })
                cur = item
                start = item["year"]
                end = item["year"]

        segments.append({
            "start_year": start,
            "end_year": end,
            "leader_name": cur["leader_name"],
            "main_party": None if cur["party_id"] is None else {
                "id": cur["party_id"],
                "name": cur["party_name"],
                "abbr": cur["party_abbr"],
            },
            "coalition": cur["coalition"],
            "confidence": cur["confidence"],
            "source_id": cur["source_id"],
        })

    return {
        "country": {
            "iso3": c["iso3"],
            "name": c["name"],
            "continent": c["continent"],
            "coverage_status": c["coverage_status"],
        },
        "selected_year": year,
        "selected": selected,
        "timeline": {
            "range": {"from": from_year, "to": to_year},
            "segments": segments,
        },
        "events": {"count": len(ev), "events": ev},
        "articles": {"count": len(ar), "articles": ar},
    }
