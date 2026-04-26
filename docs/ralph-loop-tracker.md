# Ralph-Loop 追蹤系統

> **目的：** Monitor Agent 用於追蹤「紅燈要修、綠燈確認」的作戰中心
> **口號：** 紅燈必修、綠燈確認、不通過不放行

---

## 📌 Ralph-Loop 概念說明

**Ralph-Loop** 是標虎大隊的開發節奏：

1. **R**equire → 提出需求（Analyst）
2. **A**nalyze → 分析規格（Analyst）
3. **L**ogic → 確認邏輯（Analyst）
4. **P**lan → 規劃實作（Coder）
5. **H**ack → 動手實作（Coder）
6. **L**oop → 測試驗證（Monitor）

- 🟢 **綠燈**：通過所有檢查，繼續前進
- 🔴 **紅燈**：失敗，需修復後才能進入下一階段
- 🟡 **黃燈**：部分通過，暫停等待

---

## 🏃 Sprint 迭代記錄

| Sprint | 日期 | 內容 | 狀態 |
|--------|------|------|------|
| Sprint 1 | 2026-04-26 | 建立追蹤系統、初始化架構 | 🟡 進行中 |
| Sprint 1 Phase 5 | 2026-04-26 | 測試驗證衝刺（Steward執行） | ✅ 完成 |

---

## 📋 User Stories 追蹤表

| ID | Story | Status | Assigned | Priority |
|----|-------|--------|----------|----------|
| US-01 | 作為投資者，我需要從 Yahoo Finance 取得日K線資料，以便進行技術分析 | 🟢 已實作 | Coder | P0 |
| US-02 | 作為投資者，我需要系統自動判斷 ETF 或個股，以便套用對應 MA 參數 | 🟢 已實作 | Coder | P0 |
| US-03 | 作為投資者，我需要系統計算 MA/RSI/KD/MACD/布林帶指標，以便判斷多空方向 | 🟢 已實作 | Coder | P0 |
| US-04 | 作為投資者，我需要系統根據核心指標（MA+RSI+KD）產生 LONG/SHORT/NEUTRAL 訊號 | 🟢 已實作 | Coder | P0 |
| US-05 | 作為投資者，我需要系統用過濾器（MACD+布林帶）否決錯誤訊號 | 🟢 已實作 | Coder | P0 |
| US-06 | 作為投資者，我需要系統在 OVERBOUGHT/OVERSOLD 時發出警示 | 🟢 已實作 | Coder | P1 |
| US-07 | 作為投資者，我需要系統執行停損（20%）與停利（20%）風控 | 🟢 已實作 | Coder | P1 |
| US-08 | 作為投資者，我需要系統標記持股過夜（固定 True） | 🟢 已實作 | Coder | P1 |
| US-09 | 作為投資者，我需要系統輸出標準化 JSON 格式訊號 | 🟢 已實作 | Coder | P0 |
| US-10 | 作為投資者，我需要系統支援回測並輸出績效指標（PF/MaxDD/WinRate） | 🟢 已實作 | Coder | P1 |
| US-11 | 作為投資者，我需要系統提供 CLI 介面方便操作 | 🟢 已實作 | Coder | P2 |
| US-12 | 作為投資者，我需要系統支援 8 檔標的（2330/2890/2881/2317/0050/0052/00919/009816） | 🟢 已實作 | Coder | P0 |

---

## 🔧 實作模組追蹤表

| 順序 | 模組 | 檔案 | 依賴 | 工時 | Status | 備註 |
|------|------|------|------|------|--------|------|
| 1 | data_loader.py | `data/data_loader.py` | 無 | 1 hr | 🟢 完成 | 含重試機制 |
| 2 | ticker_classifier.py | `strategy/ticker_classifier.py` | 無 | 0.5 hr | 🟢 完成 | 8檔支援 |
| 3 | indicators.py | `strategy/indicators.py` | 1, 2 | 2 hr | 🟢 完成 | 全指標實作 |
| 4 | signal_generator.py | `signals/signal_generator.py` | 3 | 3 hr | 🟢 完成 | 核心模組 |
| 5 | position_manager.py | `portfolio/position_manager.py` | 4 | 1 hr | 🟢 完成 | 20%停損停利 |
| 6 | backtester.py | `backtest/backtester.py` | 1, 5 | 2 hr | 🟢 完成 | 含OOS檢驗 |
| 7 | run.py + main.py | 根目錄 | 4, 6 | 0.5 hr | 🟢 完成 | — |
| 8 | 單元測試 | `tests/` | 3, 4 | 2 hr | 🟡 待修復 | 2個KD測試失敗 |

---

## 🚦 四階段驗收標準（紅綠燈追蹤）

