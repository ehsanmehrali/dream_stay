
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from sqlalchemy.exc import IntegrityError
import datetime
import bcrypt

from database import get_db
from models import User


auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Registers a new user (host or guest) with email and password.
    :return: Success msg, otherwise error.
    """
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    role = data.get('role', 'guest')
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    phone = data.get('phone')
    address = data.get('address')

    if not email or not password:
        return jsonify({'error': 'Missing fields'}), 400

    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    with get_db() as db:
        user = User(
            email=email,
            password_hash=hashed_pw.decode('utf-8'),
            role=role,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            address=address
        )
        try:
            db.add(user)
            db.commit()
            return jsonify({'msg': 'User registered successfully'}), 201
        except IntegrityError:
            db.rollback()
            return jsonify({'error': 'Username or email already exists'}), 409


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Login a user (host or guest or admin) with email and password.
    :return: Access token(JWT) and user's role, otherwise error.
    """
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({
            'error': 'Invalid credentials'
        }), 400

    with get_db() as db:
        user = db.query(User).filter_by(email=email).first()

        if not user:
            return jsonify({
                'error': 'Invalid credentials'
            }), 401

        if not bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
            return jsonify({
                'error': 'Invalid credentials'
            }), 401

        access_token = create_access_token(
            identity=str(user.id),
            additional_claims={"id": user.id, "role": user.role},
            expires_delta=datetime.timedelta(hours=2)
        )

    return jsonify({
        'access_token': access_token,
        'role': user.role
    }), 200
