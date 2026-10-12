# INVENTIQ Documentation Hub

Welcome to the comprehensive documentation hub for **INVENTIQ** (Waxis Inventory Management System), developed for **SND Foods International Inc. (Waxi's)**.

---

## 📚 Documentation Index

| Document | Description |
| :--- | :--- |
| **[System Architecture](architecture/system_design.md)** | Comprehensive system design, entity-relationship diagrams, component boundaries, and security models. |
| **[Dual-Mode AI Forecasting](ai_forecasting.md)** | Technical breakdown of the 30-day rolling consumption model and Agrilytics supplier delivery rhythm engine. |
| **[Design System & Ergonomics](design_system.md)** | Brand color tokens (`#871F09`, `#FE5F10`, `#FED216`), WCAG 2.2 AA contrast standards, and touch ergonomics ($\ge$48px). |
| **[Production Deployment](deployment/render_supabase.md)** | Step-by-step instructions for Render Web Service, Supabase PostgreSQL pooler, and automated cron jobs. |
| **[Architecture Decisions (ADRs)](DECISIONS.md)** | Log of critical technical decisions made throughout development (ADR-001 through ADR-012). |
| **[Project State & Rules](PROJECT_STATE.md)** | Source of truth for completed features, active priorities, and "Do Not Redo" architectural invariants. |
| **[Engineering Task Log](TASK_LOG.md)** | Detailed reverse-chronological log of all engineering tasks, code modifications, and test assertions. |
| **[Agent Workflow Guidelines](agents.md)** | Operational guidelines and constraints for autonomous AI coding agents collaborating on this codebase. |

---

## 🏗️ System Overview

INVENTIQ is a high-reliability, zero-external-AI inventory intelligence monolith built on:
* **Backend**: Django 4.2 LTS (Python 3.11+)
* **Database**: PostgreSQL 15+ (Supabase Transaction Pooler, Port 6543) / SQLite for local development
* **Frontend**: Django Templates + HTMX partial swapping + Bootstrap 5 + Chart.js
* **Static Assets**: WhiteNoise with compressed manifest storage
* **Mobile/Tablet**: Progressive Web App (PWA) with service worker offline fallback and standalone app mode
* **Deployment**: Render Web Service + Daily Render Cron Job

---

## 🧭 Navigation Quick Links
* Root README: [`../README.md`](../README.md)
* Application Settings: [`../config/settings.py`](../config/settings.py)
* Production Build Pipeline: [`../build.sh`](../build.sh)
* Render Blueprint: [`../render.yaml`](../render.yaml)
