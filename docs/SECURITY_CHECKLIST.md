# SECURITY_CHECKLIST.md (LOCK)
Проект: **gruzo2_bot**
Дата: 2026-02-10

## 1) Secrets (must-have)
- [ ] `.env` НЕ в git (проверка `.gitignore`)
- [ ] Секреты НЕ печатаются в логах (нет debug print токенов/ENV)
- [ ] Серверный `.env` защищён:
  - `chmod 600 /opt/gruzo2_bot/.env`
  - владелец = сервис-пользователь
- [ ] Ротация токена (BotFather) описана и понятна команде:
  - При подозрении на утечку → сразу rotate token → обновить `.env` → restart service

## 2) Repo scanning (CI)
- [ ] Secret scan в CI включён (gitleaks/trufflehog)
- [ ] Merge запрещён без зелёного CI (branch protection)

## 3) SSH/Server baseline
- [ ] Отдельный user для сервиса (не root)
- [ ] Только SSH key auth (по возможности отключить password auth)
- [ ] Firewall baseline: разрешить 22/tcp (по IP), остальное закрыть
- [ ] Логи аутентификации мониторятся (опционально fail2ban)

## 4) Incident minimal playbook
1) Обнаружили утечку → rotate token
2) Проверили git history / CI alerts
3) Перевыпустили `.env` на сервере
4) `systemctl restart gruzo2_bot`
5) Добавили proof в `ops/proof/PROOF_SECURITY_INCIDENT.txt`
