# 🗺️ Backend Roadmap: PinLite Template

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../README.md)

Development strategy for the server side. The project is divided into a **Common Base** and two development branches.

## 🚨 Phase 0: Audit & Preparation (Current Focus)

Priority tasks before starting active development.

*   [ ] **[Project Structure Audit](./tasks/audit/project_structure_audit.md)** — Review `src/backend-fastapi`, `deploy/Fast_api`, `deploy/nginx`. Prepare for `init_repo`.

## 🧱 Common Base (Foundation)

Tasks required for any development branch (Security, Infrastructure).

### Security & Users

*   [ ] **[Refactor User Creation Flags](./tasks/common/user_flags.md)** — Flexible user creation (Admin/User) for init scripts.
*   [ ] **[Privacy & Security Hardening](./tasks/common/privacy_security.md)** — EXIF stripping, CORS, Security Headers.
*   [ ] **[Secure Auth Storage (Backend Only)](./tasks/common/auth_cookies.md)** — Implement `Set-Cookie: HttpOnly` on backend.
*   [ ] **[Security Improvements](./tasks/common/security_improvements.md)** — DDoS protection (Cloudflare), Monitoring.

### Process

*   [x] **[Git Flow](./git_flow.md)** — Branching standards.

---

## 🔀 Development Branches

### 🅰️ Branch 1: "Universal Backend" (Full Platform)

Development as a full-fledged backend for a site with users and social features.
*Goal: Template for social network, blog, or marketplace.*

*   [ ] **[Social Mechanics](./tasks/universal/social_features.md)** — Likes, comments, feed. (Must Have for this branch).

### 🅱️ Branch 2: "SAS / Microservice" (Headless Storage)

Development as an isolated image storage service (S3 Replacement).
*Goal: Personal S3 for other projects.*

*   [ ] **[Headless Mode](./tasks/sas/headless_mode.md)** — API Key operation, registration disabled, "Service Only" mode.
