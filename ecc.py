"""Educational ECC key agreement and authenticated encryption for bulk fields."""

import hashlib
import hmac
import json
import secrets


# Standard secp256k1 curve parameters used by the website's ECC key agreement.
# P is the prime field modulus; the curve is y^2 = x^3 + 7 (mod P).
# N is the order of the generator point, and G is that generator point.
P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
G = (55066263022277343669578518895168534326250603453777594175500187360389116729240,
     32670510020758816978083085130507043184471273380659243275938904335757337482424)


def inverse_mod(value, modulus):
    # Return the modular inverse used to calculate an ECC line slope.
    return pow(value % modulus, -1, modulus)


def point_add(left, right):
    # left and right are curve points; None represents the point at infinity.
    # The point at infinity is the identity element for addition.
    if left is None:
        return right
    if right is None:
        return left
    if left[0] == right[0] and (left[1] + right[1]) % P == 0:
        # Opposite points add to the point at infinity.
        return None
    if left == right:
        # For doubling, slope = (3*x^2) / (2*y) because secp256k1 has a = 0.
        denominator = 2 * left[1] % P
        if denominator == 0:
            return None
        slope = (3 * left[0] * left[0]) % P
        slope = slope * inverse_mod(denominator, P) % P
    else:
        # For two different points, slope = (y2-y1) / (x2-x1).
        denominator = (right[0] - left[0]) % P
        slope = (right[1] - left[1]) % P
        slope = slope * inverse_mod(denominator, P) % P
    x = (slope * slope - left[0] - right[0]) % P
    # The formulas below calculate the x and y coordinates of left + right.
    return x, (slope * (left[0] - x) - left[1]) % P


def scalar_mult(scalar, point=G):
    # Double-and-add computes scalar * point efficiently.
    if scalar < 0:
        raise ValueError("scalar must be non-negative")
    result = None
    while scalar > 0:
        # An odd current scalar bit means this point contributes to the result.
        if scalar % 2 == 1:
            result = _add(result, point)
        # Double the point before processing the next binary bit.
        point = point_add(point, point)
        # Divide by two to move to the next scalar bit.
        scalar //= 2
    return result


_add = point_add
_multiply = scalar_mult


def _stream(key, length):
    # Generate a repeatable HMAC-SHA256 byte stream for XOR encryption.
    return b"".join(hmac.new(key, counter.to_bytes(4, "big"), hashlib.sha256).digest()
                    for counter in range((length + 31) // 32))[:length]


class ECC:
    def __init__(self, private_key=None):
        # key_management.py restores this key when the website starts.
        # A private key is a secret scalar; the public key is private_key * G.
        self.private_key = private_key or secrets.randbelow(N - 1) + 1
        self.public_key = _multiply(self.private_key)

    def export(self):
        # Store integer key values in JSON-compatible form for key_management.py.
        return {"private": self.private_key, "public": list(self.public_key)}

    @classmethod
    def from_export(cls, payload):
        # Rebuild the ECC object from the stored private key.
        return cls(payload["private"])

    def encrypt(self, value):
        # The website uses ECC for larger fields such as notes and profiles.
        # raw is the original website text represented as UTF-8 bytes.
        raw = value.encode("utf-8") if isinstance(value, str) else bytes(value)
        # ephemeral is a new temporary private key for this one encryption.
        ephemeral = secrets.randbelow(N - 1) + 1
        # The ephemeral public key allows the receiver to derive the same key.
        shared = _multiply(ephemeral, self.public_key)
        # Both sides derive the same shared point without sending private keys.
        key = hashlib.sha256(shared[0].to_bytes(32, "big")).digest()
        # nonce makes the generated HMAC stream unique for this ciphertext.
        nonce = secrets.token_bytes(16)
        # XOR the plaintext bytes with the generated stream to produce ciphertext.
        ciphertext = bytes(a ^ b for a, b in zip(raw, _stream(key + nonce, len(raw))))
        # The tag detects modified nonce or ciphertext before decryption.
        tag = hmac.new(key, nonce + ciphertext, hashlib.sha256).hexdigest()
        # Store all required values as JSON for the database TEXT column.
        return json.dumps({"ephemeral": list(_multiply(ephemeral)), "nonce": nonce.hex(), "data": ciphertext.hex(), "tag": tag}, separators=(",", ":"))

    def decrypt(self, ciphertext):
        # Called after a website read to recover an encrypted database value.
        # Read the temporary public point sent with the encrypted value.
        payload = json.loads(ciphertext)
        # The receiver combines its private key with that point to get the same key.
        shared = _multiply(self.private_key, tuple(payload["ephemeral"]))
        key = hashlib.sha256(shared[0].to_bytes(32, "big")).digest()
        # Convert the stored hexadecimal strings back into bytes.
        nonce = bytes.fromhex(payload["nonce"])
        data = bytes.fromhex(payload["data"])
        # Verify authenticity before attempting to recover plaintext.
        expected = hmac.new(key, nonce + data, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, payload["tag"]):
            raise ValueError("ECC authentication failed")
        # XOR with the same stream to recover the original UTF-8 text.
        return bytes(a ^ b for a, b in zip(data, _stream(key + nonce, len(data)))).decode("utf-8")