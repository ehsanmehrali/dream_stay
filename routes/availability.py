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



@availability_bp.route('/availability/bulk-update', methods=['PUT'])
@jwt_required()
def bulk_update_availability():
    """
    Allows a host to update multiple availability records in one request.
    Only future or today dates are eligible for update.
    Already reserved dates are not editable.
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
        if not user or user.role != 'host':
            return jsonify({'error': 'Only hosts can update availability'}), 403
        # Check Ownership
        prop = db.query(Property).filter_by(id=property_id, host_id=user.id).first()
        if not prop:
            return jsonify({'error': 'Property not found or not owned by user'}), 403

        today = date.today()
        update_results = []

        for date_str, item in dates_dict.items():
            try:
                item_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                update_results.append({'error': 'Invalid date format', 'date': date_str})
                continue
            # Past dates not allowed
            if item_date < today:
                update_results.append({'error': 'Cannot update past dates', 'date': date_str})
                continue

            availability = db.query(Availability).filter_by(
                property_id=property_id,
                date=item_date
            ).first()

            if not availability:
                update_results.append({'error': 'Availability not found', 'date': date_str})
                continue

            if availability.is_reserved:
                update_results.append({'error': 'Cannot update reserved date', 'date': date_str})
                continue

            # Apply updates
            if 'price' in item:
                try:
                    availability.price = float(item['price'])
                except ValueError:
                    update_results.append({'error': 'Invalid price format', 'date': date_str})
                    continue

            if 'is_available' in item:
                if not isinstance(item['is_available'], bool):
                    update_results.append({'error': 'is_available must be boolean', 'date': date_str})
                    continue
                availability.is_available = item['is_available']

            update_results.append({'msg': 'Availability updated', 'date': date_str})

        db.commit()
        return jsonify(update_results), 200



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