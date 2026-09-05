# CryptoNotes: RSA, ECC, HMAC, bcrypt, and salts

This guide maps the cryptography in this project to the source code. The project is educational: production systems should use audited libraries such as `cryptography` and a dedicated secret manager.

## Quick map

| Concept | Project file | Main purpose |
|---|---|---|
| RSA | `rsa.py` | Encrypt short user profile fields |
| ECC | `ecc.py` | Encrypt larger values and exchange message keys |
| HMAC-SHA256 | `rsa.py`, `ecc.py`, `key_management.py` | Detect tampering and authenticate ciphertext |
| bcrypt | `app.py` | Hash user passwords for login |
| Salt | `app.py`, `key_management.py` | Make password/key derivation outputs unique |
| scrypt | `key_management.py` | Derive a key from `KEY_PASSPHRASE` to protect private key files |

## 1. RSA

RSA is public-key cryptography. It uses a public key `(n, e)` for encryption and a private key `(n, d)` for decryption.

In `rsa.py`, the key is created as follows:

```python
first = _prime(bits // 2)
second = _prime(bits // 2)
modulus = first * second
phi = (first - 1) * (second - 1)
self.n, self.d = modulus, _mod_inverse(65537, phi)
self.public_n, self.e = modulus, 65537
```

The core operations are modular exponentiation:

```python
# Encryption with the public key
ciphertext = pow(number, self.e, self.public_n)

# Decryption with the private key
decoded = pow(block, self.d, self.n)
```

Where it is used:

- `key_management.py`: `encrypt_user_field()` and `decrypt_user_field()` use the application RSA key.
- `app.py`: profile values such as `name`, `department`, `bio`, `personal_phn`, and `discord_id` are stored through those helpers.
- `rsa.py`: the plaintext is split into blocks because RSA can only process values smaller than its modulus.

RSA is suitable here only for short values. The implementation also adds an HMAC tag because basic RSA encryption alone does not detect database tampering.

## 2. ECC

Elliptic-curve cryptography uses points on a curve. This project uses secp256k1. A private key is a random number and the public key is the private key multiplied by the generator point:

```python
self.private_key = private_key or secrets.randbelow(N - 1) + 1
self.public_key = _multiply(self.private_key)
```

The important operation is scalar multiplication:

```python
shared = scalar_mult(ephemeral, tuple(public_key))
key = hashlib.sha256(shared[0].to_bytes(32, "big")).digest()
```

The sender creates a temporary (ephemeral) private key. The recipient combines the sender's ephemeral public key with the recipient's private key. Both sides calculate the same shared secret, but an observer cannot calculate it without a private key.

Where it is used:

- `key_management.py`: notes, course content, suggestions, and other bulk fields use `encrypt_bulk()` and `decrypt_bulk()`.
- `app.py`: per-user ECC key pairs are stored in `user_ecc_keys` for note messages.
- `app.py`: each message is encrypted separately for the student and faculty recipient using `encrypt_for()`.

The project derives an HMAC key from the shared point, creates a keystream, XORs the plaintext with that keystream, and authenticates the result. This demonstrates the concepts, but an audited authenticated-encryption library such as AES-GCM or ChaCha20-Poly1305 is preferred in production.

## 3. HMAC-SHA256

HMAC is a keyed integrity check. It answers: "Was this data changed, and was it produced by someone who knows the secret key?" It does not hide data by itself.

ECC ciphertext:

```python
tag = hmac.new(key, nonce + ciphertext, hashlib.sha256).hexdigest()

expected = hmac.new(key, nonce + data, hashlib.sha256).hexdigest()
if not hmac.compare_digest(expected, payload["tag"]):
    raise ValueError("ECC authentication failed")
```

RSA ciphertext uses an HMAC over the JSON payload, excluding the tag itself:

```python
message = json.dumps(payload, sort_keys=True,
                     separators=(",", ":")).encode("utf-8")
return hmac.new(self._mac_key(), message, hashlib.sha256).hexdigest()
```

Encrypted key files in `key_management.py` also use HMAC over `salt + nonce + ciphertext`. Every tag is checked before plaintext is returned. `hmac.compare_digest()` is used to reduce timing side-channel leakage during comparison.

## 4. bcrypt

bcrypt is a password-hashing function, not an encryption algorithm. A password hash is intentionally one-way: the application does not need to decrypt a user's password. It only checks whether a submitted password produces a valid result.

The implementation is in `app.py`:

```python
def hash_password(password):
    return bcrypt.hashpw(
        password.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")


def check_password(password, password_hash):
    return bcrypt.checkpw(
        password.encode("utf-8"), password_hash.encode("utf-8")
    )
```

Where it is used:

- Registration calls `hash_password()` and stores the resulting string in `user.password`.
- Login calls `check_password()` against the stored hash.
- The admin password is handled with the same functions.

The original password is never stored. Do not replace bcrypt with RSA or ECC for passwords; passwords should normally be hashed, not reversibly encrypted.

## 5. Salt

A salt is a random, non-secret value added to a password or passphrase before key derivation. It prevents identical passwords from producing identical derived values and makes precomputed rainbow tables ineffective. The salt can be stored next to the hash or ciphertext.

### bcrypt salt

`bcrypt.gensalt()` creates and embeds a random salt in the bcrypt string returned by `hashpw()`:

```python
bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
```

When `checkpw()` runs, bcrypt reads the embedded salt and repeats the calculation. A separate salt column is not needed.

### Key-file salt

`key_management.py` creates a fresh 16-byte salt whenever it writes an encrypted private-key file:

```python
salt = secrets.token_bytes(16)
key = hashlib.scrypt(
    KEY_PASSPHRASE.encode("utf-8"),
    salt=salt, n=2**14, r=8, p=1, dklen=32
)
```

The salt is stored at the beginning of the PEM payload, so the same passphrase can derive the same key when the file is read. The salt is not a password and does not need to be secret. The passphrase and derived key do need protection.

## 6. How the pieces fit together

```text
Password registration
  password -> bcrypt + random salt -> stored password hash

Profile field
  plaintext -> RSA encryption + HMAC tag -> database

Note or course content
  plaintext -> ECC shared key -> stream encryption + HMAC tag -> database

Private RSA/ECC key file
  KEY_PASSPHRASE + random salt -> scrypt key
  key data -> encrypted payload + HMAC tag -> PEM file
```

On reads, the application verifies the HMAC before accepting encrypted data. It then decrypts profile/content fields through `key_management.py` before returning them to the web application.

## 8. Important limitations

- `rsa.py` and `ecc.py` are custom educational implementations, not audited cryptographic libraries.
- The RSA implementation should use RSA-OAEP in production.
- The ECC stream-and-HMAC construction should be replaced with an audited AEAD construction such as AES-GCM or ChaCha20-Poly1305.
- The key files depend on both the `.keys` directory and `KEY_PASSPHRASE`; losing either prevents decryption of existing data.
- `KEY_PASSPHRASE`, database credentials, mail credentials, and Flask secrets must remain outside source control.

## Source locations

- [rsa.py](rsa.py): RSA key generation, block encryption, decryption, and RSA HMAC tags.
- [ecc.py](ecc.py): secp256k1 operations, ECC encryption, decryption, and HMAC tags.
- [key_management.py](key_management.py): key-file encryption, scrypt, salts, and application encryption helpers.
- [app.py](app.py): bcrypt password functions and database call sites.
- [CRYPTO_IMPLEMENTATION.md](CRYPTO_IMPLEMENTATION.md): the longer implementation record.
