## Summary
<!-- Provide a brief description of the motivation and changes included in this pull request. -->

## Type of Change
- [ ] 🐛 Bug fix (non-breaking change which fixes an issue)
- [ ] ✨ New feature (non-breaking change which adds functionality)
- [ ] ⚡ Performance / Ergonomics improvement
- [ ] 🎨 UI / Design System update
- [ ] 📝 Documentation update
- [ ] 🔧 Build / CI / Deployment configuration

## Module Affected
- [ ] Accounts / Authentication
- [ ] Dashboard (Owner / Manager / Crew)
- [ ] Inventory / Stock Deduction
- [ ] Forecasting & Agrilytics Radar
- [ ] Procurement & PR Email / Viber
- [ ] Reports & Analytics
- [ ] PWA & Offline Engine
- [ ] Documentation / Tooling

## Pre-Merge Quality Checklist
- [ ] `python manage.py check` passes with 0 issues.
- [ ] `python manage.py makemigrations --check --dry-run` confirms no ungenerated migrations.
- [ ] `python manage.py test` passes.
- [ ] WhiteNoise static assets compiled cleanly (`python manage.py collectstatic --no-input`).
- [ ] UI changes comply with Waxi's Design System (`#871F09`, `#FE5F10`, `#FED216`) and WCAG 2.2 AA contrast.
- [ ] Documentation updated in `docs/TASK_LOG.md` and relevant guides.
