from datetime import timedelta

from models import Availability


def check_property_availability(db, property_id, check_in, check_out):
    """
    Checks if a property has available and unreserved dates for the given range.
    Returns a tuple: (success: bool, availabilities: list, message: str)
    """
    total_nights = (check_out - check_in).days
    if total_nights <= 0:
        return False, [], 'Check-out must be after check-in'

    date_range = [check_in + timedelta(days=i) for i in range(total_nights)]

    availabilities = db.query(Availability).filter(
        Availability.property_id == property_id,
        Availability.date.in_(date_range),
        Availability.is_available == True,
        Availability.is_reserved == False,
        Availability.is_blocked == False
    ).all()

    if len(availabilities) != total_nights:
        return False, [], 'Some dates are not available for booking'

    return True, availabilities, 'Dates are available'