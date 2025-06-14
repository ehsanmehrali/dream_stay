from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required

from models import User
from database import get_db


profile_bp = Blueprint('profile', __name__)


@profile_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """
    Update user personal information.
    :return: Success msg, otherwise error.
    """
    user_id = get_jwt_identity()

    with get_db() as db:
        user = db.query(User).get(user_id)

        if not user:
            return jsonify({"error": "User not found"}), 404

        data = request.get_json()
        user.first_name = data.get('first_name', user.first_name)
        user.last_name = data.get('last_name', user.last_name)
        user.phone = data.get('phone', user.phone)
        user.address = data.get('address', user.address)

        db.commit()

    return jsonify({"msg": "Profile updated successfully"})