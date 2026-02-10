# ops/logging.md (LOCK) — OPS Observability Baseline
Цель: единый стандарт логов, ограничений и диагностики для **gruzo2_bot**.

## 1) Просмотр логов (systemd/journald)
Следить за логами:
```bash
journalctl -u gruzo2_bot -f
```

Последние 200 строк:
```bash
journalctl -u gruzo2_bot -n 200 --no-pager
```

Ошибки:
```bash
journalctl -u gruzo2_bot -p err -n 200 --no-pager
```

## 2) Ограничение размера journald (рекомендовано)
Проверь текущие настройки:
```bash
journalctl --disk-usage
```

Пример минимального лимита (вручную):
- Файл: `/etc/systemd/journald.conf`
- Параметры (пример):
  - `SystemMaxUse=200M`
  - `SystemMaxFileSize=20M`
  - `MaxRetentionSec=7day`

После изменений:
```bash
sudo systemctl restart systemd-journald
```

## 3) Restart discipline (anti-loop)
Проверить unit:
- Restart=always
- RestartSec=5
- StartLimitIntervalSec=300
- StartLimitBurst=5

## 4) Healthcheck
Единый healthcheck:
```bash
bash ops/healthcheck.sh
echo $?
```
Exit code:
- 0 = PASS
- !=0 = FAIL

## 5) Минимальный alert
Базовая версия: при FAIL пишем в лог (journal) + (опционально) триггерим N8N.
