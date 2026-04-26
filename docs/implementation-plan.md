# 均線動能策略 v2｜實作規劃書

| 項目 | 內容 |
|------|------|
| 文件版本 | v1.0 |
| 撰寫角色 | Coder Agent |
| 依據來源 | SPEC.md（v1.0，2026-04-26） |
| 目的 | 將 SPEC.md 轉為可執行之程式碼實作計畫 |

---

## 1. 程式碼架構設計

```
~/code/tw-stock-signal/
├── SPEC.md                        ← 策略規格書（已存在）
├── requirements.txt               ← 依賴套件（已存在）
├── README.md                      ← 專案說明（已存在）
├── strategy/
│   ├── __init__.py
│   ├── indicators.py             ← 技術指標計算（MA5/MA10/RSI14）
│   └── ma_momentum.py            ← 核心策略邏輯
├── signals/
│   ├── __init__.py
│   └── signal_generator.py        ← 訊號產生器（訊號判斷 + JSON輸出）
├── portfolio/
│   ├── __init__.py
│   └── position_manager.py       ← 倉位管理（進場/出場/停損/停利）
├── backtest/
│   ├── __init__.py
│   └── backtester.py             ← 回測引擎
├── data/
│   ├── __init__.py
│   └── data_loader.py            ← Yahoo Finance 資料載入
├── tests/
│   ├── test_indicators.py        ← 指標單元測試
│   ├── test_signals.py           ← 訊號單元測試
│   └── test_backtest.py          ← 回測整合測試
├── docs/
│   └── implementation-plan.md     ← 本文件
├── run.py                        ← 執行入口
└── main.py                       ← 主程式整合
```

---

## 2. 模組切割職責

### 2.1 `data/data_loader.py`
- **職責**：從 Yahoo Finance 取得日K線資料（OHLCV）
- **外部依賴**：`yfinance`
- **輸出**：`pandas.DataFrame`（index=datetime, columns=Open/High/Low/Close/Volume）

### 2.2 `strategy/indicators.py`
- **職責**：計算 MA5、MA10、RSI(14)
- **內部依賴**：`data_loader.py`
- **輸出**：攜帶指標欄位的 `DataFrame`（ma5/ma10/rsi14）
- **對外介面**：
  ```python
  def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
      """輸入OHLCV資料，輸出含MA5/MA10/RSI14之DataFrame"""
  ```

### 2.3 `strategy/ma_momentum.py`
- **職責**：均線多頭排列/空頭排列判斷
- **內部依賴**：`indicators.py`
- **對外介面**：
  ```python
  def get_ma_state(ma5: float, ma10: float, threshold_pct: float = 1.0) -> str:
      """回傳 'bullish' | 'bearish' | 'neutral'"""
  ```

### 2.4 `signals/signal_generator.py`
- **職責**：根據策略規格輸出標準化 JSON 訊號
- **內部依賴**：`strategy/indicators.py`, `strategy/ma_momentum.py`
- **外部依賴**：`signals/__init__.py` 不對外暴露
- **對外介面**：
  ```python
  def generate_signal(ticker: str, df: pd.DataFrame) -> dict:
      """輸入含指標之DataFrame，輸出標準化訊號JSON"""
  ```

### 2.5 `portfolio/position_manager.py`
- **職責**：管理虛擬倉位、進場/出場判斷、停損停利
- **內部依賴**：`signal_generator.py`
- **對外介面**：
  ```python
  def should_enter(signal: dict) -> bool
  def should_exit(signal: dict, entry_price: float, position_type: str) -> bool
  ```

### 2.6 `backtest/backtester.py`
- **職責**：執行回測、計算績效指標（Profit Factor / Max Drawdown / Win Rate）
- **內部依賴**：`position_manager.py`, `data_loader.py`
- **對外介面**：
  ```python
  def run_backtest(ticker: str, start_date: str, end_date: str) -> dict:
      """回傳績效字典：profit_factor / max_drawdown / win_rate"""
  ```

### 2.7 `run.py`（CLI 執行入口）
- **職責**：提供命令列介面，呼叫 main.py 邏輯
- **對外介面**：`python run.py --ticker 2330.TW --start 2020-01-01 --end 2025-12-31`

### 2.8 `main.py`（整合主程式）
- **職責**：整合所有模組，提供訊號產生與回測之單一入口
- **對外介面**：
  ```python
  def get_signal(ticker: str) -> dict
  def run_full_backtest(ticker: str) -> dict
  ```

---

## 3. 實作順序（優先順序）

| 順序 | 任務 | 依賴關係 | 預估工時 |
|------|------|----------|----------|
| 1 | `data/data_loader.py` | 無 | 1 hr |
| 2 | `strategy/indicators.py` | 1 | 1.5 hr |
| 3 | `strategy/ma_momentum.py` | 2 | 0.5 hr |
| 4 | `signals/signal_generator.py` | 2, 3 | 1.5 hr |
| 5 | `portfolio/position_manager.py` | 4 | 1 hr |
| 6 | `backtest/backtester.py` | 1, 5 | 2 hr |
| 7 | `run.py` + `main.py` | 4, 6 | 0.5 hr |
| 8 | 單元測試 `tests/` | 1, 2, 3, 4 | 2 hr |

**總預估工時：~10 小時（不含文件）**

---

## 4. 四階段驗收對照

| 階段 | 驗收標準 | 對應模組 |
|------|----------|----------|
| 第一階段｜單元測試 | mypy --strict + RSI 初始值正確 | `indicators.py` + `tests/` |
| 第二階段｜回測驗收 | Profit Factor>1.25 / MaxDD<20% / WinRate>45% | `backtester.py` |
| 第三階段｜樣本外測試 | 測試集>=訓練集×50% | `backtester.py`（訓練/測試分割） |
| 第四階段｜壓力測試 | 48h無崩潰 / 記憶體<50MB/h / HTTP 429處理 | `data_loader.py` |

---

## 5. 既有檔案處置

| 檔案 | 處理方式 |
|------|----------|
| `strategy_ma_momentum.py` | 重構為 `strategy/ma_momentum.py`，保留邏輯 |
| `test_strategy.py` | 併入 `tests/` 目錄，重新整合對應新模組 |

---

*文件版本：v1.0 | 撰寫者：Coder Agent | 日期：2026-04-26*
