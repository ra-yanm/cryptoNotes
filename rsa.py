"""Small, self-contained RSA implementation for encrypted login records."""

import json
import secrets


def _egcd(a, b):
    if b == 0:
        return a, 1, 0
    gcd, x, y = _egcd(b, a % b)
    return gcd, y, x - (a // b) * y


def _mod_inverse(value, modulus):
    gcd, inverse, _ = _egcd(value, modulus)
    if gcd != 1:
        raise ValueError("RSA inverse does not exist")
    return inverse % modulus


def _is_prime(candidate):
    if candidate < 2 or candidate % 2 == 0:
        return candidate == 2
    odd_part = candidate - 1
    rounds = 0
    while odd_part % 2 == 0:
        odd_part //= 2
        rounds += 1
    for base in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        if base >= candidate:
            continue
        result = pow(base, odd_part, candidate)
        if result in (1, candidate - 1):
            continue
        for _ in range(rounds - 1):
            result = pow(result, 2, candidate)
            if result == candidate - 1:
                break
        else:
            return False
    return True


def _prime(bits):
    while True:
        candidate = secrets.randbits(bits) | (1 << (bits - 1)) | 1
        if _is_prime(candidate):
            return candidate


class RSA:
    def __init__(self, private_key=None, public_key=None, bits=512):
        if private_key and public_key:
            self.n, self.d = private_key
            self.public_n, self.e = public_key
            return
        while True:
            first = _prime(bits // 2)
            second = _prime(bits // 2)
            if first != second:
                modulus = first * second
                phi = (first - 1) * (second - 1)
                if _egcd(65537, phi)[0] == 1:
                    break
        self.n, self.d = modulus, _mod_inverse(65537, phi)
        self.public_n, self.e = modulus, 65537

    def private_key(self):
        return self.n, self.d

    def public_key(self):
        return self.public_n, self.e

    def encrypt(self, value):
        raw = value.encode("utf-8") if isinstance(value, str) else bytes(value)
        limit = (self.public_n.bit_length() - 1) // 8 - 2
        blocks = []
        lengths = []
        for offset in range(0, len(raw), limit):
            chunk = raw[offset:offset + limit]
            number = int.from_bytes(len(chunk).to_bytes(2, "big") + chunk, "big")
            blocks.append(pow(number, self.e, self.public_n))
            lengths.append(len(chunk) + 2)
        return json.dumps({"blocks": blocks, "lengths": lengths}, separators=(",", ":"))

    def decrypt(self, ciphertext):
        payload = json.loads(ciphertext)
        block_size = (self.n.bit_length() - 1) // 8
        raw = []
        for block, length in zip(payload["blocks"], payload["lengths"]):
            decoded = pow(block, self.d, self.n).to_bytes(block_size, "big")
            chunk = decoded[-length:]
            raw.append(chunk[2:2 + int.from_bytes(chunk[:2], "big")])
        return b"".join(raw).decode("utf-8")

    def export(self):
        return {"private": [self.n, self.d], "public": [self.public_n, self.e]}

    @classmethod
    def from_export(cls, payload):
        return cls(tuple(payload["private"]), tuple(payload["public"]))