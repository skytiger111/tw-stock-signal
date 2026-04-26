# 均線動能策略 v2 測試計畫書

## 1. 目標與範圍
本測試計畫針對 **均線動能策略 v2**（MA Momentum Strategy v2）之所有功能進行驗證，包含單元、整合、回測與壓力測試，並分別驗證 **ETF 版** 與 **個股版**。

## 2. 測試類型與項目

### 2.1 單元測試 (Unit Tests)
| 指標 | 測試項目 | 測試說明 | Must/Should |
|------|----------|----------|-------------|
| MA | 正確計算 MA5、MA10、MA20 | 給定固定收盤價序列，驗證滑動平均值 | Must |
| RSI | 計算 14 期 RSI | 包含升勢、跌勢與零除情況 | Must |
| KD | 計算 Slow %K、%D | 只在 STOCK 項目，ETF 回傳 NaN | Must |
| MACD | 計算 DIF、Signal、Histogram | 驗證 EMA 計算正確性 | Should |
| Bollinger Bands | 計算 Upper、Middle、Lower、Bandwidth | 驗證帶寬與標準差計算 | Should |
| Ticker Classifier | 正確分類為 STOCK 或 ETF | Must |

### 2.2 整合測試 (Integration Tests)
| 模組 | 測試項目 | 說明 | Must/Should |
|------|----------|------|-------------|
| data → indicators | 從 `data_loader` 讀取 OHLCV → `calculate_indicators` 產出完整欄位 | 確保指標欄位完整且型別正確 | Must |
| indicators → strategy | 以指標資料產生交易訊號 (`MAMomentumStrategy.generate_signal`) | 驗證 LONG / SHORT / NEUTRAL 及過濾器邏輯 | Must |
| strategy → portfolio | 訊號流入 `portfolio` 模組（若有） | 檢查持倉更新、止損止盈計算 | Should |

### 2.3 回測測試 (Back‑test)
- **期間**：2020‑01‑01 至 2025‑12‑31
- **資產**：ETF（0050、0052、00919、009816）與個股（2330、2890、2881、2317）
- **指標**：年度報酬、最大回撤、夏普比、勝率、平均持倉天數
- **成功標準**：
  - Must：策略在任意標的至少產生 30 筆有效信號且不拋錯誤。
  - Should：年化報酬 > 5%，最大回撤 < 20%。

### 2.4 壓力測試 (Stress Tests)
| 場景 | 測試步驟 | 預期行為 | Must/Should |
|------|----------|----------|-------------|
| 網路斷線 | 模擬 `yfinance` 連線失敗 (mock raise `ConnectionError`) | 策略返回 `ERROR` 訊號，且不拋未捕獲例外 | Must |
| API 超時 | 設定 `timeout=5s` 並延遲回應 | 超時後返回 `ERROR`，且記錄日誌 | Should |
| 記憶體限制 | 在大量歷史資料（10 年）上執行 `calculate_indicators` | 不超過 500MB 記憶體使用，未發生 `MemoryError` | Should |

### 2.5 ETF vs 個股版測試
- **ETF 版**：檢驗 MA10 > MA20、KD 為 NaN、過濾器正確應用。
- **個股版**：檢驗 MA5 > MA10、KD 需符合 K>D 且在低檔（LONG）/高檔（SHORT）時觸發。
- 每個版本各自 **Must** 產生 20 筆有效訊號。

## 3. 成功標準分級
| 分級 | 定義 | 必須通過項目 |
|------|------|--------------|
| **Must Pass** | 必須全部成功，否則策略不可部署 | 所有單元測試、整合測試、ETF/個股版基本功能、網路斷線容錯、回測最小信號量。
| **Should Pass** | 建議通過，可接受少量失敗 (≤5%) | MACD、Bollinger、性能指標、回測績效門檻。

## 4. 測試執行方式
- 使用 **pytest** 作為測試框架。
- 單元與整合測試放於 `tests/` 目錄，檔名遵循 `test_*.py`。
- 回測腳本 `backtest/run_backtest.py`，輸出 CSV 與圖表至 `backtest/results/`。
- 壓力測試利用 **pytest‑asyncio** 與 **unittest.mock** 模擬失敗情境。
- CI/CD（GitHub Actions）自動執行所有 `Must Pass` 測試，`Should Pass` 為警示。

## 5. 交付物
- `tests/` 內完整測試程式碼
- `backtest/` 及結果檔案
- `docs/test-plan.md`（本文件）
- CI 設定檔 `.github/workflows/ci.yml`

---
*本文檔由 Steward Agent 依照 TEST‑MASTER skill 與 SPEC.md 產出，供開發團隊作為測試基準。*
