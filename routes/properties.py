
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy.exc import IntegrityError

from models import Property, User
from database import get_db


properties_bp = Blueprint('properties', __name__)


@properties_bp.route('/properties', methods=['POST'])
@jwt_required()
def create_property():
    """
    It creates 'Property' for who have the 'host' role.
    :return: Success msg and property id If it was successful, otherwise error.
    """
    user_id = get_jwt_identity()

    with get_db() as db:
        user = db.query(User).get(user_id)

        if not user or user.role != 'host':
            return jsonify({'error': 'Only host can create properties'}), 403

        data = request.get_json()
        title = data.get('title')
        description = data.get('description')
        location = data.get('location')

        if not title or not location:
            return jsonify({'error': 'Title and location are required'}), 400

        # Check for existing properties from same host
        existing = db.query(Property).filter_by(
            title=data['title'],
            location=data['location'],
            host_id=user.id
        ).first()

        if existing:
            return jsonify({'msg': 'Property already exists'}), 409

        prop = Property(
            title=title,
            description=description,
            location=location,
            host_id=user.id
        )
        # IntegrityError handler (race condition)
        try:
            db.add(prop)
            db.commit()
        except IntegrityError:
            db.rollback()
            return jsonify({'msg': 'Duplicate property not allowed'}), 409

        return jsonify({'msg': 'Property created successfully', 'property_id': prop.id}), 201


