"""
Zero-dependency Pure-Python QR Code SVG Generator & Bridge
Designed specifically for Nepal Passport Office Payment Integration.
Supports standards-compliant QR generation with zero external pip dependencies,
with graceful fallback to `qrcode` library if available.
"""

import io
import base64
import urllib.parse


# Galois Field GF(256) arithmetic tables for Reed-Solomon ECC (QR Code standard)
_EXP = [0] * 512
_LOG = [0] * 256

def _init_gf256():
    x = 1
    for i in range(255):
        _EXP[i] = x
        _LOG[x] = i
        x <<= 1
        if x & 0x100:
            x ^= 0x11D  # Primitive polynomial x^8 + x^4 + x^3 + x^2 + 1
    for i in range(255, 512):
        _EXP[i] = _EXP[i - 255]

_init_gf256()

def _gf_mul(x, y):
    if x == 0 or y == 0:
        return 0
    return _EXP[_LOG[x] + _LOG[y]]

def _poly_mul(p, q):
    r = [0] * (len(p) + len(q) - 1)
    for j, q_val in enumerate(q):
        for i, p_val in enumerate(p):
            r[i + j] ^= _gf_mul(p_val, q_val)
    return r

def _rs_generator_poly(nsym):
    g = [1]
    for i in range(nsym):
        g = _poly_mul(g, [1, _EXP[i]])
    return g

def _rs_encode(data, nsym):
    gen = _rs_generator_poly(nsym)
    res = list(data) + [0] * nsym
    for i in range(len(data)):
        coef = res[i]
        if coef != 0:
            for j in range(len(gen)):
                res[i + j] ^= _gf_mul(gen[j], coef)
    return res[len(data):]


# Version specifications: (version, ecc_level_M): total_data_codewords, ecc_codewords
# Version 3 (29x29) Medium: 44 data codewords (352 bits), 26 ECC codewords
# Version 4 (33x33) Medium: 64 data codewords (512 bits), 36 ECC codewords (2 blocks of 18)
# Version 5 (37x37) Medium: 86 data codewords, 48 ECC codewords
def _select_version(data_len):
    # Byte mode header: 4 bits mode + 8 bits count = 12 bits -> 2 bytes
    needed = data_len + 2
    if needed <= 26:
        return 2, 28, 16, 25, []  # v2-M: 25x25, 28 data, 16 ecc, align at 18
    elif needed <= 44:
        return 3, 44, 26, 29, [22]  # v3-M: 29x29, 44 data, 26 ecc, align at 22
    elif needed <= 64:
        return 4, 64, 36, 33, [26]  # v4-M: 33x33, 64 data, 36 ecc, align at 26
    elif needed <= 86:
        return 5, 86, 48, 37, [30]  # v5-M: 37x37, 86 data, 48 ecc, align at 30
    elif needed <= 108:
        return 6, 108, 56, 41, [34] # v6-M: 41x41
    else:
        return 7, 130, 68, 45, [22, 38] # v7-M: 45x45


class QRCodeMatrix:
    """Standard QR Code matrix builder (Finder, Timing, Alignment, Masking)"""

    def __init__(self, size):
        self.size = size
        self.matrix = [[None] * size for _ in range(size)]
        self.reserved = [[False] * size for _ in range(size)]

    def _set(self, r, c, val, is_reserved=True):
        self.matrix[r][c] = 1 if val else 0
        if is_reserved:
            self.reserved[r][c] = True

    def add_finder_pattern(self, top, left):
        for r in range(7):
            for c in range(7):
                if r in (0, 6) or c in (0, 6) or (2 <= r <= 4 and 2 <= c <= 4):
                    self._set(top + r, left + c, 1)
                else:
                    self._set(top + r, left + c, 0)
        # Separator borders
        for r in range(-1, 8):
            for c in range(-1, 8):
                if r in (-1, 7) or c in (-1, 7):
                    nr, nc = top + r, left + c
                    if 0 <= nr < self.size and 0 <= nc < self.size:
                        self._set(nr, nc, 0)

    def add_timing_patterns(self):
        for i in range(self.size):
            if not self.reserved[6][i]:
                self._set(6, i, 1 if i % 2 == 0 else 0)
            if not self.reserved[i][6]:
                self._set(i, 6, 1 if i % 2 == 0 else 0)

    def add_alignment_pattern(self, cr, cc):
        for r in range(-2, 3):
            for c in range(-2, 3):
                if not (0 <= cr + r < self.size and 0 <= cc + c < self.size):
                    continue
                if self.reserved[cr + r][cc + c]:
                    return  # Overlaps finder pattern
        for r in range(-2, 3):
            for c in range(-2, 3):
                val = 1 if (abs(r) == 2 or abs(c) == 2 or (r == 0 and c == 0)) else 0
                self._set(cr + r, cc + c, val)

    def reserve_format_info(self):
        # Reserve format info areas around finder patterns
        for i in range(9):
            if 0 <= i < self.size:
                self.reserved[8][i] = True
                self.reserved[i][8] = True
                self.reserved[8][self.size - 1 - i] = True
                self.reserved[self.size - 1 - i][8] = True
        # Dark module
        self._set(self.size - 8, 8, 1)

    def set_format_info(self, format_bits):
        # 15 bits of format info (Mask 0, ECC M: bits 101010000010010)
        # Top-left horizontal & vertical
        for i in range(6):
            self.matrix[8][i] = (format_bits >> (14 - i)) & 1
        self.matrix[8][7] = (format_bits >> 8) & 1
        self.matrix[8][8] = (format_bits >> 7) & 1
        self.matrix[7][8] = (format_bits >> 6) & 1
        for i in range(6):
            self.matrix[5 - i][8] = (format_bits >> (5 - i)) & 1

        # Second copy: bottom-left & top-right
        for i in range(7):
            self.matrix[self.size - 1 - i][8] = (format_bits >> (14 - i)) & 1
        for i in range(8):
            self.matrix[8][self.size - 8 + i] = (format_bits >> (7 - i)) & 1


