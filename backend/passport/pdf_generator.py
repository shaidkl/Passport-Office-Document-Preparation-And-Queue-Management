"""Generate a TD3-sized digital passport record.

The PDF deliberately does not reproduce Nepal's protected passport artwork,
security printing, or contactless chip. It mirrors the public ICAO TD3 page
dimensions and machine-readable data structure while remaining unmistakably a
portal-issued digital record that is not valid for physical travel.
"""

import io
import re
import unicodedata
import zlib
from datetime import date, datetime

from PIL import Image, ImageOps


POINTS_PER_MM = 72 / 25.4
PAGE_WIDTH = 125 * POINTS_PER_MM
PAGE_HEIGHT = 88 * POINTS_PER_MM
MRZ_WEIGHTS = (7, 3, 1)
MRZ_VALUES = {str(number): number for number in range(10)}
MRZ_VALUES.update({chr(code): code - 55 for code in range(65, 91)})
MRZ_VALUES["<"] = 0


def escape_pdf_text(value):
    """Escape text used inside a PDF literal string."""
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def get_passport_page_count(application):
    """Return the physical booklet page option selected by the applicant."""
    category = (application.passport_category or "").lower()
    match = re.search(r"\b(34|66)\b", category)
    return int(match.group(1)) if match else 34


def _pdf_date(value, fallback="NOT RECORDED"):
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        return value.strftime("%d %b %Y").upper()
    return fallback


def _mrz_date(value):
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        return value.strftime("%y%m%d")
    return "<<<<<<"


def _mrz_clean(value, separator="<"):
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").upper()
    return re.sub(r"[^A-Z0-9]", separator, ascii_value)


def _mrz_check(value):
    total = sum(MRZ_VALUES.get(char, 0) * MRZ_WEIGHTS[index % 3] for index, char in enumerate(value))
    return str(total % 10)


def _split_name(full_name):
    parts = [part for part in re.split(r"\s+", str(full_name or "").strip()) if part]
    if not parts:
        return "NOT RECORDED", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[-1], " ".join(parts[:-1])


def _document_number(application):
    """Return the allocated nine-character sequential passport number."""
    passport_number = str(getattr(application, "passport_number", "") or "").upper()
    if not re.fullmatch(r"NP\d{7}", passport_number):
        raise ValueError("A valid sequential passport number is required.")
    return passport_number


def build_td3_mrz(application):
    """Build the two 44-character TD3 MRZ lines, including all check digits."""
    applicant = application.applicant
    surname, given_names = _split_name(applicant.full_name)
    mrz_name = f"{_mrz_clean(surname)}<<{_mrz_clean(given_names)}"
    line_one = ("P<NPL" + mrz_name)[:44].ljust(44, "<")

    document_number = _mrz_clean(_document_number(application))[:9].ljust(9, "<")
    birth_date = _mrz_date(getattr(applicant, "date_of_birth", None))
    expiry_date = _mrz_date(getattr(application, "expiry_date", None))
    sex_value = str(getattr(applicant, "gender", "") or "").strip().upper()
    sex = {"MALE": "M", "FEMALE": "F"}.get(sex_value, "X")
    optional_data = "<" * 14

    document_check = _mrz_check(document_number)
    birth_check = _mrz_check(birth_date)
    expiry_check = _mrz_check(expiry_date)
    optional_check = _mrz_check(optional_data)
    composite_source = (
        document_number
        + document_check
        + birth_date
        + birth_check
        + expiry_date
        + expiry_check
        + optional_data
        + optional_check
    )
    composite_check = _mrz_check(composite_source)
    line_two = (
        document_number
        + document_check
        + "NPL"
        + birth_date
        + birth_check
        + sex
        + expiry_date
        + expiry_check
        + optional_data
        + optional_check
        + composite_check
    )
    return line_one, line_two


def _rgb(red, green, blue):
    return f"{red:.3f} {green:.3f} {blue:.3f}"


def _text(commands, x, y, value, size=7, font="F1", color=(0.06, 0.14, 0.24)):
    commands.append(
        f"BT /{font} {size:.2f} Tf {_rgb(*color)} rg {x:.2f} {y:.2f} Td "
        f"({escape_pdf_text(value)}) Tj ET"
    )


def _line(commands, x1, y1, x2, y2, color=(0.72, 0.77, 0.82), width=0.5):
    commands.append(
        f"{_rgb(*color)} RG {width:.2f} w {x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S"
    )


