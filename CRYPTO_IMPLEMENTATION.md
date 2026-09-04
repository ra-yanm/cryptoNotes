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

Encrypted blocks and their lengths are stored as JSON so they can be placed in a database `TEXT` column. The JSON payload also contains a version and an HMAC-SHA256 tag. The tag covers the complete RSA payload, excluding the tag itself, using a key derived from the RSA private key. Decryption verifies this tag with `hmac.compare_digest()` before processing any RSA blocks.

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

The authentication tag detects tampering before the value is decrypted. The tag covers the nonce and ciphertext.

ECC is used for larger fields such as notes, suggestions, course descriptions, bios, and Discord IDs.

### Note Messages

Note questions use per-user ECC key pairs. A key pair is created for a student or faculty member when they first send or open a message conversation. The public key is stored in `user_ecc_keys`, while the private key is encrypted with the application's existing ECC key before it is stored.

Each message is encrypted twice with `ecc.py`: once for the student's public key and once for the course coordinator's public key. This allows both participants to read the conversation while the database stores only ciphertext. Each encrypted copy has its own HMAC-SHA256 tag covering its nonce and ciphertext. The API authorizes access through the note's course coordinator and the authenticated student before decrypting a message for display.

## `key_management.py`

This module is the only module imported by the application for normal encryption operations. It:

1. Creates a `.keys` directory if necessary.
2. Requires `KEY_PASSPHRASE` from `.env` or the process environment.
3. Generates RSA and ECC keys on first startup.
4. Encrypts the exported key data into passphrase-protected PEM files.
5. Loads and authenticates the same keys on later startups.
6. Exposes `encrypt_login`, `decrypt_login`, `encrypt_bulk`, and `decrypt_bulk`.

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

## Message Authentication Code (MAC)

The system uses HMAC-SHA256 for integrity and authentication. HMAC is safer and simpler than CBC-MAC for the variable-length JSON and text values stored by this application. It does not require block padding and uses Python's `hmac` and `hashlib` implementations.

ECC bulk values calculate a tag over `nonce + ciphertext` with the key derived from the shared elliptic-curve point. RSA login records calculate a tag over the version, encrypted blocks, and block lengths with a key derived from the RSA private key. Encrypted key files calculate a tag over `salt + nonce + ciphertext` using the passphrase-derived key.

MAC verification occurs on every decryption. The tag is checked with `hmac.compare_digest()` before plaintext is returned or encrypted blocks are processed. Any invalid, missing, or malformed authentication data raises an error and is rejected. The plaintext fallback applies only to database values that are clearly not in the encrypted ECC JSON format, so an authenticated ciphertext failure is never treated as plaintext.

## Implemented Integrity Changes

The integrity requirement was implemented in the following way:

1. Added HMAC-SHA256 authentication to RSA login ciphertext. RSA payloads now include `version`, `blocks`, `lengths`, and `tag` fields.
2. RSA decryption verifies the tag before decrypting blocks. Missing tags, unsupported versions, and modified payloads are rejected.
3. Retained the existing HMAC-SHA256 protection for ECC bulk data and encrypted key files.
4. Changed bulk-data handling so an ECC authentication failure is raised instead of being silently returned as plaintext.
5. Kept compatibility for legacy database rows that are plainly stored as unencrypted text.

Newly encrypted data is authenticated automatically through `key_management.py`. Existing RSA ciphertext created before this change does not contain a MAC and must be re-encrypted before it can be used with the updated implementation.

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

## Web Security Controls

The web application enables `HttpOnly` cookies so client-side JavaScript cannot read the session cookie, `SameSite=Lax` to reduce cross-site request forgery, and configurable `Secure` cookies for HTTPS deployments through `SESSION_COOKIE_SECURE=true`. Keep it `false` only for local HTTP development.

Flask-WTF `CSRFProtect` validates a token on every browser `POST`. WTForms generate tokens automatically, and manual forms include the token explicitly. API requests are kept behind the web application's server-side request boundary.

The session is cleared and rebuilt after successful login OTP verification, which rotates the signed session contents and prevents an attacker from fixing a pre-authentication session. Authenticated sessions expire after 30 minutes of inactivity. The `before_request` hook clears expired sessions before redirecting to login.

Jinja autoescaping is retained for all user- and database-originated text. Stored `|safe` output was removed, preventing notes or suggestions from becoming executable HTML. Inline JavaScript and inline event handlers were moved to `static/app.js`; the response Content Security Policy allows scripts only from the application origin. Additional headers disable framing, MIME sniffing, and unsafe referrer disclosure.

These controls reduce XSS, session theft, session fixation, CSRF, clickjacking, and DOM injection risk. They do not replace HTTPS, secure server deployment, dependency updates, authorization checks, or a production secret manager.