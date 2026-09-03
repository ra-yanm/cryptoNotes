"""Educational ECC key agreement and authenticated encryption for bulk fields."""

import hashlib
import hmac
import json
import secrets


P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
G = (55066263022277343669578518895168534326250603453777594175500187360389116729240,
     32670510020758816978083085130507043184471273380659243275938904335757337482424)


def _add(left, right):
    if left is None:
        return right
    if right is None:
        return left
    if left[0] == right[0] and (left[1] + right[1]) % P == 0:
        return None
    if left == right:
        slope = 3 * left[0] * left[0] * pow(2 * left[1], P - 2, P) % P
    else:
        slope = (right[1] - left[1]) * pow(right[0] - left[0], P - 2, P) % P
    x = (slope * slope - left[0] - right[0]) % P
    return x, (slope * (left[0] - x) - left[1]) % P


def _multiply(scalar, point=G):
    result = None
    while scalar:
        if scalar & 1:
            result = _add(result, point)
        point = _add(point, point)
        scalar >>= 1
    return result


def _stream(key, length):
    return b"".join(hmac.new(key, counter.to_bytes(4, "big"), hashlib.sha256).digest()
                    for counter in range((length + 31) // 32))[:length]


class ECC:
    def __init__(self, private_key=None):
        self.private_key = private_key or secrets.randbelow(N - 1) + 1
        self.public_key = _multiply(self.private_key)

    def export(self):
        return {"private": self.private_key, "public": list(self.public_key)}

    @classmethod
    def from_export(cls, payload):
        return cls(payload["private"])

    def encrypt(self, value):
        raw = value.encode("utf-8") if isinstance(value, str) else bytes(value)
        ephemeral = secrets.randbelow(N - 1) + 1
        shared = _multiply(ephemeral, self.public_key)
        key = hashlib.sha256(shared[0].to_bytes(32, "big")).digest()
        nonce = secrets.token_bytes(16)
        ciphertext = bytes(a ^ b for a, b in zip(raw, _stream(key + nonce, len(raw))))
        tag = hmac.new(key, nonce + ciphertext, hashlib.sha256).hexdigest()
        return json.dumps({"ephemeral": list(_multiply(ephemeral)), "nonce": nonce.hex(), "data": ciphertext.hex(), "tag": tag}, separators=(",", ":"))

    def decrypt(self, ciphertext):
        payload = json.loads(ciphertext)
        shared = _multiply(self.private_key, tuple(payload["ephemeral"]))
        key = hashlib.sha256(shared[0].to_bytes(32, "big")).digest()
        nonce = bytes.fromhex(payload["nonce"])
        data = bytes.fromhex(payload["data"])
        expected = hmac.new(key, nonce + data, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, payload["tag"]):
            raise ValueError("ECC authentication failed")
        return bytes(a ^ b for a, b in zip(data, _stream(key + nonce, len(data)))).decode("utf-8")