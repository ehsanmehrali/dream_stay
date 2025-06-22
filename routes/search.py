
from datetime import datetime, timedelta
from flask import request, jsonify
from flask_jwt_extended import jwt_required
from flask import Blueprint

from models import Property, Availability
from database import get_db


search_bp = Blueprint('search', __name__)


@search_bp.route('/search', methods=['GET'])
def search_properties():
    location = request.args.get('location')
    check_in_str = request.args.get('check_in')
    check_out_str = request.args.get('check_out')

    if not location or not check_in_str or not check_out_str:
        return jsonify({'error': 'location, check_in, and check_out are required'}), 400

    try:
        check_in = datetime.strptime(check_in_str, "%Y-%m-%d").date()
        check_out = datetime.strptime(check_out_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

    if check_in >= check_out:
        return jsonify({'error': 'check_out must be after check_in'}), 400

    total_nights = (check_out - check_in).days
    # Create a list of all stay dates
    date_range = [check_in + timedelta(days=i) for i in range(total_nights)]

    with get_db() as db:
        # Getting all properties in target location
        properties = db.query(Property).filter_by(location=location, is_approved=True).all()
        results = []

        for prop in properties:
            availability_records = db.query(Availability).filter(
                Availability.property_id == prop.id,
                Availability.date.in_(date_range),
                Availability.is_available == True,
                Availability.is_reserved == False,
                Availability.is_blocked == False
            ).all()

            if len(availability_records) == total_nights:
                total_price = sum([a.price for a in availability_records])
                results.append({
                    'property_id': prop.id,
                    'title': prop.title,
                    'location': prop.location,
                    'price_per_night': round(total_price / total_nights, 2),
                    'total_price': float(total_price),
                    'available_from': check_i
