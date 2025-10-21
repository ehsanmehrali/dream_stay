from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Property, User
from database import get_db

property_bp = Blueprint('property', __name__)

@property_bp.route('/host/properties', methods=['GET'])
@jwt_required()
def get_host_properties():
    user_id = get_jwt_identity()

    with get_db() as db:
        user = db.query(User).filter_by(id=user_id).first()

        if not user or user.role != 'host':
            return jsonify({'error': 'Access forbidden: user is not a host'}), 403

        properties = db.query(Property).filter_by(host_id=user.id).all()

        return jsonify({
            'host_id': user.id,
            'properties': [
                {
                    'id': p.id,
                    'title': p.title,
                    'location': p.location,
                    'description': p.description,
                    'is_activated': p.is_approved
                }
                for p in properties
            ]
        }), 200
