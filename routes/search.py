
from datetime import datetime
from flask import request, jsonify

from flask import Blueprint

from models import Property
from database import get_db
from utils.availability import check_property_availability

search_bp = Blueprint('search', __name__)


@search_bp.route('/search', methods=['GET'])
def search_properties():
    """
    Searches for bookable accommodations within a specific time
    period based on location or accommodation title.
    Returns a list of properties list:
    [['property_id', 'title', 'location', 'price_per_night', 'total_price', 'available_from', 'available_to', 'total_night']]
    """
    location = request.args.get('location')
    title = request.args.get('title')
    check_in_str = request.args.get('check_in')
    check_out_str = request.args.get('check_out')

    if not check_in_str or not check_out_str:
        return jsonify({'error': 'check_in and check_out are required'}), 400

    if not location and not title:
        return jsonify({'error': 'location or title must be provided'}), 400

    try:
        check_in = datetime.strptime(check_in_str, "%Y-%m-%d").date()
        check_out = datetime.strptime(check_out_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

    if check_in >= check_out:
        return jsonify({'error': 'check_out must be after check_in'}), 400

    total_nights = (check_out - check_in).days

    with get_db() as db:
        # Getting all properties or exact property availability data, based on location or title
        if title:
            properties = db.query(Property).filter(
                Property.title.ilike(f'%{title}%'),
                Property.is_approved == True
            ).all()
        else:
            properties = db.query(Property).filter_by(
                location=location,
                is_approved=True
            ).all()

        results = []
        for prop in properties:
            # using helper function from /utils
            success, availability_records, _ = check_property_availability(db, prop.id, check_in, check_out)

            if success:
                total_price = sum([a.price for a in availability_records])
                results.append({
                    'property_id': prop.id,
                    'title': prop.title,
                    'location': prop.location,
                    'price_per_night': round(total_price / total_nights, 2),
                    'total_price': float(total_price),
                    'available_from': check_in_str,
                    'available_to': check_out_str,
                    'total_night': total_nights
                })
        return jsonify(results), 200
