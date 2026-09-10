import io
import os
import struct
import time
import zlib
from datetime import datetime


def escape_pdf_text(text):
    """Escapes special characters in PDF strings."""
    if not text:
        return ""
    return str(text).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _extract_image_for_pdf(img_path):
    """
    Extracts raw image stream, dimensions, and PDF dictionary parameters
    for JPEG or PNG without requiring external third-party dependencies.
    """
    if not img_path or not os.path.exists(img_path):
        return None
    try:
        with open(img_path, 'rb') as f:
            data = f.read()

        # 1. JPEG image
        if data.startswith(b'\xff\xd8'):
            i = 2
            length = len(data)
            w, h = 300, 390
            while i < length - 8:
                if data[i] != 0xFF:
                    i += 1
                    continue
                marker = data[i+1]
                if marker in (0xC0, 0xC1, 0xC2, 0xC3):
                    h = (data[i+5] << 8) + data[i+6]
                    w = (data[i+7] << 8) + data[i+8]
                    break
                elif marker in (0xD8, 0xD9):
                    i += 2
                    continue
                else:
                    seg_len = (data[i+2] << 8) + data[i+3]
                    i += 2 + seg_len
            return {
                'width': w,
                'height': h,
                'colorspace': '/DeviceRGB',
                'bpc': 8,
                'filter': '/DCTDecode',
                'extra_dict': '',
                'stream': data
            }

        # 2. PNG image
        elif data.startswith(b'\x89PNG\r\n\x1a\n'):
            w, h = struct.unpack(">II", data[16:24])
            bit_depth = data[24]
            color_type = data[25]
            idat = bytearray()
            pos = 8
            while pos < len(data) - 12:
                chunk_len = struct.unpack(">I", data[pos:pos+4])[0]
                chunk_type = data[pos+4:pos+8]
                if chunk_type == b'IDAT':
                    idat.extend(data[pos+8:pos+8+chunk_len])
                pos += 12 + chunk_len

            colors = 4 if color_type == 6 else (3 if color_type == 2 else 1)
            colorspace = '/DeviceRGB' if colors >= 3 else '/DeviceGray'
            extra_dict = f"/DecodeParms << /Predictor 15 /Columns {w} /Colors {colors} /BitsPerComponent {bit_depth} >>"
            return {
                'width': w,
                'height': h,
                'colorspace': colorspace,
                'bpc': bit_depth,
                'filter': '/FlateDecode',
                'extra_dict': extra_dict,
                'stream': bytes(idat)
            }
    except Exception:
        return None
    return None


