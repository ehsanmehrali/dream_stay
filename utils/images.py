import io, uuid
from PIL import Image, ImageOps, Image as PILImage
from config import Config
from utils.r2 import r2_client

def _save_variant_to_bytes(img: PILImage.Image, max_px: int):
    out = img.copy()
    out.thumbnail((max_px, max_px))
    buf = io.BytesIO()
    out.save(buf, format='WEBP', method=6, quality=85)
    data = buf.getvalue()
    return data, out.width, out.height, len(data)

def _strip_exif(img: PILImage.Image) -> PILImage.Image:
    data = list(img.getdata())
    clean = PILImage.new(img.mode, img.size)
    clean.putdata(data)
    return clean

def process_image(file_storage, property_id: int):
    if not Config.USE_R2:
        raise RuntimeError("R2 is required; set USE_R2=true")

    img = Image.open(file_storage.stream)
    img = ImageOps.exif_transpose(img).convert('RGB')
    img = _strip_exif(img)

    uid = uuid.uuid4().hex
    base_key = f"property/{property_id}/{uid}"
    variants = {"thumb": 240, "medium": 800, "large": 1600}

    s3 = r2_client()
    saved = {}
    for name, px in variants.items():
        data, w, h, size_bytes = _save_variant_to_bytes(img, px)
        key = f"{base_key}/{name}.webp"
        s3.put_object(
            Bucket=Config.R2_BUCKET_NAME,
            Key=key,
            Body=data,
            ContentType="image/webp",
            CacheControl="public, max-age=31536000, immutable",
        )
        saved[name] = {
            "key": key,
            "url": f"{Config.R2_PUBLIC_BASE_URL}/{key}",
            "width": w, "height": h, "bytes": size_bytes
        }

    return {
        "width": img.width,
        "height": img.height,
        "bytes": saved["medium"]["bytes"],
        "format": "webp",
        "storage_key": saved["medium"]["key"],
        "thumb_url": saved["thumb"]["url"],
        "url": saved["medium"]["url"],
        "large_url": saved["large"]["url"],
        "rel_medium": saved["medium"]["key"],
    }
