
from flask import Blueprint, request, jsonify
from flask import Response
import json
from collections import OrderedDict
from datetime import datetime, timedelta
from models import Property, Availability
from database import get_db



search_bp = Blueprint('search', __name__)


@search_bp.route('/search', methods=['GET'])
def search_properties():
    """
    Search properties by location/title within a date range (dates are mandatory).
    - Date range is (check_in, check_out) -> checkout date is not included.
    - Output: A list of objects for each property with the order of the keys:
        location, property_id, title, total_night, total_price, available_from, available_to, dates
    - The `dates` key is at the end and contains the price/status of each night.
    - If include_partial=false (default) only returns if all nights are available.
    Example output for each item:
    {
      "location": "Tehran",
      "property_id": 1,
      "title": "ehsan Flatt 02",
      "total_night": 14,
      "total_price": 168000.0,
      "available_from": "2025-10-01",
      "available_to": "2025-10-15",
      "dates": {
        "2025-10-01": {"is_available": true, "price": 12000.0},
        ...
        "2025-10-14": {"is_available": true, "price": 12000.0}
      }
    }
    """
    location = request.args.get('location', type=str)
    title = request.args.get('title', type=str)
    include_partial = (request.args.get('include_partial', 'false').lower() == 'true')
    limit = request.args.get('limit', type=int) or 50
    offset = request.args.get('offset', type=int) or 0
    check_in_str = request.args.get('check_in', type=str)
    check_out_str = request.args.get('check_out', type=str)

    # Dates are mandatory.
    if not check_in_str or not check_out_str:
        return jsonify({'error': 'check_in and check_out are required (YYYY-MM-DD)'}), 400

    # Date validation.
    try:
        check_in = datetime.strptime(check_in_str, '%Y-%m-%d').date()
        check_out = datetime.strptime(check_out_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD.'}), 400

    if check_out <= check_in:
        return jsonify({'error': 'check_out must be after check_in'}), 400

    total_nights = (check_out - check_in).days

    results = []
    with get_db() as db:
        q = db.query(Property)
        if location:
            q = q.filter(Property.location.ilike(f"%{location.strip()}%"))
        if title:
            q = q.filter(Property.title.ilike(f"%{title.strip()}%"))

        props = q.offset(offset).limit(limit).all()

        for p in props:
            # Only nights in range (check_in, check_out)
            recs = (
                db.query(Availability)
                .filter(
                    Availability.property_id == p.id,
                    Availability.date >= check_in,
                    Availability.date < check_out,
                )
                .all()
            )
            by_date = {r.date: r for r in recs}

            dates_map = {}
            all_nights_available = True
            total_price = 0.0

            cur = check_in
            while cur < check_out:
                r = by_date.get(cur)
                if r:
                    is_avail = bool(r.is_available and not r.is_reserved and not r.is_blocked)
                    price_val = float(r.price)
                else:
                    is_avail = False
                    price_val = 0.0

                if is_avail:
                    total_price += price_val
                else:
                    all_nights_available = False

                dates_map[cur.strftime('%Y-%m-%d')] = {
                    'price': price_val,
                    'is_available': is_avail
                }
                cur += timedelta(days=1)

            # Default behavior: Return only when all nights are available.
            if not include_partial and not all_nights_available:
                continue
            item = OrderedDict()
            cover = next((im for im in p.images if im.is_cover), None)
            item['cover_url'] = cover.url if cover else (p.images[0].url if p.images else None)
            item['location'] = p.location
            item['property_id'] = p.id
            item['title'] = p.title
            item['total_night'] = total_nights
            item['total_price'] = total_price
            item['available_from'] = check_in_str
            item['available_to'] = check_out_str

            item['dates'] = dates_map

            results.append(item)

        body = json.dumps(results, ensure_ascii=False, sort_keys=False)

    return Response(body, status=200, mimetype='application/json')