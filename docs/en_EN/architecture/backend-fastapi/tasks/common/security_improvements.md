# 🛡️ Security Improvements Backlog

[⬅️ Back](../../README.md) | [🏠 Docs Root](../../../../../README.md)

Security improvement tasks postponed during MVP phase.

## 1. CloudFlare Integration

*   **Priority:** Medium
*   **Goal:** DDoS protection, hide real IP, acceleration via CDN.
*   **Tasks:**
    *   [ ] Register CloudFlare account.
    *   [ ] Move `pinlite.dev` NS records to CloudFlare.
    *   [ ] Enable "Bot Fight Mode".
    *   [ ] Configure WAF Rules (block countries, suspicious UA).
    *   [ ] Configure "Full (Strict)" SSL mode.

## 2. Advanced Monitoring & Alerting

*   **Priority:** High (post-release)
*   **Goal:** Instant notification of attacks and errors.
*   **Tasks:**
    *   [ ] Integrate **Sentry** for backend error tracking.
    *   [ ] Configure **Prometheus + Grafana** (or lightweight alternative) for server metrics (CPU, RAM, Nginx RPS).
    *   [ ] Write FastAPI Middleware to detect attacks (path scanning) and send alerts to Telegram/Slack.
    *   [ ] Configure Nginx log rotation and analysis (e.g., via GoAccess).

## 3. Container Security

*   **Priority:** Low
*   **Tasks:**
    *   [ ] Run containers as non-root user (already done for backend, check nginx).
    *   [ ] Use `docker scan` or Trivy to find vulnerabilities in images.
