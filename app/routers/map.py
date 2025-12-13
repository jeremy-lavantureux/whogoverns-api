from fastapi import APIRouter, Query
from app.db import get_conn

router = APIRouter()

@router.get("/map")
def map_data(
    year: int = Query(..., ge=1945, le=2025),
    continent: str | None = Query(default=None, pattern="^(AF|AN|AS|EU|NA|OC|SA)$"),
    group: str | None = Query(default=None, pattern="^(EU|OECD)$"),
    covered_only: bool = False,
    lang: str = Query(default="en", pattern="^(en|fr)$"),
):
    """
    Returns a compact ISO3->data mapping for a given year.
    """
    params = {"year": year}

    where = []
    if continent:
        where.append("c.continent = %(continent)s")
        params["continent"] = continent

    if covered_only:
        where.append("c.coverage_status = 'available'")

    # Group filtering uses membership table
    join_group = ""
    if group:
        join_group = """
            join public.country_group_members gm
              on gm.country_iso3 = c.iso3
            join public.country_groups g
              on g.id = gm.group_id and g.code = %(group)s
        """
        params["group"] = group

    where_sql = ("where " + " and ".join(where)) if where else ""

    sql = f"""
        select
          c.iso3,
          case when %(lang)s = 'fr' then coalesce(c.name_fr, c.name_en) else c.name_en end as country_name,
          c.continent,
          c.coverage_status,
          r.coalition,
          r.confidence,
          r.source_id,
          p.id as party_id,
          p.name as party_name,
          p.abbreviation as party_abbr
        from public.countries c
        {join_group}
        left join public.ruling_by_year r
          on r.country_iso3 = c.iso3 and r.year = %(year)s
        left join public.parties p
          on p.id = r.main_party_id
        {where_sql}
        order by c.iso3
    """

    with get_conn() as conn:
        rows = conn.execute(sql, params | {"lang": lang}).fetchall()

        countries = {}
        available_count = 0
        with_data_count = 0

        for row in rows:
            if row["coverage_status"] == "available":
                available_count += 1
            if row["party_id"] is not None:
                with_data_count += 1

            countries[row["iso3"]] = {
                "country": {
                    "name": row["country_name"],
                    "continent": row["continent"],
                    "coverage_status": row["coverage_status"],
                },
                "power": {
                    "main_party": None if row["party_id"] is None else {
                        "id": row["party_id"],
                        "name": row["party_name"],
                        "abbr": row["party_abbr"],
                    },
                    "coalition": row["coalition"],
                    "confidence": row["confidence"],
                    "source_id": row["source_id"],
                }
            }

    return {
        "year": year,
        "meta": {
            "lang": lang,
            "filters": {
                "continent": continent,
                "group": group,
                "covered_only": covered_only,
            },
            "counts": {
                "countries_returned": len(rows),
                "available": available_count,
                "with_data": with_data_count,
            }
        },
        "countries": countries,
    }
