# 🛡️ Task: Privacy & Security Hardening

[⬅️ Back](../../README.md) | [🏠 Docs Root](../../../../../README.md)

**Status:** Draft
**Priority:** Medium (P2)
**Type:** Security

## 🎯 Goal

Eliminate potential vulnerabilities and improve user privacy.

## 📝 Task List

### 1. CORS Configuration Check

*   **Problem:** Risk of incorrect `ALLOWED_ORIGINS` setting in prod. If `*` or `localhost` is there, it's a hole.
*   **Solution:**
    *   Check `.env` on server.
    *   Ensure `allow_origin_regex` is disabled in prod.
*   **Action (Verification):**
    1.  SSH to VPS.
    2.  `cat /opt/pinlite/.env | grep ALLOWED_ORIGINS`
    3.  Should be: `ALLOWED_ORIGINS=["https://pinlite.dev"]`

### 2. HTTP Security Headers (CSP)

*   **Problem:** Missing Content-Security-Policy (CSP), making site vulnerable to XSS.
*   **Solution:**
    *   Add to Nginx:
        ```nginx
        add_header Content-Security-Policy "default-src 'self'; img-src 'self' data:; script-src 'self' 'unsafe-inline';" always;
        add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;
        ```

### 3. EXIF Data Stripping

*   **Problem:** Phone photos contain GPS coordinates.
*   **Solution:**
    *   Remove EXIF metadata when saving file (using Pillow).
    *   Keep only Orientation (so photo doesn't rotate).

### 4. Content Moderation (Future)

*   **Problem:** No protection against prohibited content.
*   **Solution:**
    *   Integration with AI moderation services (AWS Rekognition, Google Vision).
    *   Report system.
