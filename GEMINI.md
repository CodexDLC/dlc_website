# DLC Montage: Project AI Agent Guidelines

This repository uses the Antigravity / AGY Agent System.

## Project Knowledge & Skills
All agents working on this codebase MUST follow the specialized project skills located in .agents/skills/ (and mirrored in docs/agent-skills/):

1. **dlc-project**: General architectural rules, eplacement-only\ mode (no legacy bridges/aliases), CRM vs Public website separation.
2. **dlc-german-terminology**: Strict German PV & electrical construction terminology (Vorarbeiter, Bauleiter, Meister, Ansprechpartner, AC/DC).
3. **dlc-selector-service-discipline**: Architectural separation of pure queries (\selectors.py\) and atomic mutation transactions (\services.py\).
4. **dlc-cabinet-design** & **dlc-design-system**: Brand UI rules, Deep Navy (\#0A2540\), Energy Green (\#00A86B\), 15-minute grids.
5. **dlc-testing-strategy** & **dlc-quality-gate**: Pytest test suite discipline and verification.
6. **dlc-model-schema-change**: Migration and schema integrity rules.
7. **dlc-logging-quality**: Loguru structured logging rules.
8. **dlc-settlement-reporting**: Two-circuit reporting (Abrechnung for Chef vs Abnahme for Emil), Google Sheets live sync, flat material delivery (50 €), piece-work unagreed pricing discipline.
9. **dlc-daily-report-entry**: Strict discrete daily report entry protocol, physical work sequence (cable laying before connection), 15-minute grid, no multi-hour aggregated chunks, per-cable line items.
10. **dlc-background-jobs**, **dlc-deployment-architecture**, **dlc-release-flow**, **dlc-integrations**, etc.

## Core Rules for Agent Actions
- **Language**: German for official UI documents/terms, Russian for team/chat communication when requested.
- **Reporting**: MBG daily reports strictly use 15-minute intervals (\minute % 15 == 0\, \second == 0\).
- **Tests**: Always verify changes by running \pytest\.
