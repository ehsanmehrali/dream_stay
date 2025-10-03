
from __future__ import annotations

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from sqlalchemy import func
from database import get_db
from models import Property, PropertyImage
from utils.images import process_image
from config import Config
from utils.r2 import r2_client  # Only used when USE_R2=true
from typing import Optional

images_bp = Blueprint('images', __name__, url_prefix='/properties')


# ---------- helpers ----------

def _current_user_id() -> Optional[int]:
    """
    Reads user_id from JWT:
    - If you have provided an additional 'id' claim when creating the token → returns the same.
    - Otherwise converts identity (which is usually a string) to int.
    """
    claims = get_jwt()
    uid = claims.get("id")
    if uid is not None:
        return int(uid)
    ident = get_jwt_identity()
    try:
        return int(ident) if ident is not None else None
    except (TypeError, ValueError):
        return None


def _ensure_owner(db, property_id: int, user_id: int):
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        return None, ('property not found', 404)
    if prop.host_id != user_id:
        return None, ('forbidden', 403)
    return prop, None


def _files_from_request():
    """Flexibility for some clients sending files[]."""
    files = request.files.getlist('files')
    if not files:
        files = request.files.getlist('files[]')
    return files or []


def _url_to_key(url: str) -> Optional[str]:
    """
    Extracts the object key from the public URL.
    For R2 we use R2_PUBLIC_BASE_URL.
    """
    base = (Config.R2_PUBLIC_BASE_URL or '').rstrip('/')
    if url and url.startswith(base + '/'):
        return url[len(base) + 1:]
    return None


# ---------- routes ----------

@images_bp.route('/<int:property_id>/images', methods=['GET'])
def list_images(property_id: int):
    with get_db() as db:
        imgs = (
            db.query(PropertyImage)
            .filter(PropertyImage.property_id == property_id)
            .order_by(
                PropertyImage.is_cover.desc(),
                PropertyImage.sort_order.asc(),
                PropertyImage.id.asc()
            )
            .all()
        )
        return jsonify([
            {
                'id': i.id,
                'url': i.url,
                'thumb_url': i.thumb_url,
                'large_url': i.large_url,
                'is_cover': i.is_cover,
                'sort_order': i.sort_order,
                'caption': i.caption,
                'alt_text': i.alt_text,
                'width': i.width,
                'height': i.height,
                'bytes': i.bytes,
                'created_at': i.created_at.isoformat()
            } for i in imgs
        ]), 200


@images_bp.route('/<int:property_id>/images', methods=['POST'])
@jwt_required()
def upload_images(property_id: int):
    user_id = _current_user_id()
    if user_id is None:
        return jsonify({'error': 'unauthorized'}), 401

    files = _files_from_request()
    if not files:
        return jsonify({'error': 'no files provided (use multipart/form-data with key "files")'}), 400

    with get_db() as db:
        prop, err = _ensure_owner(db, property_id, user_id)
        if err:
            return jsonify({'error': err[0]}), err[1]

        count_now = db.query(func.count(PropertyImage.id)).filter(
            PropertyImage.property_id == property_id
        ).scalar()

        max_count = getattr(Config, "IMAGE_MAX_COUNT", 20)
        if count_now + len(files) > max_count:
            return jsonify({'error': f'max {max_count} images per property'}), 400

        created = []
        for idx, f in enumerate(files):
            try:
                meta = process_image(f, property_id)  # It saves itself on R2 or locally depending on USE_R2
            except Exception as e:
                return jsonify({'error': f'file {idx+1}: {e}'}), 400

            img = PropertyImage(
                property_id=property_id,
                storage_key=meta['rel_medium'],  # Medium version (relative) key for reference
                url=meta['url'],
                thumb_url=meta['thumb_url'],
                large_url=meta['large_url'],
                width=meta['width'],
                height=meta['height'],
                bytes=meta['bytes'],
                format=meta['format'],
                sort_order=count_now + idx
            )

            # If the first image of this property is → cover
            if count_now == 0 and idx == 0:
                img.is_cover = True

            db.add(img)
            db.flush()

            created.append({
                'id': img.id,
                'url': img.url,
                'thumb_url': img.thumb_url,
                'large_url': img.large_url,
                'is_cover': img.is_cover,
                'sort_order': img.sort_order
            })

        db.commit()
        return jsonify(created), 201


@images_bp.route('/<int:property_id>/images/<int:image_id>', methods=['PATCH'])
@jwt_required()
def update_image(property_id: int, image_id: int):
    user_id = _current_user_id()
    if user_id is None:
        return jsonify({'error': 'unauthorized'}), 401

    payload = request.get_json(silent=True) or {}

    with get_db() as db:
        prop, err = _ensure_owner(db, property_id, user_id)
        if err:
            return jsonify({'error': err[0]}), err[1]

        img = db.query(PropertyImage).filter(
            PropertyImage.id == image_id,
            PropertyImage.property_id == property_id
        ).first()
        if not img:
            return jsonify({'error': 'image not found'}), 404

        if payload.get('is_cover') is True:
            # Take them all out of the cover and cover this one
            db.query(PropertyImage).filter(
                PropertyImage.property_id == property_id,
                PropertyImage.id != image_id
            ).update({PropertyImage.is_cover: False})
            img.is_cover = True

        if isinstance(payload.get('sort_order'), int):
            img.sort_order = payload['sort_order']

        if 'caption' in payload:
            img.caption = (payload['caption'] or '')[:256]
        if 'alt_text' in payload:
            img.alt_text = (payload['alt_text'] or '')[:256]

        db.commit()
        return jsonify({'ok': True}), 200


@images_bp.route('/<int:property_id>/images/<int:image_id>', methods=['DELETE'])
@jwt_required()
def delete_image(property_id: int, image_id: int):
    user_id = _current_user_id()
    if user_id is None:
        return jsonify({'error': 'unauthorized'}), 401

    with get_db() as db:
        prop, err = _ensure_owner(db, property_id, user_id)
        if err: return jsonify({'error': err[0]}), err[1]

        img = db.query(PropertyImage).filter(
            PropertyImage.id==image_id,
            PropertyImage.property_id==property_id
        ).first()
        if not img:
            return jsonify({'error':'image not found'}), 404

        s3 = r2_client()
        for field in ['url','thumb_url','large_url']:
            k = _url_to_key(getattr(img, field))
            if k:
                try:
                    s3.delete_object(Bucket=Config.R2_BUCKET_NAME, Key=k)
                except Exception:
                    pass

        db.delete(img)
        db.commit()
        return jsonify({'ok': True}), 200
