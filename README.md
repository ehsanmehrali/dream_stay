# DreamStay API

A lightweight **Flask** + **SQLAlchemy** backend for a vacation-rental style app. It supports **JWT auth**, 
**property management**, **availability & search**, **bookings with PDF voucher generation**, and **image uploads**
(with optional Cloudflare R2 object storage). CORS is enabled for configurable front‑end origins.

> Health check: `GET /` → `{"status":"DreamStay is running"}`

---

## Features

- 🔐 **Authentication**: Register & login, JWT access tokens (`flask-jwt-extended`).
- 🏠 **Properties**: Create properties (title, description, location).
- 📅 **Availability**: Create/modify availability; bulk updates; prevents edits to reserved dates.
- 🔎 **Search**: Filter properties by date range; optional pagination.
- 🧾 **Bookings**: Create bookings and receive a **PDF voucher** (via `reportlab`).
- 🖼️ **Images**: Upload/manage property images (local disk or **Cloudflare R2**); cover image + ordering.
- 🌐 **CORS**: Allow-list of origins via `ALLOWED_ORIGINS` (comma‑separated).
- 🗄️ **Database**: SQLAlchemy ORM; auto `create_all` on startup.

---

## Tech Stack

- Python 3.12+
- Flask 3.x, Flask‑JWT‑Extended, Flask‑CORS
- SQLAlchemy 2.x
- ReportLab (PDF vouchers)
- Pillow / pillow-heif (image processing)
- Optional: Cloudflare R2 via `boto3` (S3-compatible)

---

## Project Structure

```
.
├── app.py
├── config.py
├── database.py
├── models.py
├── routes/
│   ├── auth.py
│   ├── properties.py
│   ├── availability.py
│   ├── search.py
│   ├── booking.py
│   └── property_images.py
├── utils/
│   ├── availability.py
│   ├── images.py
│   ├── pdf_generator.py
│   └── r2.py
├── requirements.txt
└── (dreamstay.db, .env)  # local dev artifacts
```

---

## Quick Start

### 1) Clone & set up env
```bash
python -m venv .venv
source .venv/bin/activate  # (Windows: .venv\Scripts\activate)
pip install -r requirements.txt
cp .env.example .env  # if provided; otherwise create it (see vars below)
```

### 2) Configure environment
Create `.env` with at least:
```
SQLALCHEMY_DATABASE_URI=sqlite:///dreamstay.db
SECRET_KEY=change-me
DEBUG=True
ALLOWED_ORIGINS=http://localhost:5173
```

For Cloudflare R2 uploads (optional):
```
USE_R2=true
R2_ACCOUNT_ID=...
R2_ACCESS_KEY_ID=...
R2_SECRET_ACCESS_KEY=...
R2_BUCKET_NAME=...
# Provided by Cloudflare dashboard (public read):
R2_PUBLIC_BASE_URL=https://<your-public-bucket-domain>
# S3 endpoint used for uploads/deletes (falls back automatically):
R2_ENDPOINT=https://<account_id>.r2.cloudflarestorage.com
```

Other image limits:
```
IMAGE_MAX_COUNT=30
IMAGE_MAX_MB=15
```

### 3) Run
```bash
# Dev
python app.py  # defaults to Flask built-in server

# Production example
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```
The app auto-creates tables on start.

---

## API Reference (v1)

Unless stated, all JSON requests/returns use `application/json`.
Protected endpoints require `Authorization: Bearer <token>`.

### Auth
- **POST `/register`**
  - Body: `{ "email", "password", "role"="guest", "first_name", "last_name", "phone", "address" }`
  - Returns: user info or error.

- **POST `/login`**
  - Body: `{ "email", "password" }`
  - Returns: `{ "access_token": "<JWT>" }` on success.

### Profile
- **PUT `/profile`** (auth)
  - Body (any subset): `{ "first_name", "last_name", "phone", "address" }`
  - Returns: `{"msg":"Profile updated successfully"}`

### Properties
- **POST `/properties`** (auth; host)
  - Body: `{ "title", "description", "location" }`
  - Returns: `{"msg":"Property created successfully","property_id": <id>}`