def _rect(commands, x, y, width, height, stroke=(0.25, 0.35, 0.45), fill=None, line_width=0.6):
    if fill:
        commands.append(f"{_rgb(*fill)} rg {x:.2f} {y:.2f} {width:.2f} {height:.2f} re f")
    if stroke:
        commands.append(
            f"{_rgb(*stroke)} RG {line_width:.2f} w "
            f"{x:.2f} {y:.2f} {width:.2f} {height:.2f} re S"
        )


def _common_page_markings(commands, page_number, total_pages):
    _text(
        commands,
        12,
        PAGE_HEIGHT - 10,
        "DIGITAL RECORD - NOT VALID FOR PHYSICAL TRAVEL",
        size=5.2,
        font="F2",
        color=(0.55, 0.12, 0.12),
    )
    _text(
        commands,
        PAGE_WIDTH - 45,
        7,
        f"{page_number} / {total_pages}",
        size=5.5,
        color=(0.35, 0.4, 0.45),
    )


def _compressed_stream(commands):
    return zlib.compress("\n".join(commands).encode("latin-1", "replace"), level=9)


def _prepare_portrait(application):
    """Return an RGB JPEG suitable for a portrait XObject, if one is available."""
    photo_document = (
        application.documents.filter(document_type__icontains="photo", verification_status="Verified")
        .order_by("-upload_date")
        .first()
    )
    if not photo_document or not photo_document.has_available_file():
        return None

    try:
        source = photo_document.open_preserved_file()
        try:
            image = Image.open(source)
            image.load()
        finally:
            source.close()
        image = ImageOps.exif_transpose(image).convert("RGB")
        portrait = ImageOps.fit(image, (450, 600), method=Image.Resampling.LANCZOS, centering=(0.5, 0.43))
        output = io.BytesIO()
        portrait.save(output, format="JPEG", quality=88, optimize=True)
        return {"data": output.getvalue(), "width": 450, "height": 600}
    except (OSError, ValueError):
        return None


def _notice_page(application, total_pages):
    signature = getattr(application, "digital_signature", None)
    document_number = _document_number(application)
    reference = f"NP-{application.submission_date.year}-{application.application_id:04d}"
    commands = []
    _rect(commands, 0, 0, PAGE_WIDTH, PAGE_HEIGHT, stroke=None, fill=(0.965, 0.972, 0.980))
    _common_page_markings(commands, 1, total_pages)

    _rect(commands, 12, 145, PAGE_WIDTH - 24, 72, stroke=(0.04, 0.18, 0.34), fill=(0.04, 0.18, 0.34))
    _text(commands, 24, 195, "GOVERNMENT OF NEPAL", size=8, font="F2", color=(1, 1, 1))
    _text(commands, 24, 180, "DEPARTMENT OF PASSPORTS", size=14, font="F2", color=(1, 1, 1))
    _text(commands, 24, 164, "PORTAL-ISSUED DIGITAL PASSPORT RECORD", size=8, color=(0.88, 0.92, 0.97))

    _text(commands, 18, 128, "IMPORTANT VALIDATION NOTICE", size=8, font="F2", color=(0.55, 0.08, 0.08))
    _text(commands, 18, 114, "This PDF is an electronic portal record. It is not the physical ePassport,", size=6.8)
    _text(commands, 18, 104, "contains no contactless chip, and cannot be used for border crossing or visas.", size=6.8)
    _text(commands, 18, 94, "Protected security artwork and manufacturing features are intentionally omitted.", size=6.8)

    _line(commands, 18, 84, PAGE_WIDTH - 18, 84)
    _text(commands, 18, 71, "RECORD DETAILS", size=7, font="F2")
    _text(commands, 18, 58, f"Application reference: {reference}", size=6.4)
    _text(commands, 18, 48, f"Document reference: {document_number}", size=6.4)
    _text(commands, 18, 38, f"Selected booklet: {total_pages} pages", size=6.4)

    if signature:
        _text(commands, 178, 71, "DIGITAL VERIFICATION", size=7, font="F2")
        _text(commands, 178, 58, f"Certificate: {signature.certificate_serial}", size=5.6)
        _text(commands, 178, 48, f"Algorithm: {signature.algorithm}", size=5.6)
        _text(commands, 178, 38, f"Key ID: {signature.key_id}", size=5.6)
        _text(commands, 178, 28, f"Payload hash: {signature.payload_hash[:28]}...", size=5.2, font="F3")
    else:
        _text(commands, 178, 58, "No digital signature is attached.", size=6, color=(0.55, 0.08, 0.08))

    return _compressed_stream(commands)