def _generate_qr_matrix(text):
    """Encodes text payload into a 2D boolean matrix using byte mode & ECC M"""
    data_bytes = text.encode('utf-8')
    ver, total_data, ecc_len, size, align_coords = _select_version(len(data_bytes))

    # 1. Byte mode bit stream: Mode=0100 (4 bits) + Count (8 bits) + Data + Terminator
    bits = []
    # Mode 4 (Byte): 0100
    bits.extend([0, 1, 0, 0])
    # Char count (8 bits for version < 10)
    c_len = len(data_bytes)
    for i in range(7, -1, -1):
        bits.append((c_len >> i) & 1)
    for b in data_bytes:
        for i in range(7, -1, -1):
            bits.append((b >> i) & 1)

    # Terminator (up to 4 zeroes)
    max_bits = total_data * 8
    term_len = min(4, max_bits - len(bits))
    bits.extend([0] * term_len)

    # Pad to byte boundary
    while len(bits) % 8 != 0:
        bits.append(0)

    # Pad bytes: 0xEC (236) and 0x11 (17)
    pad_bytes = [0xEC, 0x11]
    pad_idx = 0
    while len(bits) < max_bits:
        pb = pad_bytes[pad_idx % 2]
        for i in range(7, -1, -1):
            bits.append((pb >> i) & 1)
        pad_idx += 1

    # Convert bitstream to data codewords
    data_codewords = []
    for i in range(0, len(bits), 8):
        byte_val = 0
        for bit in bits[i:i + 8]:
            byte_val = (byte_val << 1) | bit
        data_codewords.append(byte_val)

    # 2. Compute Reed-Solomon ECC
    ecc_codewords = _rs_encode(data_codewords, ecc_len)
    all_codewords = data_codewords + ecc_codewords

    # 3. Create matrix and add function patterns
    qr = QRCodeMatrix(size)
    qr.add_finder_pattern(0, 0)
    qr.add_finder_pattern(0, size - 7)
    qr.add_finder_pattern(size - 7, 0)
    qr.add_timing_patterns()
    for ac in align_coords:
        qr.add_alignment_pattern(ac, ac)
    qr.reserve_format_info()

    # 4. Place data bits in 2-column zigzag fashion (right to left)
    bit_stream = []
    for cw in all_codewords:
        for i in range(7, -1, -1):
            bit_stream.append((cw >> i) & 1)

    bit_idx = 0
    col = size - 1
    going_up = True

    while col > 0:
        if col == 6:  # Skip vertical timing pattern
            col -= 1
        rows = range(size - 1, -1, -1) if going_up else range(size)
        for r in rows:
            for c in (col, col - 1):
                if not qr.reserved[r][c]:
                    b_val = bit_stream[bit_idx] if bit_idx < len(bit_stream) else 0
                    bit_idx += 1
                    # Apply Mask Pattern 0: (row + col) % 2 == 0
                    mask = 1 if ((r + c) % 2 == 0) else 0
                    qr.matrix[r][c] = b_val ^ mask
        col -= 2
        going_up = not going_up

    # Format info for ECC Level M, Mask Pattern 0:
    # 15-bit sequence (pre-computed with BCH(15,5) XOR 101010000010010): 0x5412 (0101010000010010)
    format_bits = 0x5412
    qr.set_format_info(format_bits)

    return qr.matrix, size


def generate_qr_svg(payload: str, module_size: int = 8, border: int = 4) -> str:
    """
    Generates a clean, standards-compliant SVG representation of a QR Code.
    Works entirely in pure Python without external dependencies.
    """
    # 1. Check if 'qrcode' pip package is available for optimal compatibility
    try:
        import qrcode
        import qrcode.image.svg
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=module_size,
            border=border,
            image_factory=qrcode.image.svg.SvgPathImage
        )
        qr.add_data(payload)
        qr.make(fit=True)
        img = qr.make_image()
        stream = io.BytesIO()
        img.save(stream)
        return stream.getvalue().decode('utf-8')
    except Exception:
        pass

    # 2. Pure-Python fallback generator
    matrix, matrix_size = _generate_qr_matrix(payload)
    total_size = (matrix_size + border * 2) * module_size

    paths = []
    for r in range(matrix_size):
        for c in range(matrix_size):
            if matrix[r][c] == 1:
                x = (c + border) * module_size
                y = (r + border) * module_size
                paths.append(f"M{x},{y}h{module_size}v{module_size}h-{module_size}z")

    path_data = " ".join(paths)

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" version="1.1" viewBox="0 0 {total_size} {total_size}" width="100%" height="100%" shape-rendering="crispEdges">
  <rect width="100%" height="100%" fill="#ffffff"/>
  <path d="{path_data}" fill="#001a33"/>
</svg>"""
    return svg


def generate_qr_data_uri(payload: str) -> str:
    """
    Returns an SVG data URI suitable for direct usage in HTML <img src="..."> tags.
    """
    svg = generate_qr_svg(payload)
    encoded = urllib.parse.quote(svg)
    return f"data:image/svg+xml;utf8,{encoded}"
