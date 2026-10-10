---
name: dlc-selector-service-discipline
description: Разделение read/write логики Django-функций DLC Montage. Использовать при selectors, services, views, формах и cabinet-контексте.
---

# DLC Montage: selectors и services

## Read path

`view -> selector -> prepared data -> template`

Selectors владеют запросами, фильтрами, поиском, статусами, related-object loading и подготовкой данных для страниц. Selector не изменяет базу данных.

## Write path

`view/form/admin action -> service -> models and side effects`

Services владеют созданием и изменением данных, переходами статусов, транзакциями, проверками бизнес-правил, уведомлениями и инвалидацией кэша. Service не рендерит шаблон.

## Views и templates

View парсит запрос, проверяет доступ, вызывает selector или service и возвращает response. Template показывает подготовленные данные; не выполняет запросы и не принимает предметные решения.