def _field(commands, x, y, label, value, value_size=7.1):
    _text(commands, x, y + 7, label.upper(), size=4.6, font="F2", color=(0.35, 0.4, 0.45))
    _text(commands, x, y - 1, value, size=value_size, font="F2")


def _data_page(application, total_pages, has_portrait):
    applicant = application.applicant
    surname, given_names = _split_name(applicant.full_name)
    line_one, line_two = build_td3_mrz(application)
    issue_date = getattr(application, "issue_date", None)
    expiry_date = getattr(application, "expiry_date", None)
    gender = str(getattr(applicant, "gender", "") or "").strip().upper()
    sex = {"MALE": "M", "FEMALE": "F"}.get(gender, "X")
    place_of_birth = getattr(applicant, "place_of_birth", None) or "NOT RECORDED"

    commands = []
    _rect(commands, 0, 0, PAGE_WIDTH, PAGE_HEIGHT, stroke=None, fill=(0.975, 0.972, 0.945))
    _common_page_markings(commands, 2, total_pages)
    _rect(commands, 10, 205, PAGE_WIDTH - 20, 26, stroke=None, fill=(0.08, 0.24, 0.37))
    _text(commands, 17, 219, "NEPAL / NPL", size=10, font="F2", color=(1, 1, 1))
    _text(commands, 97, 219, "PASSPORT DATA - DIGITAL RECORD", size=8, font="F2", color=(1, 1, 1))

    photo_x, photo_y, photo_width, photo_height = 14, 73, 64, 86
    _rect(commands, photo_x, photo_y, photo_width, photo_height, stroke=(0.25, 0.31, 0.37), fill=(0.9, 0.91, 0.9))
    if has_portrait:
        commands.append(
            f"q {photo_width:.2f} 0 0 {photo_height:.2f} {photo_x:.2f} {photo_y:.2f} cm /Im1 Do Q"
        )
    else:
        _text(commands, photo_x + 9, photo_y + 43, "NO VERIFIED", size=5.8, font="F2", color=(0.45, 0.45, 0.45))
        _text(commands, photo_x + 14, photo_y + 34, "PORTRAIT", size=5.8, font="F2", color=(0.45, 0.45, 0.45))

    _field(commands, 14, 176, "Type", "P / ORDINARY")
    _field(commands, 100, 187, "Issuing state", "NPL")
    _field(commands, 180, 187, "Document number", _document_number(application), value_size=8)
    _field(commands, 100, 166, "Surname", surname)
    _field(commands, 100, 145, "Given names", given_names or "-")
    _field(commands, 100, 124, "Nationality", "NEPALI")
    _field(commands, 180, 124, "Date of birth", _pdf_date(getattr(applicant, "date_of_birth", None)))
    _field(commands, 290, 124, "Sex", sex)
    _field(commands, 100, 103, "Place of birth", place_of_birth, value_size=6.3)
    _field(commands, 100, 82, "Date of issue", _pdf_date(issue_date), value_size=6.4)
    _field(commands, 180, 82, "Date of expiry", _pdf_date(expiry_date), value_size=6.4)
    _field(commands, 264, 82, "Authority", "DOP NEPAL", value_size=6.4)
    _text(commands, 100, 66, "Holder signature: not captured in this digital record", size=5.1, color=(0.38, 0.4, 0.42))

    _rect(commands, 10, 14, PAGE_WIDTH - 20, 43, stroke=(0.2, 0.25, 0.3), fill=(0.94, 0.94, 0.90), line_width=0.7)
    _text(commands, 20, 40, line_one, size=8.4, font="F3", color=(0.02, 0.02, 0.02))
    _text(commands, 20, 25, line_two, size=8.4, font="F3", color=(0.02, 0.02, 0.02))
    return _compressed_stream(commands)


