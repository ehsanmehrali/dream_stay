import enum
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Date, Enum, Numeric, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship


Base = declarative_base()


class User(Base):
    """
    This class defines the structure of the users table. Each user can have different roles.
    """
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)
    first_name = Column(String)
    last_name = Column(String)
    phone = Column(String)
    address = Column(String)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # # ONE TO MANY: A user can own multiple properties (if they are a host).
    properties = relationship('Property', back_populates='host')

    # ONE TO MANY: A user (as a guest) can have multiple bookings.
    bookings = relationship('Booking', back_populates='user')


class Property(Base):
    """
    This class defines the structure of the properties table.
    Same host, same property title and location are prohibited.
    """
    __tablename__ = 'properties'

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(String)
    location = Column(String, nullable=False)
    host_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    is_approved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Prevent duplicate storage
    __table_args__ = (
        UniqueConstraint('title', 'location', 'host_id', name='uq_title_location_host'),
    )

    # MANY TO ONE: Each property is owned by one host (user).
    host = relationship('User', back_populates='properties')

    # ONE TO MANY: A property can be booked multiple times.
    bookings = relationship('Booking', back_populates='property')


class Availability(Base):
    """ Availability per date for a specific property (price & availability flags). """
    __tablename__ = 'availability'

    id = Column(Integer, primary_key=True)
    property_id = Column(Integer, ForeignKey('properties.id'), nullable=False)
    date = Column(Date, nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    is_reserved = Column(Boolean, default=False, nullable=False)
    is_available = Column(Boolean, default=False, nullable=False)


class BookingStatus(enum.Enum):
    """ It holds the names of the three main reservation modes. """
    pending = 'pending'
    confirmed = 'confirmed'
    cancelled = 'cancelled'


class Booking(Base):
    """ This class defines the structure of the bookings table. """
    __tablename__ = 'bookings'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    property_id = Column(Integer, ForeignKey('properties.id'), nullable=False)
    check_in = Column(Date, nullable=False)
    check_out = Column(Date, nullable=False)
    total_price = Column(Numeric(10, 2), nullable=False)
    status = Column(Enum(BookingStatus), nullable=False, default=BookingStatus.pending)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    voucher_code = Column(String, unique=True)
    cancellation_policy = Column(String)

    # MANY TO ONE: Each booking is made by one user.
    user = relationship('User', back_populates='bookings')

    # MANY TO ONE: Each booking is for one property.
    property = relationship('Property', back_populates='bookings')


class Commission(Base):
    """
    This class contains the table structure of commission or
    (service fee) values for hosts and customers.
    """
    __tablename__ = 'commissions'

    id = Column(Integer, primary_key=True)
    property_id = Column(Integer, ForeignKey('properties.id'))
    percentage = Column(Numeric(10, 2), nullable=False)
    defined_by_admin_id = Column(Integer, ForeignKey('users.id'))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # MANY TO ONE: Each commission belongs to one property.
    property = relationship('Property')

    # MANY TO ONE: Each commission is defined by one admin (user).
    admin = relationship('User')