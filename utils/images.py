import io, os, uuid
from PIL import Image, ImageOps
from config import Config

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
    HEIF_OK = True
except Exception:
    HEIF_OK = False

ALLOWED = Config.IMAGE_ALLOWED_FORMATS

def _ext_ok(filename: str) -> bool:
    return filename.lower().split(".")[-1] in ALLOWED


def _check_size(stream: io.BytesIO):
    stream.seek(0, io.SEEK_END)
    size = stream.tell()
    stream.seek(0)
    if size > Config.IMAGE_MAX_MB * 1024 * 1024:
        raise ValueError(f"file to large (> {Config.IMAGE_MAX_MB} MB")
    return size

def _open_image(stream: io.BytesIO) -> Image.Image:
    img = Image.open(stream)
    return ImageOps.exif_transpose(img)

def _strip_exif(img: Image.Image) -> Image.Image:
    data = list(img.getdata())
    clean = Image.new(img.mode, img.size)
    clean.putdata(data)
    return clean

def _save_variants(img: Image.Image, base_dir: str, base_url: str):
    os.makedirs(base_dir, exist_ok=True)
    # Sizes
    variants = {
        'thumb' : 240,
        'medium' : 800,
        'large' : 1600
    }

    saved = {}
    for name, max_px in variants.items():
        out = img.copy()
        out.thumbnail((max_px, max_px))
        key = f"{name}.webp"
        path = os.path.join(base_dir, key)
        out.save(path, format='WEBP', method=6, quality=85)
        saved[name] = {
            'path' : path,
            'rel' : os.path.relpath(path, Config.IMAGE_UPLOAD_DIR).replace('\\','/'),
            'size' : os.path.getsize(path),
            'width' : out.width,
            'height' : out.height
        }
    urls = {k: f"{base_url}/{v['rel']}" for k, v in saved.items()}
    return saved, urls

def process_image(file_storage, property_id: int):
    # first validation
    filename = file_storage.filename or 'upload'
    if not _ext_ok(filename):
        raise ValueError(f"unsupported format; allowed: {', '.join(sorted(ALLOWED))}")
    b = io.BytesIO(file_storage.read())
    size = _check_size(b)

    img = _open_image(b)
    img = _strip_exif(img).convert('RGB')

    # Save path: uploads/property/{id}/{uuid}/
    uid = uuid.uuid4().hex
    base_rel_dir = f"property/{property_id}/{uid}"
    base_dir = os.path.join(Config.IMAGE_UPLOAD_DIR, base_rel_dir)
    base_url = f"{Config.IMAGE_BASE_URL}/{base_rel_dir}"

    saved, urls = _save_variants(img, base_dir, base_url)

    meta = {
        'width': img.width,
        'height': img.height,
        'bytes': size,
        'format': (img.format or '').lower(),
        'storage_key': f"{base_rel_dir}/medium.webp",  # کلید نماینده
        'thumb_url': urls['thumb'],
        'url': urls['medium'],
        'large_url': urls['large'],
        'rel_medium': saved['medium']['rel']
    }
    return meta