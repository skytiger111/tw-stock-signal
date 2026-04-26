# 均線動能策略 v2｜實作規劃書（更新版）

| 項目 | 內容 |
|------|------|
| 文件版本 | v2.0 |
| 撰寫角色 | Coder Agent |
| 依據來源 | SPEC.md（v2.0，commit 77f5c9b，2026-04-26） |
| 更新日期 | 2026-04-26 |

---

## 1. 程式碼架構設計

```
~/code/tw-stock-signal/
├── SPEC.md                          ← 策略規格書（v2.0）
├── requirements.txt
├── README.md
├── docs/
│   └── implementation-plan.md       ← 本文件
├── data/
│   ├── __init__.py
│   └── data_loader.py               ← Yahoo Finance 資料載入
├── strategy/
│   ├── __init__.py
│   ├── indicators.py                ← 技術指標計算（MA / RSI / KD / MACD / BB）
│   └── ticker_classifier.py         ← ETF / 個股分類判斷
├── signals/
│   ├── __init__.py
│   └── signal_generator.py          ← 訊號產生器（核心指標 + 過濾器邏輯）
├── portfolio/
│   ├── __init__.py
│   └── position_manager.py          ← 倉位管理（停損 20% / 停利 20% / 過夜）
├── backtest/
│   ├── __init__.py
│   └── backtester.py                ← 回測引擎
├── tests/
│   ├── test_indicators.py           ← 指標單元測試
│   ├── test_signal_generator.py      ← 訊號邏輯測試
│   └── test_backtest.py             ← 回測整合測試
├── run.py                           ← CLI 執行入口
└── main.py                          ← 整合主程式
```

---

## 2. 模組切割職責

### 2.1 `data/data_loader.py`
- **職責**：從 Yahoo Finance 取得日K線（OHLCV），前溯至少 30 交易日
- **外部依賴**：`yfinance`
- **對外介面**：
  ```python
  def load_ohlcv(ticker: str, days: int = 60) -> pd.DataFrame:
      """回傳含 Open/High/Low/Close/Volume 之 DataFrame，index=Datetime"""
  ```

### 2.2 `strategy/ticker_classifier.py`
- **職責**：判斷 ETF 或個股（對應不同 MA 週期與 KD 是否啟用）
- **對外介面**：
  ```python
  def classify_ticker(ticker: str) -> str:
      """回傳 'ETF' 或 'STOCK'"""
  ```
- **依據**：第 4 節支援股票清單

### 2.3 `strategy/indicators.py`
- **職責**：計算全部技術指標
  - MA：個股用 MA5/MA10，ETF 用 MA10/MA20
  - RSI(14)
  - KD(9, 3, 3)：僅個股，ETF 設為 null
  - MACD(12, 26, 9)：DIF / Signal / Histogram
  - 布林帶(20)：上軌 / 中軌 / 下軌 / Bandwidth
- **對外介面**：
  ```python
  def calculate_indicators(df: pd.DataFrame, ticker_type: str) -> pd.DataFrame:
      """輸入OHLCV，輸出含全部指標之DataFrame"""
  ```

### 2.4 `signals/signal_generator.py`
- **職責**：
  1. 計算核心指標（MA + RSI + KD）多空方向
  2. 過濾器（MACD + 布林帶）否決 Logic
  3. 輸出標準化 JSON（第 8 節格式）
- **依據邏輯**：第 3 節訊號邏輯 + 第 3.3 節過濾器
- **對外介面**：
  ```python
  def generate_signal(ticker: str, df_with_indicators: pd.DataFrame) -> dict:
      """輸出標準化訊號JSON"""
  ```

### 2.5 `portfolio/position_manager.py`
- **職責**：
  - 進場/出場判斷（根據停損 20%、停利 20%）
  - 持股過夜標記（固定 True）
- **對外介面**：
  ```python
  def should_enter(signal: dict) -> bool
  def should_exit(signal: dict, entry_price: float, position_type: str) -> bool
  def get_stop_loss(entry_price: float) -> float
  def get_take_profit(entry_price: float) -> float
  ```

### 2.6 `backtest/backtester.py`
- **職責**：歷史回測 + 績效指標（Profit Factor / Max Drawdown / Win Rate）
- **對外介面**：
  ```python
  def run_backtest(ticker: str, start_date: str, end_date: str) -> dict:
      """輸出績效字典"""
  ```

### 2.7 `run.py` + `main.py`
- **run.py**：CLI 介面（`python run.py --ticker 2330.TW`）
- **main.py**：`get_signal()` + `run_full_backtest()` 統一入口

---

## 3. 實作順序

| 順序 | 任務 | 依賴 | 預估工時 |
|------|------|------|----------|
| 1 | `data/data_loader.py` | 無 | 1 hr |
| 2 | `strategy/ticker_classifier.py` | 無 | 0.5 hr |
| 3 | `strategy/indicators.py` | 1, 2 | 2 hr |
| 4 | `signals/signal_generator.py` | 3 | 3 hr |
| 5 | `portfolio/position_manager.py` | 4 | 1 hr |
| 6 | `backtest/backtester.py` | 1, 5 | 2 hr |
| 7 | `run.py` + `main.py` | 4, 6 | 0.5 hr |
| 8 | 單元測試 `tests/` | 3, 4 | 2 hr |

**總預估工時：~12 小時**

---

## 4. 訊號邏輯實作要點（v2 核心）

### 4.1 訊號判斷流程
```
1. 載入資料 + 計算指標
2. 判斷 ticker_type（ETF / STOCK）
3. 核心指標多空：
   - MA 多頭：MA5 > MA10（個股）或 MA10 > MA20（ETF）
   - RSI 多頭：RSI > 50
   - KD 多頭：K > D 且 K 低檔反轉（個股，ETF 跳過）
4. 過濾器檢查：
   - MACD 空頭條件 → 否決 LONG
   - MACD 多頭條件 → 否決 SHORT
   - 布林帶空頭條件 → 否決 LONG
   - 布林帶多頭條件 → 否決 SHORT
5. 輸出訊號 + 警示（OVERBOUGHT/OVERSOLD 獨立附加）
```

### 4.2 警示不覆寫
- OVERBOUGHT / OVERSOLD 為獨立欄位 `alert`，不因過濾器或核心指標消失

---

## 5. 四階段驗收標準

| 階段 | 驗收標準 | 對應模組 |
|------|----------|----------|
| 第一階段｜單元測試 | mypy --strict + RSI 初始值正確 | `indicators.py` |
| 第二階段｜回測驗收 | PF>1.25 / MaxDD<20% / WinRate>45% | `backtester.py` |
| 第三階段｜樣本外測試 | 測試集 >= 訓練集 × 50% | `backtester.py` |
| 第四階段｜壓力測試 | 48h無崩潰 / 記憶體<50MB/h / HTTP 429處理 | `data_loader.py` |

---

## 6. 既有檔案處置

| 檔案 | 處理方式 |
|------|----------|
| `strategy_ma_momentum.py` | 重構成 `strategy/indicators.py` + `signals/signal_generator.py` |
| `test_strategy.py` | 併入 `tests/`，依新模組重構 |

---

*文件版本：v2.0 | 撰寫者：Coder Agent | 日期：2026-04-26*
