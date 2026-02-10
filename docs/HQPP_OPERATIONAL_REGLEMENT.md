# HQ++ OPERATIONAL REGLEMENT (LOCK)
Проект: **gruzo2_bot**
Версия пакета: **v1.1**
Дата: 2026-02-10

## PURPOSE
Единая дисциплина HQ++: один источник правды, быстрый runtime, архив без хаоса, доказуемое исполнение, управляемый рост через KPI.

**Инварианты:** ZERO-LOSS / ZERO-DISTORTION / NO-GUESS / ONE-CHAIN / ZERO-DUPLICATION.

---

## 1) CANON / RUNTIME / ARCHIVE POLICY (LOCK)
### 1.1 CANON (Source of Truth)
- CANON = единственный действующий документ/состояние, на которое ссылаются решения.
- Любое “что правильно?” решается CANON.
- Изменения CANON: только через CHAIN-ID + PROOF + версия + changelog.

### 1.2 RUNTIME (Operational Slice)
- RUNTIME = укороченная версия для работы/вставки/быстрого запуска.
- RUNTIME НЕ заменяет CANON.
- RUNTIME всегда содержит ссылку/идентификатор версии CANON.

### 1.3 ARCHIVE (Read-only)
- ARCHIVE = предыдущие версии, read-only, только для истории/форензики.
- Запрещено делать решения по ARCHIVE без сверки с CANON.

---

## 2) PROOF POLICY (LOCK)
### 2.1 Правило готовности
- Запрещено писать “готово” без PROOF.
- PROOF = проверяемый артефакт: лог/команда/скрин/файл/CI-run.

### 2.2 ONE-CHAIN карточка (обязательна)
Для каждого CHAIN-ID должны быть:
- ACTION (одно)
- TEST (одно)
- EXPECTED (PASS criteria)
- PROOF (где лежит)
- STATUS (PASS/FAIL)
- NEXT (ровно один следующий CHAIN-ID)

### 2.3 Gate
- PASS только при PASS criteria + наличии PROOF.
- FAIL = факт: причина → 1 минимальный следующий шаг.

---

## 3) WEEKLY KPI RHYTHM (LOCK)
### 3.1 Ритм
- 1 раз в неделю: KPI snapshot + trend + 1 improvement (обязательно ONE-CHAIN).

### 3.2 Минимальный KPI набор
- Deploy Lead Time
- Uptime
- MTTR
- Change Failure Rate
- Automation Rate

### 3.3 Правило улучшения
Каждую неделю:
1) выбираем 1 bottleneck,
2) создаём CHAIN-ID,
3) делаем ACTION/TEST/PROOF,
4) фиксируем влияние на KPI.