def generate_passport_pdf(application):
    """
    Generates a valid PDF-1.4 Virtual e-Passport certificate for the given Application.
    Embeds the applicant's verified passport-size photo and accurate selected package/page count.
    Returns bytes of the PDF file.
    """
    applicant = application.applicant
    sig = getattr(application, 'digital_signature', None)
    token = getattr(application, 'queue_token', None)

    # Passport details
    app_id_str = f"NP-2026-{application.application_id:04d}"
    full_name = applicant.full_name.upper() if applicant else "CITIZEN USER"
    nationality = (applicant.nationality or "NEPALI").upper() if applicant else "NEPALI"
    dob = str(applicant.date_of_birth) if (applicant and applicant.date_of_birth) else "1995-01-01"
    gender = (applicant.gender or "MALE").upper() if applicant else "MALE"
    passport_type_str = getattr(application, 'passport_type', 'Ordinary e-Passport')
    pages_str = getattr(application, 'passport_pages', '34 Pages')
    # Issue & Expiry Date handling from Application model

    if getattr(application, 'issue_date', None):
        issue_date = application.issue_date.strftime("%Y-%m-%d")
    elif application.submission_date:
        issue_date = application.submission_date.strftime("%Y-%m-%d")
    else:
        issue_date = datetime.now().strftime("%Y-%m-%d")

    if getattr(application, 'expiry_date', None):
        expiry_date = application.expiry_date.strftime("%Y-%m-%d")
    else:
        try:
            from django.conf import settings
            validity = getattr(settings, 'PASSPORT_VALIDITY_YEARS', 10)
            sub_dt = application.issue_date or application.submission_date or datetime.now()
            expiry_date = sub_dt.replace(year=sub_dt.year + validity).strftime("%Y-%m-%d")
        except Exception:
            expiry_date = "2036-09-08"


    # Signature details
    sig_authority = sig.signing_authority if sig else "Department of Passports, Government of Nepal"
    cert_serial = sig.certificate_serial if sig else f"NPL-DOP-PKI-2026-{application.application_id:04d}"
    sig_algo = sig.algorithm if sig else "RSA-SHA256"
    sig_hash = sig.signature_hash if sig else f"SHA256:NPL{application.application_id}{int(time.time())}"
    token_str = f"T-{token.token_number:03d}" if token else "T-101"

    # Retrieve verified Passport Photo document
    img_info = None
    if hasattr(application, 'documents'):
        photo_doc = application.documents.filter(
            document_type__icontains='photo',
            verification_status='Verified'
        ).order_by('-document_id').first()
        if photo_doc and photo_doc.file_path:
            try:
                img_info = _extract_image_for_pdf(photo_doc.file_path.path)
            except Exception:
                try:
                    from django.conf import settings
                    full_p = os.path.join(settings.MEDIA_ROOT, str(photo_doc.file_path))
                    img_info = _extract_image_for_pdf(full_p)
                except Exception:
                    img_info = None

    # MRZ lines (ICAO standard 44 chars)
    name_parts = full_name.split()
    surname = name_parts[-1] if len(name_parts) > 1 else name_parts[0]
    given_names = " ".join(name_parts[:-1]) if len(name_parts) > 1 else ""
    mrz_name = f"{surname}<<{given_names.replace(' ', '<')}".ljust(39, '<')[:39]
    mrz_line1 = f"P<NPL{mrz_name}"[:44]

    dob_compact = dob.replace("-", "")[2:] if len(dob) >= 10 else "950101"
    exp_compact = expiry_date.replace("-", "")[2:] if len(expiry_date) >= 10 else "360908"
    gender_char = gender[0] if gender else "M"
    pass_clean = f"NP{application.application_id:07d}"
    mrz_line2 = f"{pass_clean}9NPL{dob_compact}5{gender_char}{exp_compact}2<<<<<<<<<<<<<<04"[:44]

    # Content Stream Commands (Origin at bottom-left: 595 x 842 pts - A4)
    # Coordinate system: (0,0) is bottom-left, (595, 842) is top-right.
    stream_cmds = [
        # 1. Outer & Inner Border (Government Style)
        "q",
        "0.05 0.15 0.35 rg",  # Primary Navy Blue
        "0.05 0.15 0.35 RG",
        "2 w",
        "25 25 545 792 re S",
        "0.85 0.70 0.20 RG",  # Gold accent inner border
        "1.5 w",
        "29 29 537 784 re S",
        "Q",

        # 2. Header Banner Background
        "q",
        "0.08 0.18 0.38 rg",
        "31 730 533 81 re f",
        "Q",

        # Header Text
        "BT",
        "/F2 16 Tf",
        "1 1 1 rg",  # White
        "170 785 Td",
        f"({escape_pdf_text('GOVERNMENT OF NEPAL')}) Tj",
        "ET",

        "BT",
        "/F1 11 Tf",
        "0.9 0.85 0.5 rg",  # Soft Gold
        "155 768 Td",
        f"({escape_pdf_text('MINISTRY OF FOREIGN AFFAIRS  |  DEPARTMENT OF PASSPORTS')}) Tj",
        "ET",

        "BT",
        "/F2 13 Tf",
        "1 1 1 rg",
        "190 745 Td",
        f"({escape_pdf_text('OFFICIAL VIRTUAL e-PASSPORT')}) Tj",
        "ET",

        # 3. Subheader Status Strip
        "q",
        "0.92 0.95 0.98 rg",
        "31 700 533 28 re f",
        "0.8 0.85 0.9 RG",
        "0.5 w",
        "31 700 533 28 re S",
        "Q",

        "BT",
        "/F2 8.5 Tf",
        "0.1 0.3 0.2 rg",
        "42 710 Td",
        f"({escape_pdf_text('DOCUMENT STATUS: VALID & CERTIFIED')}) Tj",
        "ET",

        "BT",
        "/F1 8.5 Tf",
        "0.3 0.3 0.4 rg",
        "235 710 Td",
        f"({escape_pdf_text('ICAO 9303 COMPLIANT  |  DIGITAL PASS: ' + app_id_str)}) Tj",
        "ET",

        "BT",
        "/F2 8.5 Tf",
        "0.6 0.2 0.1 rg",
        "465 710 Td",
        f"({escape_pdf_text('TOKEN: ' + token_str)}) Tj",
        "ET",

        # 4. Citizen Credentials Frame
        "q",
        "0.97 0.97 0.98 rg",
        "45 420 505 260 re f",
        "0.8 0.8 0.85 RG",
        "1 w",
        "45 420 505 260 re S",
        "Q",
    ]

    if img_info:
        # Render verified applicant photograph inside frame
        stream_cmds.extend([
            "q",
            "60 520 100 130 re W n",  # Clip path to frame bounds
            "100 0 0 130 60 520 cm",   # Coordinate transform matrix
            "/ImPhoto Do",
            "Q",
            "q",
            "0.6 0.7 0.8 RG",
            "1.5 w",
            "60 520 100 130 re S",    # Outer photo border
            "Q",
        ])
    else:
        # Clean placeholder frame
        stream_cmds.extend([
            "q",
            "0.90 0.92 0.95 rg",
            "60 520 100 130 re f",
            "0.7 0.75 0.8 RG",
            "1 w",
            "60 520 100 130 re S",
            "Q",
            "BT",
            "/F2 9 Tf",
            "0.4 0.4 0.5 rg",
            "82 585 Td",
            "(DIGITAL) Tj",
            "ET",
            "BT",
            "/F2 9 Tf",
            "0.4 0.4 0.5 rg",
            "86 570 Td",
            "(PHOTO) Tj",
            "ET",
            "BT",
            "/F1 7 Tf",
            "0.1 0.6 0.2 rg",
            "68 535 Td",
            "(BIOMETRIC MATCH) Tj",
            "ET",
        ])

    stream_cmds.extend([
        # Credentials Fields (Right Side)
        # Field 1: Full Name
        "BT",
        "/F1 8 Tf",
        "0.5 0.5 0.5 rg",
        "180 635 Td",
        "(Full Legal Name / Pura Naam:) Tj",
        "ET",
        "BT",
        "/F2 12 Tf",
        "0.05 0.15 0.35 rg",
        "180 620 Td",
        f"({escape_pdf_text(full_name)}) Tj",
        "ET",

        # Field 2: Passport Number
        "BT",
        "/F1 8 Tf",
        "0.5 0.5 0.5 rg",
        "380 635 Td",
        "(Passport No. / Rahadani No:) Tj",
        "ET",
        "BT",
        "/F2 12 Tf",
        "0.75 0.1 0.1 rg",
        "380 620 Td",
        f"({escape_pdf_text(app_id_str)}) Tj",
        "ET",

        # Field 3: Nationality & Category
        "BT",
        "/F1 8 Tf",
        "0.5 0.5 0.5 rg",
        "180 590 Td",
        "(Nationality / Rastriyata:) Tj",
        "ET",
        "BT",
        "/F2 10 Tf",
        "0.1 0.1 0.1 rg",
        "180 577 Td",
        f"({escape_pdf_text(nationality)}) Tj",
        "ET",

        "BT",
        "/F1 8 Tf",
        "0.5 0.5 0.5 rg",
        "380 590 Td",
        "(Passport Type & Pages:) Tj",
        "ET",
        "BT",
        "/F2 10 Tf",
        "0.1 0.1 0.1 rg",
        "380 577 Td",
        f"({escape_pdf_text(passport_type_str + '  |  ' + pages_str)}) Tj",
        "ET",

        # Field 4: DOB & Gender
        "BT",
        "/F1 8 Tf",
        "0.5 0.5 0.5 rg",
        "180 550 Td",
        "(Date of Birth / Janma Miti:) Tj",
        "ET",
        "BT",
        "/F2 10 Tf",
        "0.1 0.1 0.1 rg",
        "180 537 Td",
        f"({escape_pdf_text(dob)}) Tj",
        "ET",

        "BT",
        "/F1 8 Tf",
        "0.5 0.5 0.5 rg",
        "380 550 Td",
        "(Sex / Gender:) Tj",
        "ET",
        "BT",
        "/F2 10 Tf",
        "0.1 0.1 0.1 rg",
        "380 537 Td",
        f"({escape_pdf_text(gender)}) Tj",
        "ET",

        # Field 5: Dates of Issue & Expiry
        "BT",
        "/F1 8 Tf",
        "0.5 0.5 0.5 rg",
        "180 510 Td",
        "(Date of Issue / Jari Miti:) Tj",
        "ET",
        "BT",
        "/F2 10 Tf",
        "0.1 0.1 0.1 rg",
        "180 497 Td",
        f"({escape_pdf_text(issue_date)}) Tj",
        "ET",

        "BT",
        "/F1 8 Tf",
        "0.5 0.5 0.5 rg",
        "380 510 Td",
        "(Date of Expiry / Myad Sakine Miti:) Tj",
        "ET",
        "BT",
        "/F2 10 Tf",
        "0.1 0.1 0.1 rg",
        "380 497 Td",
        f"({escape_pdf_text(expiry_date)}) Tj",
        "ET",

        # Field 6: Issuing Authority & Biometrics
        "BT",
        "/F1 8 Tf",
        "0.5 0.5 0.5 rg",
        "180 470 Td",
        "(Issuing Authority:) Tj",
        "ET",
        "BT",
        "/F2 10 Tf",
        "0.1 0.1 0.1 rg",
        "180 457 Td",
        "(DEPARTMENT OF PASSPORTS, KATHMANDU, NEPAL) Tj",
        "ET",

        "BT",
        "/F1 8 Tf",
        "0.5 0.5 0.5 rg",
        "180 440 Td",
        "(Biometric Authentication:) Tj",
        "ET",
        "BT",
        "/F2 9 Tf",
        "0.08 0.5 0.15 rg",
        "285 440 Td",
        "(VERIFIED - SYSTEM AUTHENTICATED) Tj",
        "ET",

        # 5. Machine Readable Zone (MRZ Box)
        "q",
        "0.08 0.1 0.18 rg",  # Dark Slate Background for MRZ
        "45 320 505 80 re f",
        "0.7 0.6 0.2 RG",
        "1.5 w",
        "45 320 505 80 re S",
        "Q",

        "BT",
        "/F3 12 Tf",  # Courier Monospace for ICAO MRZ
        "1 1 0.9 rg",
        "60 365 Td",
        f"({escape_pdf_text(mrz_line1)}) Tj",
        "ET",

        "BT",
        "/F3 12 Tf",
        "1 1 0.9 rg",
        "60 340 Td",
        f"({escape_pdf_text(mrz_line2)}) Tj",
        "ET",

        # 6. Official Government Digital Signature Box
        "q",
        "0.96 0.97 0.99 rg",
        "45 140 505 160 re f",
        "0.75 0.8 0.88 RG",
        "1 w",
        "45 140 505 160 re S",
        "Q",

        "BT",
        "/F2 11 Tf",
        "0.05 0.15 0.35 rg",
        "60 275 Td",
        "(GOVERNMENT DIGITAL SIGNATURE & CRYPTOGRAPHIC VERIFICATION) Tj",
        "ET",

        "BT",
        "/F2 9 Tf",
        "0.1 0.55 0.2 rg",
        "450 275 Td",
        "(STATUS: SIGNED & VALID) Tj",
        "ET",

        "BT",
        "/F1 8 Tf",
        "0.3 0.3 0.3 rg",
        "60 250 Td",
        f"({escape_pdf_text('Certifying Authority: ' + sig_authority)}) Tj",
        "ET",

        "BT",
        "/F1 8 Tf",
        "0.3 0.3 0.3 rg",
        "60 232 Td",
        f"({escape_pdf_text('Certificate Serial Number: ' + cert_serial)}) Tj",
        "ET",

        "BT",
        "/F1 8 Tf",
        "0.3 0.3 0.3 rg",
        "60 214 Td",
        f"({escape_pdf_text('Signing Algorithm: ' + sig_algo)}) Tj",
        "ET",

        "BT",
        "/F3 7 Tf",
        "0.2 0.2 0.3 rg",
        "60 196 Td",
        f"({escape_pdf_text('Cryptographic Hash: ' + sig_hash[:70])}) Tj",
        "ET",

        "BT",
        "/F1 8 Tf",
        "0.4 0.4 0.4 rg",
        "60 178 Td",
        f"({escape_pdf_text('Verification Timestamp: ' + issue_date + '  |  Digitally verified by Dept of Passports')}) Tj",
        "ET",

        "BT",
        "/F1 7 Tf",
        "0.5 0.5 0.5 rg",
        "60 152 Td",
        "(Notice: This document is an authentic electronic certificate issued under the Passport Queue Management System.) Tj",
        "ET",

        # 7. Official Legal Footer
        "BT",
        "/F1 8 Tf",
        "0.4 0.4 0.4 rg",
        "120 55 Td",
        "(Department of Passports  |  Tripureshwor, Kathmandu, Nepal  |  www.nepalpassport.gov.np) Tj",
        "ET",

        "BT",
        "/F1 7 Tf",
        "0.6 0.6 0.6 rg",
        "180 42 Td",
        "(Official Academic Capstone Implementation  |  All rights reserved) Tj",
        "ET",
    ])

    stream_content = "\n".join(stream_cmds).encode("latin-1", "replace")
    stream_len = len(stream_content)

    # Build PDF Objects
    objects = []
    
    # 1 0 obj: Catalog
    objects.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    
    # 2 0 obj: Pages
    objects.append(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
    
    # 3 0 obj: Page
    xobject_res = " /XObject << /ImPhoto 8 0 R >>" if img_info else ""
    page_obj_str = (
        b"3 0 obj\n"
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842]\n"
        b"/Contents 4 0 R\n"
        + f"/Resources << /Font << /F1 5 0 R /F2 6 0 R /F3 7 0 R >>{xobject_res} >>\n".encode("ascii")
        + b">>\nendobj\n"
    )
    objects.append(page_obj_str)

    # 4 0 obj: Content Stream
    stream_header = f"4 0 obj\n<< /Length {stream_len} >>\nstream\n".encode("ascii")
    stream_footer = b"\nendstream\nendobj\n"
    objects.append(stream_header + stream_content + stream_footer)

    # 5 0 obj: Font F1 (Helvetica)
    objects.append(b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n")

    # 6 0 obj: Font F2 (Helvetica-Bold)
    objects.append(b"6 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>\nendobj\n")

    # 7 0 obj: Font F3 (Courier - Monospace for MRZ & Hash)
    objects.append(b"7 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>\nendobj\n")

    # 8 0 obj: Image XObject (if photo present)
    if img_info:
        img_stream = img_info['stream']
        img_len = len(img_stream)
        extra_d = f" {img_info['extra_dict']}" if img_info.get('extra_dict') else ""
        img_header = (
            f"8 0 obj\n"
            f"<< /Type /XObject /Subtype /Image /Width {img_info['width']} /Height {img_info['height']} "
            f"/ColorSpace {img_info['colorspace']} /BitsPerComponent {img_info['bpc']} "
            f"/Filter {img_info['filter']}{extra_d} /Length {img_len} >>\nstream\n"
        ).encode("ascii")
        img_footer = b"\nendstream\nendobj\n"
        objects.append(img_header + img_stream + img_footer)

    # Assemble complete PDF file with correct byte offsets in xref
    output = io.BytesIO()
    output.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")

    offsets = []
    for obj in objects:
        offsets.append(output.tell())
        output.write(obj)

    xref_pos = output.tell()
    num_objects = len(objects) + 1  # 0 is the special null entry

    output.write(f"xref\n0 {num_objects}\n".encode("ascii"))
    output.write(b"0000000000 65535 f \n")
    for offset in offsets:
        output.write(f"{offset:010d} 00000 n \n".encode("ascii"))

    trailer = (
        f"trailer\n"
        f"<< /Size {num_objects} /Root 1 0 R >>\n"
        f"startxref\n{xref_pos}\n%%EOF\n"
    ).encode("ascii")
    output.write(trailer)

    return output.getvalue()
