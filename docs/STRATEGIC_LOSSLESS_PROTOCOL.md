# STRATEGIC_LOSSLESS_PROTOCOL.md (LOCK)
Цель: нулевая потеря смысла, нулевая потеря доказательств, нулевая самодеятельность.

## Инварианты
- NO-GUESS: “готово” только с Proof
- ONE CHAIN: 1 действие + 1 тест + 1 proof
- ZERO-DUPLICATION: один канон, все остальное архив
- FAIL = факт: фиксируем причину и минимальный следующий шаг

## Canon discipline
- CANON PROMPT = v1.2 Full (ONE PIECE + Appendix + Execution Pack)
- Любые изменения: через CHAIN-ID + changelog

## Proof pack
Каждый релиз/деплой сопровождается:
- PROOF_DEPLOY_BASELINE.txt
- CI logs (link/path)
- Security scan result
