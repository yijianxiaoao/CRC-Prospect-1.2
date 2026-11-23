# -*- coding: utf-8 -*-
"""TOTP two-factor authentication, key encryption, and one-time recovery codes. """
import base64
import hashlib
import hmac
import json
import re
import secrets
import time
from io import BytesIO

import pyotp
import qrcode
import qrcode.image.svg
from cryptography.fernet import Fernet, InvalidToken

import config


RECOVERY_ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'


def _key_material() -> bytes:
    """Derive an independent MFA key from the application master key. TOTP seeds are never stored in plaintext. """
    return hashlib.sha256(('crc-mfa:' + config.SECRET_KEY).encode('utf-8')).digest()


def _fernet() -> Fernet:
    return Fernet(base64.urlsafe_b64encode(_key_material()))


def encrypt_secret(secret: str) -> str:
    """Encrypt the TOTP secret. """
    return _fernet().encrypt((secret or '').encode('utf-8')).decode('ascii')


def decrypt_secret(token: str) -> str:
    """Decrypt the TOTP secret. Return an empty string if the master key changed or the data are corrupted. """
    if not token:
        return ''
    try:
        return _fernet().decrypt(token.encode('ascii')).decode('utf-8')
    except (InvalidToken, ValueError, UnicodeError):
        return ''


def generate_secret() -> str:
    """Generate a Base32 secret compatible with authenticator apps. """
    return pyotp.random_base32(length=32)


def provisioning_uri(secret: str, username: str) -> str:
    """Generate an otpauth:// provisioning URI. """
    return pyotp.TOTP(secret).provisioning_uri(
        name=username, issuer_name=config.MFA_ISSUER)


def qr_svg(uri: str) -> str:
    """"Render the provisioning URI as embedded SVG without sending secrets to third-party QR services. """
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=6,
        border=2,
    )
    qr.add_data(uri)
    qr.make(fit=True)
    image = qr.make_image(image_factory=qrcode.image.svg.SvgPathImage)
    output = BytesIO()
    image.save(output)
    svg = output.getvalue().decode('utf-8')
    return re.sub(r'^<\?xml[^>]*\?>\s*', '', svg)


def normalize_totp(code: str) -> str:
    return re.sub(r'\D', '', str(code or ''))


def verify_totp(secret: str, code: str, last_counter: int = 0) -> tuple:
    """Verify a TOTP code and return (whether verification passed, time counter used).

    Accept only the current time window and the configured adjacent windows, and reject replayed counters.
    """
    if not secret:
        return False, int(last_counter or 0)
    supplied = normalize_totp(code)
    if len(supplied) != 6:
        return False, int(last_counter or 0)

    totp = pyotp.TOTP(secret)
    current = int(time.time() // 30)
    used = int(last_counter or 0)
    for offset in range(-config.MFA_VALID_WINDOW, config.MFA_VALID_WINDOW + 1):
        counter = current + offset
        if counter <= used:
            continue
        expected = totp.generate_otp(counter)
        if hmac.compare_digest(expected, supplied):
            return True, counter
    return False, used


def normalize_recovery_code(code: str) -> str:
    return ''.join(ch for ch in str(code or '').upper() if ch.isalnum())


def _recovery_digest(code: str) -> str:
    value = normalize_recovery_code(code).encode('ascii', errors='ignore')
    return hmac.new(_key_material(), value, hashlib.sha256).hexdigest()


def generate_recovery_codes(count: int = None) -> list:
    """Generate recovery codes intended for one-time display. """
    total = int(count or config.MFA_RECOVERY_CODE_COUNT)
    codes = []
    for _ in range(total):
        raw = ''.join(secrets.choice(RECOVERY_ALPHABET) for _ in range(10))
        codes.append('%s-%s' % (raw[:5], raw[5:]))
    return codes


def hash_recovery_codes(codes: list) -> str:
    return json.dumps([_recovery_digest(code) for code in codes], separators=(',', ':'))


def verify_recovery_code(hashes_json: str, code: str) -> tuple:
    """Verify and atomically consume a recovery code. Return (whether verification passed, remaining hashes JSON). """
    try:
        hashes = json.loads(hashes_json or '[]')
    except (TypeError, ValueError):
        hashes = []
    if not isinstance(hashes, list):
        hashes = []
    digest = _recovery_digest(code)
    for index, saved in enumerate(hashes):
        if hmac.compare_digest(str(saved), digest):
            remaining = hashes[:index] + hashes[index + 1:]
            return True, json.dumps(remaining, separators=(',', ':'))
    return False, json.dumps(hashes, separators=(',', ':'))


def secret_display(secret: str) -> str:
    """Group the Base32 key into blocks of four characters for manual entry. """
    value = (secret or '').upper()
    return ' '.join(value[i:i + 4] for i in range(0, len(value), 4))
