# DOC_DoD_DEPLOY.md (LOCK)
Проект: **gruzo2_bot**
Цель: **Production Deploy PASS** (systemd baseline)
Дата: 2026-02-10

## 0) Definition of Done (DoD) — Deploy PASS
Deploy считается **PASS**, только если выполнены ВСЕ пункты:

### A) Service lifecycle (systemd)
- [ ] Unit файл установлен: `ops/systemd/gruzo2_bot.service`
- [ ] Service enabled: `systemctl enable gruzo2_bot`
- [ ] Service active: `systemctl is-active gruzo2_bot` → `active`
- [ ] Restart policy работает: при kill процесса сервис поднимается сам
- [ ] Reboot-survive: после `reboot` сервис сам стартует

### B) Health & Functionality (Telegram flows)
- [ ] `/start` PASS на сервере
- [ ] User flow PASS (создание заявки)
- [ ] Admin flow PASS (кнопки/действия)

### C) Logs & Observability baseline
- [ ] Логи доступны: `journalctl -u gruzo2_bot -f`
- [ ] Логи ограничены/ротируются (journald limits / logrotate)
- [ ] Healthcheck установлен и даёт PASS:
  - `bash ops/healthcheck.sh` → exit code 0
- [ ] Есть минимальный сигнал FAIL (лог/уведомление/N8N — опционально)

### D) Security baseline
- [ ] Секреты НЕ в git: `.env` в `.gitignore`, gitleaks/secret scan PASS
- [ ] Секреты НЕ в логах (нет print токена/ENV)
- [ ] `.env` на сервере защищён: права `chmod 600`, владелец сервис-юзер
- [ ] Процедура ротации токена описана (см. `docs/SECURITY_CHECKLIST.md`)

### E) Proof (обязательный)
- [ ] Создан файл `ops/proof/PROOF_DEPLOY_BASELINE.txt` с командами и выводом:
  - systemctl status / enable
  - journalctl tail
  - healthcheck output + exit code
  - reboot proof (время + status)
- [ ] Заполнен CHAIN лог (см. `CHAIN_LOG.md`)

---

## 1) Быстрый baseline-план (systemd)
### 1.1 Серверные предпосылки (Ubuntu)
```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git
```

### 1.2 Пользователь и директории
Рекомендуется отдельный пользователь:
```bash
sudo adduser --disabled-password --gecos "" gruzo
sudo mkdir -p /opt/gruzo2_bot
sudo chown -R gruzo:gruzo /opt/gruzo2_bot
```

### 1.3 Деплой кода
```bash
sudo -u gruzo bash -lc 'cd /opt/gruzo2_bot && git clone <REPO_URL> .'
sudo -u gruzo bash -lc 'cd /opt/gruzo2_bot && python3 -m venv .venv && . .venv/bin/activate && pip install -U pip && pip install -r requirements.txt'
```

### 1.4 ENV
Создать `/opt/gruzo2_bot/.env` (НЕ коммитить) и защитить:
```bash
sudo -u gruzo bash -lc 'cd /opt/gruzo2_bot && nano .env'
sudo chmod 600 /opt/gruzo2_bot/.env
sudo chown gruzo:gruzo /opt/gruzo2_bot/.env
```

### 1.5 systemd unit
Скопировать unit:
```bash
sudo cp ops/systemd/gruzo2_bot.service /etc/systemd/system/gruzo2_bot.service
sudo systemctl daemon-reload
sudo systemctl enable --now gruzo2_bot
sudo systemctl status gruzo2_bot --no-pager
```

### 1.6 Proof
Заполни `ops/proof/PROOF_DEPLOY_BASELINE.txt` по шаблону, затем прогон DoD.

---

## 2) PASS/FAIL Gate
- **PASS**: все чекбоксы DoD закрыты, proof есть.
- **FAIL**: фиксируем 1 причину → 1 исправление → 1 повторный тест (ONE CHAIN).

