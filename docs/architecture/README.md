---
title: GenXSOP Architecture Documentation
---

# GenXSOP Architecture

This folder contains the architecture documentation for **GenXSOP**.

## Quick links

1. **System Context (C4 L1)** — [`system-context.md`](system-context.md)
2. **Containers (C4 L2)** — [`container.md`](container.md)
3. **Backend Architecture** — [`backend.md`](backend.md)
4. **Frontend Architecture** — [`frontend.md`](frontend.md)
5. **Data Model** — [`data-model.md`](data-model.md)
6. **Runtime & Deployment** — [`runtime-deployment.md`](runtime-deployment.md)
7. **Cross-cutting Concerns** — [`cross-cutting.md`](cross-cutting.md)
8. **Key Decisions** — [`decisions.md`](decisions.md)
9. **Components (C4 L3) — Forecasting** — [`components-forecasting.md`](components-forecasting.md)

## Scope

These documents describe:

- The **static structure** of the solution (layers/modules)
- Key **runtime flows** (auth, CRUD, forecasting)
- **Interfaces/contracts** between frontend ↔ backend ↔ database
- Cross-cutting concerns like **security**, **errors**, **testing**, and **audit logging**

## Conventions

- Diagrams are written in **Mermaid** so they render directly in GitHub.
- Backend terminology:
  - **Router** = HTTP layer / thin controller (`backend/app/routers/*`)
  - **Service** = business logic (`backend/app/services/*`)
  - **Repository** = data access (`backend/app/repositories/*`)
  - **Model** = SQLAlchemy ORM (`backend/app/models/*`)
  - **Schema** = Pydantic DTO (`backend/app/schemas/*`)
