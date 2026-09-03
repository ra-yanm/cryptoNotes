# Cryptographic Storage Implementation

This project uses three separate Python modules. The implementation is educational and demonstrates the algorithms requested for the CSE447 project. It is not a replacement for audited production cryptography.

## Module Responsibilities

### `rsa.py`

`rsa.py` contains a small RSA implementation:

1. Two random probable primes are generated with Miller-Rabin testing.
2. The modulus is calculated as `n = p * q`.
3. The public exponent is `e = 65537`.
4. The private exponent `d` is calculated using the modular inverse of `e`.
5. UTF-8 input is split into blocks and encrypted with modular exponentiation:

   `ciphertext = plaintext^e mod n`

6. Decryption uses:

   `plaintext = ciphertext^d mod n`

Encrypted blocks and their lengths are stored as JSON so they can be placed in a database `TEXT` column.

RSA is used for login credentials because login data is small. The API stores an encrypted JSON object containing the login identity and password.

### `ecc.py`

`ecc.py` implements elliptic-curve operations over the secp256k1 curve:

- Point addition
- Point doubling
- Scalar multiplication
- Private/public key generation
- Ephemeral key agreement

For each bulk value, a new ephemeral private key is generated. The sender and the application key derive the same shared point. A SHA-256 digest of the shared point becomes the encryption key.

The resulting bulk ciphertext includes:

- The ephemeral public point
- A random nonce
- XOR-encrypted data generated from an HMAC-SHA256 stream
- An HMAC authentication tag

The authentication tag detects tampering before the value is decrypted.

ECC is used for larger fields such as notes, suggestions, course descriptions, bios, and Discord IDs.

## `key_management.py`

This module is the only module imported by the application for normal encryption operations. It:

1. Creates a `.keys` directory if necessary.
2. Requires `KEY_PASSPHRASE` from `.env` or the process environment.
3. Generates RSA and ECC keys on first startup.
4. Encrypts the exported key data into passphrase-protected PEM files.
5. Loads and authenticates the same keys on later startups.
5. Exposes `encrypt_login`, `decrypt_login`, `encrypt_bulk`, and `decrypt_bulk`.

The key files are `.keys/rsa_private.pem` and `.keys/ecc_private.pem`. The key directory is excluded from Git. Losing these files or the passphrase means previously encrypted data cannot be decrypted, so production deployments should use a protected secret-management system and backups.

## Database Integration

The API integration is in `app.py`.

### Login records

The `secure_login` table contains:

- `identity_hash`: SHA-256 of the user ID or email, used for lookup without storing the identity as the lookup key
- `encrypted_credentials`: RSA-encrypted JSON containing the identity and password

Existing database rows contain plaintext passwords because they were part of the original SQL dump. On the first successful legacy login, the API:

1. Verifies the old plaintext password.
2. Stores RSA-encrypted credentials indexed by both user ID and email.
3. Clears the old `user.password` value.

Later logins use the encrypted record instead of the old password column.

### Bulk records

The API encrypts values before `INSERT` and `UPDATE`. It decrypts them after `SELECT`, immediately before returning JSON to the web application. Existing plaintext values remain readable through a compatibility fallback, but newly written values use ECC encryption.

The SQL dump changes the encrypted content columns to `TEXT` because encrypted JSON is larger than the original note and title values.

## Request Flow

```text
Browser
  -> web_app.py
  -> app.py API
  -> key_management.py
       -> rsa.py for login data
       -> ecc.py for bulk data
  -> MariaDB
```

For reads, the flow reverses: the API retrieves ciphertext, decrypts it through `key_management.py`, and returns plaintext to the existing templates.

## Verification

The modules can be checked with:

```text
python -m py_compile app.py web_app.py rsa.py ecc.py key_management.py
```

RSA and ECC round-trip tests verify that encrypted values decrypt to their original UTF-8 values.

## Important Limitations

This implementation is intended for demonstrating the requested algorithms. Production systems should use reviewed libraries such as `cryptography`, RSA-OAEP or a password-hashing function such as Argon2id/bcrypt, authenticated encryption such as AES-GCM or ChaCha20-Poly1305, constant-time curve implementations, key rotation, and a dedicated secret manager. Passwords should normally be hashed rather than reversibly encrypted.

## Registration and OTP Authentication

Registration is implemented in `forms.py` and `web_app.py` with Flask-WTF. `RegistrationForm` validates the user ID, email, name, department, password length, and matching confirmation password. Flask-WTF also adds CSRF protection to the browser forms.

The API registration flow is:

1. The web form sends the validated fields to `/api/register`.
2. The API hashes the password with `bcrypt` and never stores the original password.
3. The API creates a six-digit OTP, stores only its SHA-256 hash with a five-minute expiry, and sends the code through Flask-Mailman.
4. The user submits the code at `/verify-registration`.
5. `/api/verify-registration` consumes the one-time record and creates the account with `email_verified = 1`.

Login uses a separate OTP challenge:

1. `/api/login` checks the submitted password with `bcrypt.checkpw`.
2. The API sends a new six-digit OTP to the account email.
3. The browser submits that OTP to `/api/verify-login`.
4. Only after successful OTP verification does the web application create the user session.

OTP values are never returned in API responses or stored in plaintext. SMTP settings are supplied through `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_USE_TLS`, and `MAIL_DEFAULT_SENDER` environment variables.

## Local Environment Setup

Copy `.env.example` to `.env` and replace its placeholder values. The application loads `.env` automatically using `python-dotenv`. The `.env` file is ignored by Git and must not be committed. Database credentials, SMTP credentials, `WEB_SECRET_KEY`, and `KEY_PASSPHRASE` have no hardcoded fallback and must be supplied through `.env` or the process environment.

Start the API and web application with the configured environment:

```text
python app.py
python web_app.py
```

For Gmail, use an app password rather than the normal account password. The database password, Flask session secret, SMTP credentials, and private key directory are all configurable through `.env`.