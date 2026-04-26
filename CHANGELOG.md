# Changelog — tw-stock-signal

所有版本演化、重要調整、與時間戳記。

---

## [v0.1] — 2026-04-26（MVP階段）

### 完成時間
2026-04-26

### 策略內容
- MA5 / MA10 均線交叉
- RSI(14) Wilder's RSI
- 訊號：LONG / NEUTRAL / SHORT
- 警示：OVERBOUGHT / OVERSOLD

### 支援標的
2330.TW、2890.TW、00919.TW、2881.TW、0052.TW、0050.TW、009816.TW、2317.TW

### 測試結果
- 單元測試：8/8 通過

### Commit History
- `2a7e45d` — feat: v0.1 MVP - 均線動能策略MA5/MA10/RSI14單元驗證通過

---

## [v0.2] — 2026-04-26（策略升級階段）

### 完成時間
2026-04-26

### 策略內容（v2 升級）
- 新增 MACD（過濾器）
- 新增 布林帶（過濾器）
- 新增 KD 指標（僅個股）
- ETF 使用 MA10 > MA20（個股使用 MA5 > MA10）
- 停損/停利：固定 20%
- 持股方式：過夜

### 訊號邏輯
- LONG/SHORT：核心指標（MA+RSI+KD）全滿足 + 過濾器不通過否決
- NEUTRAL：核心未全數滿足，或被過濾器否決

### 文件產出
- SPEC.md v2.0（策略規格書）
- implementation-plan.md（實作規劃書）
- test-plan.md v2.0（測試計畫書）
- deployment-plan.md（部署計畫書）
- user-stories.json（24則 User Stories）
- ralph-loop-tracker.md（追蹤系統）

### Commit History
- `77f5c9b` — feat: 升級均線動能策略至 v2
- `1755d75` — docs: add implementation-plan.md
- `d68bcb9` — docs: add deployment plan v1.0
- `deb2587` — docs: add test-plan.md v2.0
- `9032d32` — chore: Add user stories
- `db9e18b` — feat(monitor): 建立 Ralph-Loop 追蹤系統

---

## [v0.2.1] — 2026-04-26（Sprint 1 完成）

### 完成時間
2026-04-26

### Sprint 1 完成項目
- Ralph-Loop 追蹤系統建立
- KD 測試修復（形狀 mismatch bug）
- 24/24 單元測試全部通過
- 12則 User Stories 實作完成

### 測試結果
- test_backtest.py：2/2 通過
- test_indicators.py：13/13 通過
- test_signal_generator.py：9/9 通過
- **總計：24/24 通過**

### Commit History
- `11bbb19` — fix: resolve KD test shape mismatch
- `571cb33` — docs(monitor): update Ralph-Loop tracker
- `cde3d28` — feat: 均線動能策略 v2 完整實作

---

## [v0.3] — 2026-04-26（Sprint 2 規劃中）

### Sprint 2 目標
- Phase 2：回測驗收（PF>1.25 / MaxDD<20% / WinRate>45%）
- Phase 3：樣本外測試（OOS）
- mypy --strict 型別檢查全通過
- Phase 4：壓力測試（48h / 記憶體 / HTTP 429）

### Commit History
（Sprint 2 完成後填入）

---

## Commit 訊息格式規範

```
[類型] 簡短描述

Types:
- feat: 新功能
- fix: 錯誤修復
- docs: 文件更新
- chore: 维护性工作
- test: 测试相关
- refactor: 重构
```

---
*最後更新：2026-04-26*
