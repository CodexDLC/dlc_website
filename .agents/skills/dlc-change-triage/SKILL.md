---
name: dlc-change-triage
description: Классификация Django-изменений DLC Montage перед редактированием: кабинет, feature, модель, сервис, публичный сайт или статика.
---

# DLC Montage: triage изменений

Перед правкой определить поверхность и тип изменения.

## Поверхности

- **Cabinet:** пространства AC, DC, Staff, Administration, их навигация и рабочие экраны.
- **Feature:** модели, формы, selectors, services и маршруты предметной области.
- **Admin:** Django Admin/Unfold для администраторов.
- **Public:** будущий сайт и клиентское пространство.
- **Assets:** отдельные cabinet- или public CSS/JS bundles.
- **Workers/integrations:** фоновые задачи, Redis, Telegram и внешние сервисы.
- **Deployment:** Dockerfile каждого runtime, Compose-слои, CI/CD и production rollout; правила задаёт `dlc-deployment-architecture`.

## Типы изменений

- шаблон; selector/read context; модель/миграция; service/write workflow; навигация; assets; граница feature.

Шаблон не считается самостоятельным решением, если для него не хватает модели, selector или service. Перед изменением кратко назвать поверхность, тип и owning feature.
