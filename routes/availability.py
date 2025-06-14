
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from models import Availability, User, Property
from database import get_db


availability_bp = Blueprint('availability', __name__)


@availability_bp.route('/availability', methods=['POST'])
@jwt_required()
def add_availability():
    """
    Any user who has the host role and has created a property (is the
    property owner) can define availability and price for different dates.
    :return: Success msg If it was successful, otherwise error.
    """
    user_id = get_jwt_identity()

    with get_db() as db:
        user = db.query(User).get(user_id)

        if user.role != 'host':
            return jsonify({'error': 'Only hosts can define availability'}), 403

        data = request.get_json()
        property_id = data.get('property_id')
        date_str = data.get('date')
        price = data.get('price')
        is_available = data.get('is_available', True)

        if not property_id or not date_str or not price:
            return jsonify({'error': 'Missing required fields'}), 400

        prop = db.query(Property).filter_by(id=property_id, host_id=user.id).first()

        if not prop:
            return jsonify({'error': 'Property not found or not owned by user'}), 403

        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

        exists = db.query(Availability).filter_by(property_id=property_id, date=date_obj).first()
        if exists:
            return jsonify({'error': 'Availability already exists for this date'}), 409

        availability = Availability(
            property_id=property_id,
            date=date_obj,
            price=price,
            is_available=is_available
        )

        db.add(availability)
        db.commit()

    return jsonify({'msg': 'Availability added successfully'}), 201

