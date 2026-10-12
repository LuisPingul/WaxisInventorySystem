# Security Policy

## 🛡️ Supported Versions

We actively provide security patches and updates for the following versions:

| Version | Supported |
| :--- | :--- |
| `main` branch | :white_check_mark: Yes |
| Production Release (Render) | :white_check_mark: Yes |
| Historical Commits | :x: No |

---

## 🔒 Reporting a Vulnerability

If you discover a security vulnerability in **INVENTIQ**, please report it responsibly.

* **Do NOT open a public GitHub Issue** to disclose security vulnerabilities.
* Contact the system administrators or lead maintainer privately.
* Please provide:
  * A clear description of the vulnerability.
  * Steps or proof-of-concept script to reproduce the issue.
  * Potential impact assessment.
* We acknowledge reports within 48 hours and work toward a coordinated patch and release.

---

## 🔑 Secret & Credential Management Best Practices

1. **Never Commit Secrets**:
   * Never commit `.env` files, production database passwords, Django secret keys, or API tokens to git.
   * Verify `.gitignore` contains `.env`, `db.sqlite3`, and local cache directories.
2. **Production Settings**:
   * Ensure `DJANGO_DEBUG=0` in production environments.
   * Enforce `SESSION_COOKIE_SECURE=True` and `CSRF_COOKIE_SECURE=True` when serving over HTTPS.
   * Whitelist trusted domains explicitly in `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`.
3. **Database Security**:
   * Always connect to remote databases (e.g., Supabase PostgreSQL) via SSL (`sslmode=require`).
