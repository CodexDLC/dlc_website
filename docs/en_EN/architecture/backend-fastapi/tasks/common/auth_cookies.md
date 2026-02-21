# 🍪 Task: Secure Auth Storage (HttpOnly Cookies)

[⬅️ Back](../../README.md) | [🏠 Docs Root](../../../../../README.md)

**Status:** 📋 Backlog
**Priority:** High
**Related Tech Debt:** Auth Storage (localStorage)

## 📝 Problem Description

In MVP version, tokens (Access and Refresh) are stored on frontend in `localStorage`.
This makes them vulnerable to XSS (Cross-Site Scripting) attacks. If an attacker can execute JS code on the page, they can steal tokens.

## 🎯 Goal

Move token storage to secure `HttpOnly` Cookies.

## 📋 Implementation Plan

1.  **Backend:**
    *   Change `/login` and `/refresh` endpoints. Instead of returning tokens in JSON body, set them via `response.set_cookie(...)`.
    *   Cookie parameters: `httponly=True`, `secure=True` (for HTTPS), `samesite='Lax'` or `'Strict'`.
    *   Change `/logout` endpoint: delete cookies (`response.delete_cookie`).

2.  **Frontend (Note):**
    *   This task concerns only server side (setting headers). Client implementation (browser reading cookies) happens automatically.