def _visa_page(application, page_number, total_pages):
    commands = []
    _rect(commands, 0, 0, PAGE_WIDTH, PAGE_HEIGHT, stroke=None, fill=(0.975, 0.972, 0.945))
    _common_page_markings(commands, page_number, total_pages)
    _text(commands, 16, PAGE_HEIGHT - 28, "VISAS", size=9, font="F2", color=(0.15, 0.25, 0.32))
    _text(
        commands,
        PAGE_WIDTH - 100,
        PAGE_HEIGHT - 28,
        _document_number(application),
        size=6,
        font="F3",
        color=(0.4, 0.43, 0.45),
    )
    _line(commands, 14, PAGE_HEIGHT - 35, PAGE_WIDTH - 14, PAGE_HEIGHT - 35, color=(0.62, 0.66, 0.67))
    _rect(commands, 14, 22, PAGE_WIDTH - 28, PAGE_HEIGHT - 66, stroke=(0.76, 0.77, 0.73), line_width=0.45)
    _text(
        commands,
        73,
        PAGE_HEIGHT / 2,
        "DIGITAL COPY - NOT VALID FOR VISA OR TRAVEL",
        size=8.5,
        font="F2",
        color=(0.84, 0.82, 0.77),
    )
    _text(
        commands,
        17,
        13,
        "Security printing, chip data, and anti-counterfeit artwork are not reproduced.",
        size=4.7,
        color=(0.45, 0.47, 0.47),
    )
    return _compressed_stream(commands)


def generate_passport_pdf(application):
    """Return a complete TD3-sized PDF for an approved passport application."""
    total_pages = get_passport_page_count(application)
    portrait = _prepare_portrait(application)

    objects = {}
    next_object_id = 1

    catalog_id = next_object_id
    next_object_id += 1
    pages_id = next_object_id
    next_object_id += 1
    font_regular_id = next_object_id
    next_object_id += 1
    font_bold_id = next_object_id
    next_object_id += 1
    font_mrz_id = next_object_id
    next_object_id += 1

    objects[font_regular_id] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
    objects[font_bold_id] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>"
    objects[font_mrz_id] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier-Bold >>"

    image_id = None
    if portrait:
        image_id = next_object_id
        next_object_id += 1
        image_header = (
            f"<< /Type /XObject /Subtype /Image /Width {portrait['width']} "
            f"/Height {portrait['height']} /ColorSpace /DeviceRGB /BitsPerComponent 8 "
            f"/Filter /DCTDecode /Length {len(portrait['data'])} >>\nstream\n"
        ).encode("ascii")
        objects[image_id] = image_header + portrait["data"] + b"\nendstream"

    page_ids = []
    for page_number in range(1, total_pages + 1):
        if page_number == 1:
            stream = _notice_page(application, total_pages)
        elif page_number == 2:
            stream = _data_page(application, total_pages, bool(portrait))
        else:
            stream = _visa_page(application, page_number, total_pages)

        content_id = next_object_id
        next_object_id += 1
        objects[content_id] = (
            f"<< /Length {len(stream)} /Filter /FlateDecode >>\nstream\n".encode("ascii")
            + stream
            + b"\nendstream"
        )

        page_id = next_object_id
        next_object_id += 1
        page_ids.append(page_id)
        resource_parts = [
            f"/Font << /F1 {font_regular_id} 0 R /F2 {font_bold_id} 0 R /F3 {font_mrz_id} 0 R >>"
        ]
        if page_number == 2 and image_id:
            resource_parts.append(f"/XObject << /Im1 {image_id} 0 R >>")
        resources = " ".join(resource_parts)
        objects[page_id] = (
            f"<< /Type /Page /Parent {pages_id} 0 R "
            f"/MediaBox [0 0 {PAGE_WIDTH:.2f} {PAGE_HEIGHT:.2f}] "
            f"/Resources << {resources} >> /Contents {content_id} 0 R >>"
        ).encode("ascii")

    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects[pages_id] = f"<< /Type /Pages /Kids [{kids}] /Count {total_pages} >>".encode("ascii")
    objects[catalog_id] = f"<< /Type /Catalog /Pages {pages_id} 0 R >>".encode("ascii")

    max_object_id = next_object_id - 1
    output = io.BytesIO()
    output.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = {0: 0}
    for object_id in range(1, max_object_id + 1):
        offsets[object_id] = output.tell()
        output.write(f"{object_id} 0 obj\n".encode("ascii"))
        output.write(objects[object_id])
        output.write(b"\nendobj\n")

    xref_offset = output.tell()
    output.write(f"xref\n0 {max_object_id + 1}\n".encode("ascii"))
    output.write(b"0000000000 65535 f \n")
    for object_id in range(1, max_object_id + 1):
        output.write(f"{offsets[object_id]:010d} 00000 n \n".encode("ascii"))
    output.write(
        (
            f"trailer\n<< /Size {max_object_id + 1} /Root {catalog_id} 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF"
        ).encode("ascii")
    )
    return output.getvalue()
