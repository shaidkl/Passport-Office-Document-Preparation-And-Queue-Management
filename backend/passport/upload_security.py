import os
import re
import socket
import struct

from django.conf import settings
from PIL import Image, UnidentifiedImageError


class UploadSecurityError(ValueError):
    pass


ALLOWED_TYPES = {
    '.pdf': ('application/pdf', b'%PDF-'),
    '.jpg': ('image/jpeg', b'\xff\xd8\xff'),
    '.jpeg': ('image/jpeg', b'\xff\xd8\xff'),
    '.png': ('image/png', b'\x89PNG\r\n\x1a\n'),
}


def _scan_with_clamav(uploaded_file):
    if not settings.MALWARE_SCAN_ENABLED:
        return

    uploaded_file.seek(0)
    try:
        with socket.create_connection(
            (settings.CLAMAV_HOST, settings.CLAMAV_PORT),
            timeout=settings.CLAMAV_TIMEOUT_SECONDS,
        ) as scanner:
            scanner.sendall(b'zINSTREAM\0')
            for chunk in uploaded_file.chunks(chunk_size=64 * 1024):
                scanner.sendall(struct.pack('!I', len(chunk)))
                scanner.sendall(chunk)
            scanner.sendall(struct.pack('!I', 0))

            response = bytearray()
            while True:
                part = scanner.recv(4096)
                if not part:
                    break
                response.extend(part)
                if b'\0' in part:
                    break
    except (OSError, socket.timeout) as exc:
        raise UploadSecurityError(
            'The security scanner is unavailable. Upload was rejected; please try again later.'
        ) from exc
    finally:
        uploaded_file.seek(0)

    result = bytes(response).decode('utf-8', errors='replace').strip('\0\r\n ')
    if result.endswith('FOUND'):
        raise UploadSecurityError('The uploaded file failed the malware security scan.')
    if not result.endswith('OK'):
        raise UploadSecurityError('The security scanner could not verify the uploaded file.')


def _validate_image(uploaded_file, extension):
    expected_format = 'JPEG' if extension in {'.jpg', '.jpeg'} else 'PNG'
    uploaded_file.seek(0)
    try:
        with Image.open(uploaded_file) as image:
            if image.format != expected_format:
                raise UploadSecurityError('The image contents do not match its filename extension.')
            width, height = image.size
            if width < 200 or height < 200:
                raise UploadSecurityError('The image resolution is too low; use at least 200 × 200 pixels.')
            if width > 10000 or height > 10000 or width * height > 25_000_000:
                raise UploadSecurityError('The image dimensions are too large to process safely.')
            image.verify()
    except (Image.DecompressionBombError, UnidentifiedImageError, OSError, SyntaxError) as exc:
        raise UploadSecurityError('The uploaded image is corrupted or invalid.') from exc
    finally:
        uploaded_file.seek(0)


def _validate_pdf(uploaded_file):
    uploaded_file.seek(0)
    content = uploaded_file.read()
    uploaded_file.seek(0)
    if not content.startswith(b'%PDF-') or b'%%EOF' not in content[-4096:]:
        raise UploadSecurityError('The uploaded PDF is corrupted or incomplete.')

    if re.search(
        rb'/(JavaScript|JS|Launch|EmbeddedFile|OpenAction|AA|Encrypt)\b',
        content,
        flags=re.IGNORECASE,
    ):
        raise UploadSecurityError('Active or embedded PDF content is not permitted.')


def validate_uploaded_document(uploaded_file, document_type):
    if uploaded_file is None:
        raise UploadSecurityError('A multipart document upload is required.')
    if not getattr(uploaded_file, 'name', ''):
        raise UploadSecurityError('The uploaded file must have a filename.')
    if uploaded_file.size <= 0:
        raise UploadSecurityError('The uploaded file is empty.')

    extension = os.path.splitext(uploaded_file.name)[1].lower()
    if extension not in ALLOWED_TYPES:
        raise UploadSecurityError('Only PDF, JPG, JPEG, and PNG files are supported.')
    if document_type == 'Passport Photo' and extension not in {'.jpg', '.jpeg', '.png'}:
        raise UploadSecurityError('Passport photographs must be JPG, JPEG, or PNG images.')

    max_size = 5 * 1024 * 1024 if document_type == 'Passport Photo' else 10 * 1024 * 1024
    if uploaded_file.size > max_size:
        limit = 5 if document_type == 'Passport Photo' else 10
        raise UploadSecurityError(f'The file exceeds the {limit} MB upload limit.')

    uploaded_file.seek(0)
    header = uploaded_file.read(16)
    uploaded_file.seek(0)
    expected_mime, signature = ALLOWED_TYPES[extension]
    if not header.startswith(signature):
        raise UploadSecurityError('The file contents do not match its filename extension.')

    supplied_mime = (getattr(uploaded_file, 'content_type', '') or '').lower()
    if supplied_mime and supplied_mime not in {expected_mime, 'application/octet-stream'}:
        raise UploadSecurityError('The declared file type does not match the uploaded content.')

    if extension == '.pdf':
        _validate_pdf(uploaded_file)
    else:
        _validate_image(uploaded_file, extension)

    _scan_with_clamav(uploaded_file)
    uploaded_file.seek(0)
    return uploaded_file
