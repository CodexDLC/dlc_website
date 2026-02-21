# 🧭 Documentation Standard

> **AUTHORITY:** This document defines how documentation is written, structured, and maintained in this project.

---

## 1. 📜 Core Philosophy

We maintain documentation in **two languages** to ensure international accessibility while keeping the local community engaged.

### 🇬🇧 English (Primary / Source of Truth)

- **Mandatory for:** All Pull Requests and technical specifications.
- **Location:** `docs/en_EN/` (mirrors folder structure).
- **Content:**
  - Full technical specifications
  - Data schemas and contracts
  - API documentation
  - Code examples
- **Goal:** Single source of truth. If code contradicts EN docs, it is a bug.

### 🇷🇺 Russian (Secondary / Conceptual Hub)

- **Optional for Contributors:** If you don't speak Russian, just write EN docs. Maintainers will add RU translation.
- **Location:** `docs/ru_RU/` (mirrors folder structure).
- **Content:**
  - Conceptual translation (the "why" and "how")
  - Links to EN version for code/schemas instead of duplication
  - Architect's mental model explanations
- **Goal:** Help Russian-speaking developers understand system design decisions.

---

## 2. ☯️ Twin Realms Principle

Documentation languages serve different purposes:

### 🇬🇧 EN = Technical Truth

- **For:** AI generators, external libraries, standards compliance
- **Format:** Granular (1 class = 1 file)
- **Contains:**
  - Contracts (`interfaces`)
  - DTO Schemas (JSON/TypeScript)
  - Mermaid Diagrams (Sequence, Class, ER)
  - API specifications

### 🇷🇺 RU = Architect's Mind

- **For:** Human developers, system understanding
- **Format:** Aggregated (1 folder = 1 README)
- **Contains:**
  - **The Why:** Why this solution was chosen
  - **The Flow:** How data flows through the system (simplified)
  - **Links:** References to EN files for technical details

---

## 3. 🗂️ Structure Mirroring Rule

Documentation structure **MUST** mirror code structure.

### Mapping Example

| Code Location | Documentation Location |
|:---|:---|
| `src/backend/features/portfolio/` | `docs/en_EN/architecture/backend/features/portfolio/` |
| `src/bot/handlers/commands/` | `docs/en_EN/architecture/bot/handlers/commands/` |
| `src/frontend/components/` | `docs/en_EN/architecture/frontend/components/` |

### Why?

- **1:1 Mapping:** Easy to find docs for any code module
- **No Orphans:** Prevents documentation from getting lost
- **Refactoring Safety:** When code moves, docs move with it

---

## 4. 🧭 Navigation Standard

Every documentation file must be easily navigable.

### Breadcrumbs (Mandatory)

Every file **MUST** start with a navigation header:

```markdown
[⬅️ Back](../README.md) | [🏠 Docs Root](../../README.md)
```

- **Back:** Links to the current directory's `README.md`
- **Docs Root:** Links to the documentation root (`docs/README.md`)

### Breadcrumb Examples

**File:** `docs/en_EN/architecture/backend/features/portfolio/data_schema.md`

❌ **BAD:**

```markdown
[Back](../) | [Home](/)
```

✅ **GOOD:**

```markdown
[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../README.md)
```

### Index Files (README.md)

Every directory **MUST** have a `README.md` acting as a navigation hub.

**Required Structure:**

1. **Header:** Emoji 📂 + Section Name
2. **Navigation:** Breadcrumbs
3. **Description:** Short summary (2-3 sentences)
4. **Map:** Table or list of files in **logical reading order** (not alphabetical)

**Index Template:**

```markdown
# 📂 [Section Name]

[⬅️ Back](../README.md) | [🏠 Docs Root](../../README.md)

Brief description of what this section contains.

## 🗺️ Module Map

| Component | Description |
|:---|:---|
| **[📄 Overview](./overview.md)** | High-level introduction |
| **[📄 Data Schema](./data_schema.md)** | Database models and DTOs |
| **[📄 API Contract](./api_contract.md)** | Endpoints and request/response formats |
```

---

