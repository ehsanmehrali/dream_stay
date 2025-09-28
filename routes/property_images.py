from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func
from database import get_db
from models import Property, PropertyImage
from utils.images import process_image
from config import Config
import os

images_bp = Blueprint('images', __name__, url_prefix='/properties')


def _ensure_owner(db, property_id, user_id):
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        return None, ('property not found', 404)
    if prop.host_id != user_id:
        return None, ('forbidden', 403)
    return prop, None

@images_bp.route('/<int:property_id>/images', methods=['GET'])
def list_images(property_id):
    with get_db() as db:
        imgs = (
            db.query(PropertyImage)
            .filter(PropertyImage.property_id == property_id)
            .order_by(PropertyImage.is_cover.desc(), PropertyImage.sort_order.asc(), PropertyImage.id.asc())
            .all()
        )
        return jsonify([{
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
        } for i in imgs]), 200

@images_bp.route('/<int:property_id>/images', methods=['POST'])
@jwt_required()
def upload_images(property_id):
    user_id = get_jwt_identity()
    files = request.files.getlist('files') or []
    if not files:
        return jsonify({'error':'no files provided (use multipart/form-data with "files" field)'}), 400

    with get_db() as db:
        prop, err = _ensure_owner(db, property_id, user_id)
        if err: return jsonify({'error': err[0]}), err[1]

        count_now = db.query(func.count(PropertyImage.id)).filter(PropertyImage.property_id == property_id).scalar()
        if count_now + len(files) > Config.IMAGE_MAX_COUNT:
            return jsonify({'error': f'max {Config.IMAGE_MAX_COUNT} images per property'}), 400

        created = []
        for idx, f in enumerate(files):
            try:
                meta = process_image(f, property_id)
            except Exception as e:
                return jsonify({'error': f'file {idx+1}: {e}'}), 400

            img = PropertyImage(
                property_id=property_id,
                storage_key=meta['rel_medium'],
                url=meta['url'],
                thumb_url=meta['thumb_url'],
                large_url=meta['large_url'],
                width=meta['width'],
                height=meta['height'],
                bytes=meta['bytes'],
                format=meta['format'],
                sort_order=count_now + idx
            )

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
def update_image(property_id, image_id):
    user_id = get_jwt_identity()
    payload = request.get_json(silent=True) or {}
    with get_db() as db:
        prop, err = _ensure_owner(db, property_id, user_id)
        if err: return jsonify({'error': err[0]}), err[1]

        img = db.query(PropertyImage).filter(PropertyImage.id==image_id, PropertyImage.property_id==property_id).first()
        if not img:
            return jsonify({'error':'image not found'}), 404

        if 'is_cover' in payload and payload['is_cover'] == True:
            # Uncover the rest of the images.
            db.query(PropertyImage).filter(PropertyImage.property_id==property_id, PropertyImage.id!=image_id)\
                .update({PropertyImage.is_cover: False})
            img.is_cover = True

        if 'sort_order' in payload and isinstance(payload['sort_order'], int):
            img.sort_order = payload['sort_order']

        if 'caption' in payload:
            img.caption = (payload['caption'] or '')[:256]
        if 'alt_text' in payload:
            img.alt_text = (payload['alt_text'] or '')[:256]

        db.commit()
        return jsonify({'ok': True}), 200

@images_bp.route('/<int:property_id>/images/<int:image_id>', methods=['DELETE'])
@jwt_required()
def delete_image(property_id, image_id):
    user_id = get_jwt_identity()
    with get_db() as db:
        prop, err = _ensure_owner(db, property_id, user_id)
        if err: return jsonify({'error': err[0]}), err[1]

        img = db.query(PropertyImage).filter(PropertyImage.id==image_id, PropertyImage.property_id==property_id).first()
        if not img:
            return jsonify({'error':'image not found'}), 404

        # Delete files from disk
        for url_field in ['url','thumb_url','large_url']:
            rel = getattr(img, url_field).replace(Config.IMAGE_BASE_URL + '/', '')
            path = os.path.join(Config.IMAGE_UPLOAD_DIR, rel)
            try:
                if os.path.exists(path): os.remove(path)
            except Exception:
                pass

        db.delete(img)
        db.commit()
        return jsonify({'ok': True}), 200