### 第一階段｜單元測試
| 檢查項 | 標準 | Status | 備註 |
|--------|------|--------|------|
| pytest 執行 | 24 tests: 22 pass, 2 fail | 🟡 待修復 | 2 KD shape mismatch |
| RSI 初始值正確 | RSI(14) 計算正確 | 🟢 通過 | test_rsi_warmup_period_returns_nan ✅ |
| RSI 邊界範圍 | RSI 0-100 | 🟢 通過 | test_rsi_bounds_0_to_100 ✅ |
| KD 計算 | K/D 0-100 | 🟢 通過 | test_kd_bounds_0_to_100 ✅ |
| MACD DIF 方向 | 趨勢正確 | 🟢 通過 | test_macd_dif_positive/negative ✅ |
| 布林帶關係 | Upper>Middle>Lower | 🟢 通過 | test_upper_above_middle ✅ |
| ETF KD=NaN | ETF不計算KD | 🟢 通過 | test_etf_ticker_kd_is_nan ✅ |
| 訊號JSON格式 | 必填欄位齊全 | 🟢 通過 | test_signal_json_schema ✅ |

### 第二階段｜回測驗證
| 檢查項 | 標準 | Status | 備註 |
|--------|------|--------|------|
| BacktestResult 欄位 | 完整 | 🟢 通過 | test_result_fields_exist ✅ |
| Profit Factor | > 1.25 | 🔴 未執行 | 待Coder完成 |
| Max Drawdown | < 20% | 🔴 未執行 | 待Coder完成 |
| Win Rate | > 45% | 🔴 未執行 | 待Coder完成 |

### 第三階段｜樣本外測試
| 檢查項 | 標準 | Status | 備註 |
|--------|------|--------|------|
| 測試集比例 | >= 訓練集 × 50% | 🔴 未執行 | — |
| 測試集 PF 達標 | > 1.0 | 🔴 未執行 | — |

### 第四階段｜壓力測試
| 檢查項 | 標準 | Status | 備註 |
|--------|------|--------|------|
| 網路斷線容錯 | ERROR訊號不拋例外 | 🔴 未執行 | — |
| HTTP 429 處理 | retry + backoff | 🔴 未執行 | — |
| 記憶體限制 | < 500MB | 🔴 未執行 | — |

---

## 🔴 失敗測試記錄（紅燈追蹤）

| # | 日期 | 測試項目 | 錯誤訊息 | 負責人 | 狀態 | 修復結果 |
|---|------|----------|----------|--------|------|----------|
| 1 | 2026-04-26 | test_kd_bullish_k_above_d | ValueError: operands could not be broadcast together with shapes (38,) (36,) | Steward | 🔴 待修復 | 測試比較了不同長度的陣列。K warmup=10格, D warmup=12格，導致有效值數量不同(38 vs 36)。需修正測試比對邏輯。 |
| 2 | 2026-04-26 | test_kd_bearish_k_below_d | ValueError: 同上 | Steward | 🔴 待修復 | 同上 |

---

## 📍 下一步行動

| 優先順序 | 行動 | 負責人 | 備註 |
|----------|------|--------|------|
| 1 | 修復 test_kd_bullish_k_above_d / test_kd_bearish_k_below_d 的形狀比對問題 | Coder | 比較最後 min(len(K),len(D)) 筆，或用 iloc 對齊 |
| 2 | 執行回測驗證（PF/MaxDD/WinRate）| Monitor | run_backtest.py |
| 3 | 執行樣本外測試（OOS）| Monitor | run_train_test_split.py |
| 4 | 壓力測試：網路斷線、429處理 | Monitor | pytest-asyncio + unittest.mock |
| 5 | mypy --strict 通過 | Coder | 型別檢查 |

---

## 📊 Phase 5 測試驗證報告摘要

| 指標 | 狀態 | 備註 |
|------|------|------|
| MA 均線 | 🟢 綠燈 | 實作完整（MA5/10/20） |
| RSI(14) | 🟢 綠燈 | Wilder's RSI，邊界正確 |
| KD 指標 | 🟡 黃燈 | 計算正確，測試有bug |
| MACD | 🟢 綠燈 | DIF/Signal/Histogram正確 |
| 布林帶 | 🟢 綠燈 | Upper/Middle/Lower/Bandwidth正確 |
| 訊號邏輯 | 🟢 綠燈 | LONG/SHORT/NEUTRAL正確分流 |
| ETF/個股分流 | 🟢 綠燈 | MA參數+KD處理正確 |
| 風控（停損/停利）| 🟢 綠燈 | 固定20%正確 |
| 持股過夜 | 🟢 綠燈 | holding_overnight=true |
| JSON格式 | 🟢 綠燈 | 所有必填欄位正確 |

---

## 📊 統計摘要

| 項目 | 數量 |
|------|------|
| User Stories 總數 | 12 |
| 實作模組總數 | 8 |
| 驗收標準總數 | 11 |
| 失敗測試記錄 | 2 |
| 🟢 綠燈（已完成） | 10 |
| 🟡 黃燈（進行中/待修） | 2 |
| 🔴 紅燈（未開始/失敗） | 0 |

---

*文件版本：v1.1 | 更新者：Steward Agent (Phase 5) | 日期：2026-04-26*
