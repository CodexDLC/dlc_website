---
name: dlc-feature-boundary-decision
description: Определение владельца новой Django-функции DLC Montage. Использовать перед созданием feature, модели, сервиса или cabinet-модуля.
---

# DLC Montage: границы feature

## Базовые владельцы

- `core` — настройки Django, корневые URLs и runtime wiring.
- `system` — глобальные настройки и общие записи, не принадлежащие одной предметной области.
- `cabinet` — shell, auth, общие cabinet-компоненты и shared views.
- `features.staff` — персонал, бригады и их состав.
- `features.projects` — объекты и назначения на объекты.
- `features.work_catalog` — справочник разделов и видов работ.
- `features.reports` — отчёты, строки работ, вложения и проверка отчётов.

## Решение

Создавать отдельную feature, если у неё свои предметные сущности, жизненный цикл, маршруты, selectors, services и тесты. Не складывать такие функции в `system` или `cabinet`.

Наличие страницы в кабинете не означает владение кабинетом: страница отчёта остаётся в `features.reports`, а в cabinet только регистрируется.
