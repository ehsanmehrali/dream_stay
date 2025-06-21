from datetime import date

from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from models import Availability, User, Property
from database import get_db


availability_bp = Blueprint('availability', __name__)


def parse_valid_dates(dates_dict):
    today = date.today()
    valid_items = []
    input_dates = set()

    # Validate input and build valid items list
    for date_str, item in dates_dict.items():
        try:
            item_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            # Past dates are ignored.
            if item_date < today:
                continue  # status code 201 -> []
            price = item.get('price')
            # Dates without a price are ignored
            if price is None:
                continue
            is_available = item.get('is_available', False)
            valid_items.append({
                'date_str': date_str,
                'parsed_date': item_date,
                'price': price,
                'is_available': is_available
            })
            input_dates.add(item_date)
        except ValueError:
            continue

    return valid_items, input_dates


@availability_bp.route('/availability', methods=['POST'])
@jwt_required()
def add_availability():
    """
    Hosts can define availability and price for different dates.
    Accepts a property_id and a dictionary of dates where each key is a date string,
    and the value is an object containing price and (optional) is_available.
    Only future or today dates will be processed.
    """
    user_id = get_jwt_identity()
    data = request.get_json()

    if not data or 'property_id' not in data or 'dates' not in data:
        return jsonify({'error': 'property_id and dates are required'}), 400

    property_id = data['property_id']
    dates_dict = data['dates']

    with get_db() as db:
        user = db.query(User).get(user_id)
        # Check user's roll
        if user.role != 'host':
            return jsonify({'error': 'Only hosts can define availability'}), 403

        # Check Ownership
        prop = db.query(Property).filter_by(id=property_id, host_id=user.id).first()
        if not prop:
            return jsonify({'error': 'Property not found or not owned by user'}), 403

        valid_items, input_dates = parse_valid_dates(dates_dict)

        # Query for check the existing dates in DB
        existing = db.query(Availability.date).filter(
            Availability.property_id == property_id,
            Availability.date.in_(input_dates)
        ).all()
        # Converting query result(existing) to a set.
        existing_dates = {e.date for e in existing}

        # Preventing duplicates
        results = []
        for item in valid_items:
            if item['parsed_date'] in existing_dates: # status code 201
                results.append({
                    'error': 'Availability already exists',
                    'date': item['date_str']
                })
                continue

            availability = Availability(
                property_id=property_id,
                date=item['parsed_date'],
                price=item['price'],
                is_available=item['is_available'],
                is_blocked=item.get('is_blocked', False)
            )
            db.add(availability)
            results.append({
                'msg': 'Availability created',
                'date': item['date_str'],
                'is_available': item['is_available']
            })

        db.commit()
        return jsonify(results), 201



@availability_bp.route('/availability/<int:availability_id>', methods=['PUT'])
@jwt_required()
def update_availability(availability_id):
    """
    Allows hosts to update the availability entry (price, availability, blocked status)
    only if the date is today or in the future and not already reserved.
    """
    data = request.get_json()
    user_id = get_jwt_identity()

    with get_db() as db:
        user = db.query(User).get(user_id)

        availability = db.query(Availability).get(availability_id)
        if not availability:
            return jsonify({'error': 'Availability not found'}), 404

        # Check ownership of the related property
        prop = db.query(Property).get(availability.property_id)
        if not prop or prop.host_id != user.id:
            return jsonify({'error': 'Unauthorized access to this availability'}), 403

        # Disallow editing reserved dates
        if availability.is_reserved:
            return jsonify({'error': 'Cannot update a reserved date.'}), 400

        # Disallow editing past dates
        if availability.date < date.today():
            return jsonify({'error': 'Cannot update past dates.'}), 400

        # Validate and apply updates
        if 'is_available' in data:
            if not isinstance(data['is_available'], bool):
                return jsonify({'error': 'is_available must be a boolean'}), 400
            availability.is_available = data['is_available']

        if 'is_blocked' in data:
            if not isinstance(data['is_blocked'], bool):
                return jsonify({'error': 'is_blocked must be a boolean'}), 400
            availability.is_blocked = data['is_blocked']

        if 'price' in data:
            try:
                availability.price = float(data['price'])
            except (ValueError, TypeError):
                return jsonify({'error': 'Invalid price format'}), 400

        db.commit()
        return jsonify({'msg': 'Availability updated successfully'}), 200




@availability_bp.route('/availability/property/<int:property_id>', methods=['GET'])
@jwt_required()
def get_property_availability(property_id):
    """
    Return list of availability records for a given property.
    Only the host who owns the property can view them.
    """
    user_id = get_jwt_identity()

    with get_db() as db:
        prop = db.query(Property).filter_by(id=property_id, host_id=user_id).first()

        # Property ownership verification
        if not prop:
            return jsonify({'error': 'Property not found or not owned by user'}), 403

        # Getting availability records
        availability_list = (
            db.query(Availability)
            .filter_by(property_id=property_id)
            .order_by(Availability.date)
            .all()
        )

        results = [
            {
                'id': avail.id,
                'date': avail.date.isoformat(),
                'price': float(avail.price),
                'is_available': avail.is_available,
                'is_reserved': avail.is_reserved
            }
            for avail in availability_list
        ]

        return jsonify(results), 200