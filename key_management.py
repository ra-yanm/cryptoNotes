"""Persistent local key storage and the application's encryption boundary."""

import json
import os
import base64
import hashlib
import hmac
import secrets
from pathlib import Path

from dotenv import load_dotenv
from ecc import ECC
from rsa import RSA


load_dotenv()
KEY_DIR = Path(os.getenv("KEY_DIRECTORY", Path(__file__).with_name(".keys")))
KEY_PASSPHRASE = os.getenv("KEY_PASSPHRASE")
if not KEY_PASSPHRASE:
    raise RuntimeError("KEY_PASSPHRASE must be set in .env or the environment")
RSA_FILE = KEY_DIR / "rsa_private.pem"
ECC_FILE = KEY_DIR / "ecc_private.pem"
ECC_KEYRING_FILE = KEY_DIR / "ecc_keyring.pem"


def _stream(key, length):
    return b"".join(
        hmac.new(key, counter.to_bytes(4, "big"), hashlib.sha256).digest()
        for counter in range((length + 31) // 32)
    )[:length]


def _write_pem(path, label, payload):
    salt = secrets.token_bytes(16)
    nonce = secrets.token_bytes(16)
    key = hashlib.scrypt(KEY_PASSPHRASE.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32)
    plaintext = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    ciphertext = bytes(a ^ b for a, b in zip(plaintext, _stream(key + nonce, len(plaintext))))
    tag = hmac.new(key, salt + nonce + ciphertext, hashlib.sha256).digest()
    encoded = base64.b64encode(salt + nonce + tag + ciphertext).decode("ascii")
    pem = f"-----BEGIN ENCRYPTED {label}-----\n"
    pem += "\n".join(encoded[index:index + 64] for index in range(0, len(encoded), 64))
    pem += f"\n-----END ENCRYPTED {label}-----\n"
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    temporary_path.write_text(pem, encoding="ascii")
    try:
        os.chmod(temporary_path, 0o600)
    except OSError:
        pass
    os.replace(temporary_path, path)


def _read_pem(path, label):
    text = path.read_text(encoding="ascii").strip()
    begin = f"-----BEGIN ENCRYPTED {label}-----"
    end = f"-----END ENCRYPTED {label}-----"
    if not text.startswith(begin) or not text.endswith(end):
        raise ValueError(f"Invalid encrypted PEM file: {path}")
    encoded = "".join(text[len(begin):].removesuffix(end).split())
    raw = base64.b64decode(encoded, validate=True)
    salt, nonce, tag, ciphertext = raw[:16], raw[16:32], raw[32:64], raw[64:]
    key = hashlib.scrypt(KEY_PASSPHRASE.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32)
    expected = hmac.new(key, salt + nonce + ciphertext, hashlib.sha256).digest()
    if not hmac.compare_digest(tag, expected):
        raise ValueError("Invalid KEY_PASSPHRASE or corrupted key file")
    plaintext = bytes(a ^ b for a, b in zip(ciphertext, _stream(key + nonce, len(ciphertext))))
    return json.loads(plaintext.decode("utf-8"))


def _load_or_create(path, factory):
    KEY_DIR.mkdir(mode=0o700, exist_ok=True)
    if path.exists():
        return factory.from_export(_read_pem(path, factory.__name__.upper()))
    legacy_name = "rsa.json" if factory is RSA else "ecc.json"
    legacy_path = KEY_DIR / legacy_name
    if legacy_path.exists():
        payload = json.loads(legacy_path.read_text(encoding="utf-8"))
        _write_pem(path, factory.__name__.upper(), payload)
        legacy_path.unlink()
        return factory.from_export(payload)
    key = factory()
    _write_pem(path, factory.__name__.upper(), key.export())
    return key


RSA_KEY = _load_or_create(RSA_FILE, RSA)
_legacy_ecc_key = _load_or_create(ECC_FILE, ECC)
if ECC_KEYRING_FILE.exists():
    _ecc_keyring = _read_pem(ECC_KEYRING_FILE, "ECC-KEYRING")
    ECC_KEYS = {
        key_id: ECC.from_export(key_data)
        for key_id, key_data in _ecc_keyring["keys"].items()
    }
    ECC_ACTIVE_KEY_ID = _ecc_keyring["active"]
else:
    ECC_KEYS = {"v1": _legacy_ecc_key}
    ECC_ACTIVE_KEY_ID = "v1"
    _write_pem(
        ECC_KEYRING_FILE,
        "ECC-KEYRING",
        {"active": ECC_ACTIVE_KEY_ID, "keys": {"v1": _legacy_ecc_key.export()}},
    )
ECC_KEY = ECC_KEYS[ECC_ACTIVE_KEY_ID]


def encrypt_user_field(value):
    return RSA_KEY.encrypt(value) if value is not None else None


def decrypt_user_field(value):
    if value is None or not isinstance(value, str):
        return value
    if value.startswith('{"version":2'):
        return RSA_KEY.decrypt(value)
    if value.startswith('{"ephemeral":'):
        return decrypt_bulk(value)
    return value


def encrypt_bulk(value):
    return encrypt_bulk_with_key(value, ECC_ACTIVE_KEY_ID)


def encrypt_bulk_with_key(value, key_id):
    if value is None:
        return None
    payload = json.loads(ECC_KEYS[key_id].encrypt(value))
    payload["key_id"] = key_id
    return json.dumps(payload, separators=(",", ":"))


def decrypt_bulk(value):
    if value is None or not isinstance(value, str) or not value.startswith('{"ephemeral":'):
        return value
    payload = json.loads(value)
    key_id = payload.get("key_id", "v1")
    return ECC_KEYS[key_id].decrypt(value)


def rotate_ecc_key():
    """Create and persist a new ECC key while retaining every prior key."""
    numeric_ids = [
        int(key_id[1:]) for key_id in ECC_KEYS if key_id.startswith("v") and key_id[1:].isdigit()
    ]
    new_id = f"v{max(numeric_ids, default=0) + 1}"
    new_key = ECC()
    new_keys = dict(ECC_KEYS)
    new_keys[new_id] = new_key
    _write_pem(
        ECC_KEYRING_FILE,
        "ECC-KEYRING",
        {"active": new_id, "keys": {key_id: key.export() for key_id, key in new_keys.items()}},
    )
    ECC_KEYS.clear()
    ECC_KEYS.update(new_keys)
    global ECC_ACTIVE_KEY_ID, ECC_KEY
    ECC_ACTIVE_KEY_ID = new_id
    ECC_KEY = new_key
    return new_id