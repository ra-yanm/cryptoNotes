"""Small, self-contained RSA implementation for encrypted user fields."""

import hashlib
import hmac
import json
import secrets
import sympy


def _egcd(a, b):
    # Extended Euclidean algorithm: return gcd(a, b) and coefficients x, y
    # such that a*x + b*y = gcd(a, b).
    if b == 0:
        return a, 1, 0
    # Reduce the problem until the remainder becomes zero.
    gcd, x, y = _egcd(b, a % b)
    # Rearrange the returned coefficients for the original a and b.
    return gcd, y, x - (a // b) * y


def _mod_inverse(value, modulus):
    # The modular inverse is the number that makes value * inverse = 1 mod modulus.
    gcd, inverse, _ = _egcd(value, modulus)
    if gcd != 1:
        raise ValueError("RSA inverse does not exist")
    return inverse % modulus


def _is_prime(candidate):
    # SymPy performs the primality test for the randomly generated RSA numbers.
    return bool(sympy.isprime(candidate))


def _prime(bits):
    # Generate an odd prime with the requested bit length.
    while True:
        candidate = secrets.randbits(bits) | (1 << (bits - 1)) | 1
        if _is_prime(candidate):
            return candidate


class RSA:
    def __init__(self, private_key=None, public_key=None, bits=512):
        # key_management.py restores these keys when the website starts.
        if private_key and public_key:
            # A private key contains n and d; a public key contains n and e.
            self.n, self.d = private_key
            self.public_n, self.e = public_key
            return
        while True:
            # Choose p and q so that e has a modular inverse modulo phi(n).
            first = _prime(bits // 2)
            second = _prime(bits // 2)
            if first != second:
                # RSA's modulus is n = p*q.
                modulus = first * second
                # phi(n) is used to calculate the private exponent d.
                phi = (first - 1) * (second - 1)
                if _egcd(65537, phi)[0] == 1:
                    break
        # 65537 is the public exponent; d is its inverse modulo phi(n).
        self.n, self.d = modulus, _mod_inverse(65537, phi)
        self.public_n, self.e = modulus, 65537

    def private_key(self):
        return self.n, self.d

    def public_key(self):
        return self.public_n, self.e

    def _mac_key(self):
        # Derive a separate HMAC key from the private RSA key for integrity checks.
        key_material = f"{self.n}:{self.d}".encode("ascii")
        return hashlib.sha256(key_material).digest()

    def _tag(self, payload):
        # Serialize the payload consistently before calculating its HMAC tag.
        message = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hmac.new(self._mac_key(), message, hashlib.sha256).hexdigest()

    def encrypt(self, value):
        # The website uses RSA for small user profile values.
        # raw is the original text converted into bytes for RSA arithmetic.
        raw = value.encode("utf-8") if isinstance(value, str) else bytes(value)
        # RSA can only encrypt numbers smaller than n, so long input is split.
        limit = (self.public_n.bit_length() - 1) // 8 - 2
        # blocks stores encrypted integer values; lengths preserves block sizes.
        blocks = []
        lengths = []
        # Encode each block before RSA modular exponentiation.
        for offset in range(0, len(raw), limit):
            # chunk is one portion of the original byte string.
            chunk = raw[offset:offset + limit]
            # Store the chunk length before converting the bytes to an integer.
            number = int.from_bytes(len(chunk).to_bytes(2, "big") + chunk, "big")
            # RSA encryption: c = m^e mod n.
            blocks.append(pow(number, self.e, self.public_n))
            lengths.append(len(chunk) + 2)
        # JSON makes the encrypted result suitable for a database TEXT column.
        payload = {"version": 2, "blocks": blocks, "lengths": lengths}
        # The tag lets the website detect modified database ciphertext.
        payload["tag"] = self._tag(payload)
        return json.dumps(payload, separators=(",", ":"))

    def decrypt(self, ciphertext):
        # Called after a website read to recover the original login value.
        # Convert the database JSON string back into a Python dictionary.
        payload = json.loads(ciphertext)
        # Remove the tag from the data being checked, then verify it first.
        tag = payload.pop("tag", None)
        if payload.get("version") != 2 or not isinstance(tag, str):
            raise ValueError("Unauthenticated RSA ciphertext")
        expected = self._tag(payload)
        if not hmac.compare_digest(expected, tag):
            raise ValueError("RSA authentication failed")
        # Decode each RSA block back into a fixed-width byte sequence.
        block_size = (self.n.bit_length() - 1) // 8
        raw = []
        for block, length in zip(payload["blocks"], payload["lengths"]):
            # RSA decryption: m = c^d mod n.
            decoded = pow(block, self.d, self.n).to_bytes(block_size, "big")
            # Keep only the bytes belonging to the original encoded chunk.
            chunk = decoded[-length:]
            # Remove the two-byte length prefix and append the original data.
            raw.append(chunk[2:2 + int.from_bytes(chunk[:2], "big")])
        # Join all chunks and convert UTF-8 bytes back to website text.
        return b"".join(raw).decode("utf-8")

    def export(self):
        # key_management.py stores this exported key data in an encrypted file.
        return {"private": [self.n, self.d], "public": [self.public_n, self.e]}

    @classmethod
    def from_export(cls, payload):
        # Rebuild an RSA object from the key-management JSON representation.
        return cls(tuple(payload["private"]), tuple(payload["public"]))