### Availability
- **GET `/availability/property/<property_id>`** (auth; host)
  - Returns availability items for a property.

- **POST `/availability`** (auth; host)
  - Create/update a single date’s availability for a property.

- **PUT `/availability/bulk-update`** (auth; host)
  - Bulk update multiple dates. Past dates are ignored; reserved dates are immutable.

### Search
- **GET `/search`**
  - Query params:  
    - `check_in=YYYY-MM-DD`  
    - `check_out=YYYY-MM-DD`  
    - Optional: `offset`, `limit`
  - Returns properties with per-night `dates` map and `total_price` when fully available.

### Bookings
- **POST `/bookings`** (auth; guest)
  - Body: `{ "property_id", "check_in", "check_out", "guest_info": {...} }`
  - On success: reserves nights, creates a booking, and returns a **PDF voucher** download (`application/pdf`).

### Property Images
- Base prefix: `/properties`
- **GET `/properties/<property_id>/images`**
- **POST `/properties/<property_id>/images`** (auth; host)
  - `multipart/form-data` with one or more `files` fields.  
  - Server enforces `IMAGE_MAX_COUNT` and `IMAGE_MAX_MB` per file.
  - If `USE_R2=true`, images stored in Cloudflare R2; otherwise stored locally.
- **PATCH `/properties/<property_id>/images/<image_id>`** (auth; host)
  - Update metadata (e.g., set cover or sort order).  
- **DELETE `/properties/<property_id>/images/<image_id>`** (auth; host)

> Note: Exact response shapes may include additional fields (ids, urls, metadata) and can evolve.

---

## Configuration

| Variable | Required | Default | Notes |
|---|---|---|---|
| `SQLALCHEMY_DATABASE_URI` | ✅ | — | e.g., `sqlite:///dreamstay.db` |
| `SECRET_KEY` | ✅ | — | Flask & JWT signing secret |
| `DEBUG` | ❌ | `False` | Development flag |
| `ALLOWED_ORIGINS` | ❌ | `http://localhost:5173` | Comma‑separated list for CORS |
| `USE_R2` | ❌ | `false` | Enable Cloudflare R2 |
| `R2_ACCOUNT_ID` | when R2 | — | Cloudflare account |
| `R2_ACCESS_KEY_ID` | when R2 | — | S3 access key |
| `R2_SECRET_ACCESS_KEY` | when R2 | — | S3 secret |
| `R2_BUCKET_NAME` | when R2 | — | Public bucket name |
| `R2_ENDPOINT` | when R2 | computed | S3 endpoint for SDK |
| `R2_PUBLIC_BASE_URL` | when R2 | — | Public base URL for serving images |
| `IMAGE_MAX_COUNT` | ❌ | `30` | Max images per property |
| `IMAGE_MAX_MB` | ❌ | `15` | Max per-file size (MB) |

---

## Development Notes

- **CORS**: Configured as `CORS(app, resources={r"/*": {"origins": ALLOWED_ORIGINS}}, methods=["GET","HEAD","OPTIONS"], allow_headers=["Content-Type","Accept","Authorization"])`.
- **DB Sessions**: Managed via `database.get_db()` context manager; engine created from `SQLALCHEMY_DATABASE_URI`.
- **Migrations**: Not configured; schema is created via `Base.metadata.create_all(...)` on startup.
- **PDF Vouchers**: `utils/pdf_generator.py` renders booking vouchers.
- **Images**: `utils/images.py` does validation/metadata extraction; if `USE_R2=true`, `utils/r2.py` handles S3 operations.

---

## Running Tests

> No test suite included. You can add `pytest` and create tests under `tests/` to validate models and routes.

---

## Deployment

- Recommend `gunicorn` behind a reverse proxy (NGINX).
- Ensure environment secrets are set and `DEBUG=False`.
- If using Cloudflare R2, make the bucket publicly readable for `R2_PUBLIC_BASE_URL`.

---

## License

Add your preferred license (e.g., MIT) as `LICENSE`.
