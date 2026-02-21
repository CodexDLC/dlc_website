# 💡 Feature: Headless / Microservice Mode

[⬅️ Back](../../README.md) | [🏠 Docs Root](../../../../../README.md)

**Status:** 💡 Idea / Backlog
**Priority:** Low (Architectural)
**Phase:** Future (v2.0)

## 📝 Description

Implementation of "API only" (Headless) server mode for use as an image storage microservice for third-party applications (Mobile Apps, Other Sites).

## 🎯 Goal

Allow using PinLite as an S3/Cloudinary replacement for custom projects.

## 📋 Concept

### 1. Operation Modes (Config)

Add `APP_MODE` variable to `.env`:

*   `FULL` (Default): Current mode. Frontend, Users, Registration.
*   `HEADLESS`: Only API for upload and serving.

### 2. Changes in Headless Mode

*   **Frontend:** Disabled (static not served).
*   **Auth:**
    *   User registration disabled.
    *   Instead of JWT (User Token), use **API Key** (Service Token) defined in `.env`.
    *   Example header: `X-API-Key: my-secret-service-key`.
*   **Storage:**
    *   All files linked to a single "System User" or stored without user binding.

### 3. Use Cases

1.  Backend for mobile app.
2.  CDN for online store.
3.  Personal screenshot storage (ShareX custom uploader).
