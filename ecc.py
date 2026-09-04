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


def encrypt_for(public_key, value):
    """Encrypt value for the owner of public_key using an ephemeral ECC key."""
    raw = value.encode("utf-8") if isinstance(value, str) else bytes(value)
    ephemeral = secrets.randbelow(N - 1) + 1
    shared = scalar_mult(ephemeral, tuple(public_key))
    key = hashlib.sha256(shared[0].to_bytes(32, "big")).digest()
    nonce = secrets.token_bytes(16)
    ciphertext = bytes(a ^ b for a, b in zip(raw, _stream(key + nonce, len(raw))))
    tag = hmac.new(key, nonce + ciphertext, hashlib.sha256).hexdigest()
    return json.dumps({
        "ephemeral": list(scalar_mult(ephemeral)),
        "nonce": nonce.hex(),
        "data": ciphertext.hex(),
        "tag": tag,
    }, separators=(",", ":"))


def decrypt_with(private_key, ciphertext):
    """Decrypt and authenticate a payload with the matching private key."""
    payload = json.loads(ciphertext)
    shared = scalar_mult(private_key, tuple(payload["ephemeral"]))
    key = hashlib.sha256(shared[0].to_bytes(32, "big")).digest()
    nonce = bytes.fromhex(payload["nonce"])
    data = bytes.fromhex(payload["data"])
    expected = hmac.new(key, nonce + data, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, payload["tag"]):
        raise ValueError("ECC authentication failed")
    return bytes(a ^ b for a, b in zip(data, _stream(key + nonce, len(data)))).decode("utf-8")


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
        return encrypt_for(self.public_key, value)

    def decrypt(self, ciphertext):
        # Called after a website read to recover an encrypted database value.
        return decrypt_with(self.private_key, ciphertext)