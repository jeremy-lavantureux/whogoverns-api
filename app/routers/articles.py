from fastapi import APIRouter, Query
from app.db import get_conn

router = APIRouter()

@router.get("/articles")
def list_articles(
    iso3: str | None = Query(default=None, min_length=3, max_length=3),
    year: int | None = Query(default=None, ge=1800, le=2100),
    lang: str = Query(default="en", pattern="^(en|fr)$"),
    limit: int = Query(default=20, ge=1, le=100),
):
    iso3 = iso3.upper() if iso3 else None

    params = {"lang": lang, "limit": limit}
    where = ["lang = %(lang)s"]

    if iso3:
        where.append("country_iso3 = %(iso3)s")
        params["iso3"] = iso3
    if year is not None:
        where.append("year = %(year)s")
        params["year"] = year

    where_sql = " where " + " and ".join(where)

    with get_conn() as conn:
        rows = conn.execute(
            f"""
            select id, slug, title, lang, country_iso3, year, tags, published_at, created_at
            from public.articles
            {where_sql}
            order by published_at desc nulls last, created_at desc
            limit %(limit)s
            """,
            params,
        ).fetchall()

    return {"count": len(rows), "articles": rows}
