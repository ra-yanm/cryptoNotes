# CryptoNotes

CryptoNotes is a Flask-based course notes application for students, faculty, and administrators. It supports user registration and OTP login, course and note management, suggestions, profiles, and encrypted questions between students and course coordinators.

The project uses a separate API server and web server. MariaDB stores the application data. Profile fields use the application RSA key, while notes, course content, suggestions, and messages use the ECC-based encryption modules in this repository.

## Project Structure

```text
447project/
├── app.py                  # API server and database operations
├── web_app.py              # Flask web interface
├── ecc.py                 # Educational ECC implementation
├── rsa.py                 # Educational RSA implementation
├── key_management.py      # Encrypted key-file storage and rotation
├── forms.py               # Flask-WTF forms
├── flaskDB447.sql         # MariaDB schema and sample data
├── requirements.txt       # Python dependencies
├── Pipfile               # Pipenv configuration
├── static/                # JavaScript and CSS
└── templates/             # Jinja HTML templates
```

## Requirements

- Windows, macOS, or Linux
- Python 3.13 (the Pipfile specifies Python 3.13)
- XAMPP with MariaDB/MySQL
- SMTP credentials for registration and login OTP email

## Local Setup

### 1. Start MariaDB

In XAMPP, start **MySQL**. The default local configuration uses MariaDB on port `3306`.

Import `flaskDB447.sql` using phpMyAdmin, or from a terminal with the XAMPP client:

```powershell
& "C:\xampp\mysql\bin\mariadb.exe" -u root -p < flaskDB447.sql
```

Use the correct XAMPP path if it is installed somewhere else. The database name created by the dump is `flaskdb447`.

### 2. Create a Python environment

From the repository root:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell blocks activation, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Pipenv can also be used:

```powershell
pip install pipenv
pipenv install
pipenv shell
```

### 3. Configure environment variables

Copy `.env.example` to `.env` and replace the placeholders:

```powershell
Copy-Item .env.example .env
```

At minimum, configure:

```dotenv
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=
DB_NAME=flaskdb447
WEB_SECRET_KEY=generate-a-long-random-secret
KEY_PASSPHRASE=generate-a-long-random-key-passphrase
```

Configure the `MAIL_*` values as well. Gmail requires an app password when two-step verification is enabled. Keep `.env` private and never commit it.

### 4. Run the application

Open two terminals in the repository root, activate `.venv` in both, and run:

Terminal 1, API server:

```powershell
python app.py
```

Terminal 2, web server:

```powershell
python web_app.py
```

Open the web application at:

```text
http://127.0.0.1:5001
```

The API runs at `http://127.0.0.1:5000`.

On first startup, the application creates missing security tables and encrypts legacy plaintext content. It also creates the `.keys` directory and passphrase-protected RSA/ECC key files. Back up `.keys` and keep the same `KEY_PASSPHRASE`; losing either prevents existing encrypted data from being decrypted.

## ECC Key Rotation

An administrator can manually rotate the ECC key from the Administration page. The application retains old key versions, encrypts new values with the active key, and migrates existing encrypted content without requiring a database reset.

## Verification

Compile the Python modules with:

```powershell
python -m py_compile app.py web_app.py rsa.py ecc.py key_management.py
```

This project contains educational cryptographic implementations. Production deployments should use audited cryptographic libraries and a dedicated secret manager.
