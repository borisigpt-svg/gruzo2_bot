# INTEGRATION_QUICKCHECK.md (LOCK)
Цель: за 60 секунд понять: “Execution Pack реально интегрирован в репо или лежит рядом”.

## PASS-критерий (в корне репозитория, где `.git`)
Должны существовать пути:
- `.github/workflows/ci.yml`
- `ops/healthcheck.sh`
- `docs/DOC_DoD_DEPLOY.md`

Если эти файлы находятся внутри папки пакета (например `.../execution_pack/...`) — интеграции в репо ещё НЕТ.

## Exec-bit (для Linux)
Проверка в Git индексе:
```bash
git ls-files -s ops/healthcheck.sh
```
PASS: режим `100755`.

На Windows выставить exec-bit:
```bash
git update-index --chmod=+x ops/healthcheck.sh
```

## CI sanity
После push/PR workflow `CI` должен запуститься и быть зелёным.