## 5. 📝 File Naming & Organization

### Naming Conventions

- **Format:** `snake_case.md` (e.g., `service_layer.md`, `data_schema.md`)
- **No Prefixes:** Do NOT use `01_`, `02_` prefixes in filenames
- **Reading Order:** Defined in `README.md` map, not by filename

### Language Folders

All documents **MUST** reside in:

- `docs/en_EN/` for English
- `docs/ru_RU/` for Russian

**Never** create language-neutral folders like `docs/shared/`.

---

## 6. ✅ Markdown Linting Rules

This project enforces **strict markdown standards** to maintain consistency.

### Required Rules

1. **MD047 (End with Newline):**
   - Every file must end with exactly **one newline** character (`\n`)
   - ❌ BAD: `...end of text.` (EOF)
   - ✅ GOOD: `...end of text.\n` (EOF)

2. **MD032 (List Spacing):**
   - Insert a **blank line** before and after any list
   - ❌ BAD:
     ```markdown
     Text
     * Item 1
     ```
   - ✅ GOOD:
     ```markdown
     Text

     * Item 1

     Next text
     ```

3. **MD007 (Indentation):**
   - Use **2 spaces** for nested lists (not 4 spaces or tabs)
   - ❌ BAD: `    * Nested item` (4 spaces)
   - ✅ GOOD: `  * Nested item` (2 spaces)

### Validation

Run linter before committing:

```bash
python scripts/lint_docs.py
```

See: [MARKDOWN_STANDARDS.md](./MARKDOWN_STANDARDS.md) for full technical specification.

---

## 7. 🚫 Common Mistakes

### ❌ Mistake 1: Numbered Prefixes

```
docs/
├── 01_introduction.md
├── 02_setup.md
└── 03_usage.md
```

**Why bad:** Breaks when files are reordered or inserted.

**Fix:** Use `README.md` map to define reading order.

### ❌ Mistake 2: Duplicating Code in RU Docs

```markdown
# RU: Схема базы данных

class User(Base):
    id = Column(Integer, primary_key=True)
    ...
```

**Why bad:** Doubles maintenance burden, creates sync issues.

**Fix:** Link to EN version:

```markdown
# RU: Схема базы данных

Смотри [EN Schema](../../en_EN/architecture/backend/data_schema.md#user-model).
```

### ❌ Mistake 3: Missing Breadcrumbs

```markdown
# My Feature

Content here...
```

**Why bad:** No way to navigate back.

**Fix:** Add navigation header:

```markdown
# My Feature

[⬅️ Back](./README.md) | [🏠 Docs Root](../../README.md)

Content here...
```

### ❌ Mistake 4: Dumping Files in Root

```
docs/en_EN/architecture/backend/
├── portfolio_service.md
├── auth_service.md
└── payment_service.md
```

**Why bad:** Violates structure mirroring rule.

**Fix:** Mirror code structure:

```
docs/en_EN/architecture/backend/
├── features/
│   ├── portfolio/
│   │   └── service.md
│   ├── auth/
│   │   └── service.md
│   └── payment/
│       └── service.md
```

---

## 8. 📋 Contributor Checklist

Before submitting documentation:

- [ ] **Language:** Documentation written in English (`docs/en_EN/`)
- [ ] **Breadcrumbs:** Navigation header added to file
- [ ] **Index:** File linked in parent folder's `README.md`
- [ ] **Structure:** Folder structure mirrors code location
- [ ] **Linting:** `python scripts/lint_docs.py` passes
- [ ] **Links:** All relative links tested and working
- [ ] **Newline:** File ends with single newline (MD047)
- [ ] **Lists:** Blank lines before/after lists (MD032)

---

## 9. 🔗 Related Standards

- **[Project Ideology](./PROJECT_IDEOLOGY.md)** - Root directory philosophy and isolation rules
- **[Markdown Standards](./MARKDOWN_STANDARDS.md)** - Technical linting specification
- **[Global Documentation Standard](./GLOBAL_DOCUMENTATION_STANDARD.md)** - AI architect instructions

---

**Last Updated:** 2025-02-07
