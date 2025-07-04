
from datetime import datetime, date, timezone

from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity

from utils.availability import check_property_availability
from utils.pdf_generator import generate_voucher_pdf
from models import User, Property, Booking
from database import get_db


booking_bp = Blueprint('booking', __name__)


@booking_bp.route('/bookings', methods=['POST'])
@jwt_required()
def create_booking():
    user_id = get_jwt_identity()
    data = request.get_json()

    check_in_str = data.get('check_in')
    check_out_str = data.get('check_out')
    property_id = data.get('property_id')
    guest_info = data.get('guest_info')

    if not all([check_in_str, check_out_str, property_id, guest_info]):
        return jsonify({'error': 'Missing required fields'}), 400

    required_fields = ['first_name', 'last_name', 'email', 'phone']
    missing = [field for field in required_fields if field not in guest_info]

    if missing:
        return jsonify({'error': f'Missing guest fields: {", ".join(missing)}'}), 400

    try:
        check_in = datetime.strptime(check_in_str, "%Y-%m-%d").date()
        check_out = datetime.strptime(check_out_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

    if check_in >= check_out:
        return jsonify({'error': 'Check-out must be after check-in'}), 400

    if check_in < date.today():
        return jsonify({'error': 'Check-in date cannot be in the past'}), 400

    with get_db() as db:
        user = db.query(User).get(user_id)
        if not user or user.role != 'guest':
            return jsonify({'error': 'Only guests can make bookings'}), 403

        prop = db.query(Property).get(property_id)
        if not prop or not prop.is_approved:
            return jsonify({'error': 'Property not found or not approved'}), 404

        success, availabilities, _ = check_property_availability(db, property_id, check_in, check_out)
        if not success:
            return jsonify({'error': 'Some dates are not available for booking'}), 409

        total_price = sum([float(a.price) for a in availabilities])

        booking = Booking(
            user_id=user.id,
            property_id=property_id,
            check_in=check_in,
            check_out=check_out,
            total_price=total_price,
            status='confirmed',
            created_at = datetime.now(timezone.utc)
        )
        db.add(booking)

        for a in availabilities:
            a.is_reserved = True

        db.commit()

        pdf_buffer = generate_voucher_pdf(booking, guest_info, prop)
        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=f"voucher_{booking.id}.pdf",
            mimetype='application/pdf'
        )
