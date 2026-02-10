# CHANGELOG_EXECUTION_PACK.md
Пакет: **gruzo2_bot_production_guardrails_pack_v1.1**
Дата: 2026-02-10

## v1.1 (current)
### Added
- `ops/proof/PROOF_PACKAGING_EP-001_NOTE.md` — пометка, что EP-001 proof исторический (v1.0).
- `docs/HQPP_OPERATIONAL_REGLEMENT.md` — политика CANON/RUNTIME/ARCHIVE + Proof policy + Weekly KPI rhythm (LOCK).
- `docs/INTEGRATION_QUICKCHECK.md` — быстрый тест интеграции пакета в корень репо + exec-bit.
- `ops/proof/PROOF_DEPLOY_BASELINE.txt` — шаблон доказательств деплоя по DoD.
- `ops/proof/PROOF_EP-002_INTEGRATE.txt` — шаблон доказательств интеграции пакета в репо.
- `PACK_MANIFEST_SHA256.txt` — манифест sha256 всех файлов пакета.
- `ops/proof/PROOF_PACKAGING_EP-003.txt` — proof упаковки версии v1.1.

### Changed
- `.github/workflows/ci.yml`:
  - добавлены `permissions`, `concurrency`, `timeout-minutes`, `pip cache`.

### Unchanged (core)
- DoD / Chain template / Security checklist / KPI pack / Observability docs / systemd unit.

## v1.0 (baseline)
- Первичная упаковка EP-001.
