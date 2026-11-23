# -*- coding: utf-8 -*-
"""Database backup encryption using Fernet (AES-128-CBC + HMAC) with an independent key file. """
import os

from cryptography.fernet import Fernet, InvalidToken

import config
from util_logger import get_logger

logger = get_logger(__name__)
KEY_PATH = os.path.join(config.DATA_DIR, '.backup_key')


def load_backup_key() -> bytes:
    """Read or generate a standalone backup key. """
    os.makedirs(config.DATA_DIR, exist_ok=True)
    env_key = (os.getenv('CRC_BACKUP_KEY') or '').strip()
    if env_key:
        return env_key.encode('ascii')
    try:
        if os.path.exists(KEY_PATH):
            value = open(KEY_PATH, 'rb').read().strip()
            if value:
                return value
        value = Fernet.generate_key()
        with open(KEY_PATH, 'wb') as file:
            file.write(value)
        logger.warning('Backup key generated: %s (store it securely offline)', KEY_PATH)
        return value
    except OSError:
        raise RuntimeError('Unable to read or create backup key')


def encrypt_bytes(payload: bytes) -> bytes:
    return Fernet(load_backup_key()).encrypt(payload)


def decrypt_bytes(payload: bytes) -> bytes:
    try:
        return Fernet(load_backup_key()).decrypt(payload)
    except InvalidToken as exc:
        raise ValueError('Backup decryption failed: key mismatch or corrupted file') from exc


def encrypt_file(source: str, target: str = None) -> str:
    target = target or (source + '.enc')
    with open(source, 'rb') as file:
        payload = file.read()
    with open(target, 'wb') as file:
        file.write(encrypt_bytes(payload))
    return target


def decrypt_file(source: str) -> bytes:
    with open(source, 'rb') as file:
        return decrypt_bytes(file.read())
