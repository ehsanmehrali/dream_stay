from flask import Blueprint, request, jsonify
from sqlalchemy import func, desc
from database import get_db
from models import Property, Booking  # assumes Reservation has property_id FK to Property.id
import time

destinations_bp = Blueprint('destinations', __name__)

# For production purpose. replace with Redis or an external cache in production.
_TRENDING_CACHE = {"data": None, "ts": 0}
_TRENDING_TTL_SECONDS = 300  # 5 minutes

@destinations_bp.route('/destinations/trending', methods=['GET'])
def trending_destinations():
    """
        Return most popular (trending) destinations based on number of reservations.
        Intended to be fetched once on UI load and then cached on the client/edge.

        Query params:
          - limit: number of items (default 8, max 20)
          - lang: language code (unused placeholder)

        Response:
          {
            "lang": "en",
            "limit": 8,
            "trending": [{"location": "Paris, France", "reservations": 124}, ...],
            "fallback": false
          }
        """
    limit = request.args.get('limit', default=8, type=int)
    lang = request.args.get('lang', default='en', type=str)

    limit = max(1, min(limit, 20))

    # Serve from simple in-process cache if fresh
    now = time.time()
    if _TRENDING_CACHE["data"] is not None and (now - _TRENDING_CACHE["ts"] < _TRENDING_TTL_SECONDS):
        payload = {
            "lang": lang,
            "limit": limit,
            "trending": _TRENDING_CACHE["data"][:limit],
            "fallback": False
        }
        resp = jsonify(payload)
        resp.headers["Cache-Control"] = "public, max-age=120, stale-while-revalidate=300"
        return resp, 200

    # Compute trending from DB (join Booking -> Property and group by destination)
    with get_db() as db:
        rows = (
            db.query(
                Property.location.label('location'),
                func.count(Booking.id).label('bookings')
            )
            .join(Booking, Booking.property_id == Property.id)
            .filter(Property.is_approved == True)
            .group_by(Property.location)
            .order_by(desc(func.count(Booking.id)))
            .limit(limit)
            .all()
        )

    if not rows:
        # Hard-coded curated fallback if no reservations exist
        hardcoded = [
                        {"location": "Paris", "bookings": 0},
                        {"location": "Lisbon", "bookings": 0},
                        {"location": "Barcelona", "bookings": 0},
                        {"location": "Rome", "bookings": 0},
                        {"location": "Amsterdam", "bookings": 0},
                        {"location": "Vienna", "bookings": 0},
                        {"location": "Athens", "bookings": 0},
                        {"location": "Prague", "bookings": 0},
                    ][:limit]
        payload = {
            "lang": lang,
            "limit": limit,
            "trending": hardcoded,
            "fallback": True
        }
        resp = jsonify(payload)
        # Allow long cache for fallback since it is static
        resp.headers["Cache-Control"] = "public, max-age=600"
        return resp, 200

    trending_list = [{"location": loc, "bookings": res} for (loc, res) in rows]

    # Update simple cache
    _TRENDING_CACHE["data"] = trending_list
    _TRENDING_CACHE["ts"] = now

    payload = {
        "lang": lang,
        "limit": limit,
        "trending": trending_list,
        "fallback": False
    }
    resp = jsonify(payload)
    # Encourage short client/edge caching
    resp.headers["Cache-Control"] = "public, max-age=120, stale-while-revalidate=300"
    return resp, 200

@destinations_bp.route('/destinations/suggest', methods=['GET'])
def suggest_destinations():
    """
        Suggest distinct property locations matching a user's query (type-ahead use case).
        This endpoint is designed to be cheap, cacheable, and limited.

        Query params:
          - q: search string (case-insensitive). Enforced min length to reduce load.
          - limit: number of results (default 8, max 50)
          - lang: language code (unused placeholder)
          - min_len: minimum length required for q (default 2)

        Response:
          {
            "q": "ber",
            "lang": "en",
            "limit": 8,
            "results": [{"location": "Berlin, Germany", "count": 12}, ...]
          }
        """

    q = request.args.get('q', '', type=str).strip()
    limit = request.args.get('limit', default=8, type=int)
    lang = request.args.get('lang', default='en', type=str)
    min_len = request.args.get('min_len', default=2, type=int)

    limit = max(1, min(limit, 50))
    min_len = max(1, min(min_len, 5))

    # Fast short-circuit for too-short queries
    if len(q) < min_len:
        payload = {"q": q, "lang": lang, "limit": limit, "results": []}
        resp = jsonify(payload)
        # Very short cache; identical short queries are common
        resp.headers["Cache-Control"] = "public, max-age=60"
        return resp, 200

    with get_db() as db:
        # Case-insensitive substring match; ensure proper index (e.g., pg_trgm) in production
        like = f"%{q}%"
        rows = (
            db.query(
                Property.location,
                func.count(Property.id).label('count')
            )
            .filter(
                Property.is_approved == True,
                Property.location.ilike(like)
            )
            .group_by(Property.location)
            .order_by(func.count(Property.id).desc(), Property.location.asc())
            .limit(limit)
            .all()
        )

    results = [{"location": loc, "count": cnt} for (loc, cnt) in rows]

    payload = {"q": q, "lang": lang, "limit": limit, "results": results}
    resp = jsonify(payload)
    # Short-lived cache to absorb fast repeats; increase at edge if desired
    resp.headers["Cache-Control"] = "public, max-age=30"
    return resp, 200