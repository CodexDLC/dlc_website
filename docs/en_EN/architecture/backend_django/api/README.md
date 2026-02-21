# 🔌 API

[⬅️ Back](../README.md) | [🏠 Docs Root](../../../../README.md)

The `api` module handles the REST API for the application using **Django Ninja**.

## 📋 Overview

Django Ninja provides a fast, type-safe way to build APIs using standard Python type hints.

## 🗺️ Module Map

| Component | Description |
|:---|:---|
| **[instance.py](./instance.py)** | The main `NinjaAPI` instance configuration. |
| **[urls.py](./urls.py)** | API routing. |

## 🛠️ Key Features

- **Automatic Docs:** Swagger/OpenAPI documentation generated automatically.
- **Type Safety:** Pydantic models for request/response validation.
- **Async Support:** Native support for async views.
