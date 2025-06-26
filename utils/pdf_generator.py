import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader


def generate_voucher_pdf(booking, guest_info, property_):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)

    width, height = A4

    # Add logo (path to physical file or BytesIO)
    logo_path = "static/logo.png"
    try:
        p.drawImage(ImageReader(logo_path), 50, height - 100, width=120, height=50, mask='auto')
    except:
        pass

    # title
    p.setFont("Helvetica-Bold", 18)
    p.drawString(200, height - 80, "Booking Voucher")

    # divider line
    p.line(50, height - 100, width - 50, height - 100)

    p.setFont("Helvetica", 12)
    y = height - 130

    lines = [
        f"Booking ID: {booking.id}",
        f"Guest: {guest_info.get('first_name', '')} {guest_info.get('last_name', '')}",
        f"Email: {guest_info.get('email', '')}",
        f"Phone: {guest_info.get('phone', '')}",
    ]

    address = guest_info.get('address', {})
    full_address = f"{address.get('street', '')}, {address.get('city', '')}, {address.get('province', '')} - {address.get('postal_code', '')}"
    lines.append(f"Address: {full_address}")

    lines.extend([
        f"Property: {property_.title} - {property_.location}",
        f"Check-in: {booking.check_in}",
        f"Check-out: {booking.check_out}",
        f"Total Price: ${booking.total_price:.2f}"
    ])

    for line in lines:
        p.drawString(70, y, line)
        y -= 20

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer
