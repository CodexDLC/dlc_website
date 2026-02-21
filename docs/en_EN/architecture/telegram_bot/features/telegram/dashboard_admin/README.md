# 📂 Dashboard Admin Feature

[⬅️ Back](../README.md) | [🏠 Docs Root](../../../../../../README.md)

## 📝 Overview
The `dashboard_admin` feature provides an administrative interface for managing the bot and viewing system statistics.

## ⚙️ Feature Setting (`feature_setting.py`)
- **States:** `DashboardAdminStates`
- **Garbage Collect:** `True`
- **Menu Config:**
    - **Key:** `dashboard_admin`
    - **Text:** `🔐 Admin Panel`
    - **Icon:** `🔐`
    - **Priority:** 10
    - **Is Admin:** `True`

## 📁 Structure
- **[Handlers](./handlers.md)**: Entry points and callback processing.
- **[Logic & Orchestrator](./logic.md)**: Business logic and coordination.
- **[UI](./ui.md)**: Message rendering and keyboards.
- **[Contracts](./contracts.md)**: Data access interfaces.
- **[Resources](./resources.md)**: Static texts and constants.
