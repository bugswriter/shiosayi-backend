# utils.py
import os
import uuid
import secrets
import string
from PIL import Image, UnidentifiedImageError
from werkzeug.utils import secure_filename

CDN_STORAGE_PATH = os.getenv("CDN_STORAGE_PATH")
CDN_BASE_URL = os.getenv("CDN_BASE_URL")
TARGET_WIDTH = 350
TARGET_ASPECT_RATIO = 2 / 3
ASPECT_RATIO_TOLERANCE = 0.05
MAX_FILE_SIZE_BYTES = 1 * 1024 * 1024


def generate_api_token(prefix="shio", length=32):
    """Generates a secure, random API token."""
    alphabet = string.ascii_letters + string.digits
    token = ''.join(secrets.choice(alphabet) for _ in range(length))
    return f"{prefix}_{token}"

def process_and_save_poster(file_storage):
    """
    Validates, resizes, and saves an uploaded film poster.
    
    Args:
        file_storage: The FileStorage object from Flask's request.files.

    Returns:
        A dictionary with the result:
        {'success': True, 'url': '...', 'path': '...'} or
        {'success': False, 'error': '...'}
    """
    if not CDN_STORAGE_PATH or not CDN_BASE_URL:
        return {'success': False, 'error': 'Server configuration error: CDN_STORAGE_PATH or CDN_BASE_URL is not set.'}

    filename = f"{uuid.uuid4().hex}.jpg"
    
    posters_dir = os.path.join(CDN_STORAGE_PATH, 'posters')
    save_path = os.path.join(posters_dir, filename)

    filename = f"{uuid.uuid4().hex}.jpg"
    file_storage.seek(0, os.SEEK_END)

    file_size = file_storage.tell()
    if file_size > MAX_FILE_SIZE_BYTES:
        return {'success': False, 'error': f'File is too large. Maximum size is {MAX_FILE_SIZE_BYTES / 1024 / 1024} MB.'}
    file_storage.seek(0)

    try:
        img = Image.open(file_storage)

        if img.format != 'JPEG':
            return {'success': False, 'error': 'Invalid file type. Only JPEG images are allowed.'}

        actual_ratio = img.width / img.height
        if abs(actual_ratio - TARGET_ASPECT_RATIO) > ASPECT_RATIO_TOLERANCE:
            error_msg = f'Invalid aspect ratio. Image ratio is {actual_ratio:.2f}, but must be near {TARGET_ASPECT_RATIO:.2f} (2:3).'
            return {'success': False, 'error': error_msg}

        new_height = int(TARGET_WIDTH / actual_ratio)
        resized_img = img.resize((TARGET_WIDTH, new_height), Image.Resampling.LANCZOS)
        os.makedirs(posters_dir, exist_ok=True)
        resized_img.save(save_path, 'JPEG', quality=85, optimize=True)
        
        final_url = f"{CDN_BASE_URL}/posters/{filename}"
        return {'success': True, 'url': final_url, 'path': save_path}

    except UnidentifiedImageError:
        return {'success': False, 'error': 'Cannot identify image file. It may be corrupt or not a valid image.'}
    except Exception as e:
        logging.error(f"Error processing poster for '{filename}': {e}")
        return {'success': False, 'error': 'An unexpected error occurred during image processing.'}