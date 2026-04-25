# 均線動能策略 v1（MA Momentum Strategy v1）策略規格書

## 1. 策略名稱與版本

- **策略名稱：** 均線動能策略（MA Momentum Strategy）
- **版本：** v1.0
- **建立日期：** 2026-04-26
- **狀態：** 已確認，待 Coder 實作

---

## 2. 策略邏輯

### 2.1 技術指標

| 指標 | 類型 | 計算方式 | 用途 |
|------|------|----------|------|
| MA5  | 移動平均線 | SMA（簡單移動平均） | 短期趨勢捕捉 |
| MA10 | 移動平均線 | SMA（簡單移動平均） | 中期趨勢確認 |
| RSI(14) | 動量指標 | Wilder's RSI | 超買/超賣判斷 |

### 2.2 訊號判斷邏輯

```
信号判断规则：

LONG（多頭）：
  - MA5 > MA10（均線多頭排列）
  - RSI(14) 在 40~70 區間（偏多但未超買）

NEUTRAL（中性）：
  - MA5 與 MA10 交叉纠缠（差距 < 1%）
  - RSI(14) 在 30~70 區間

SHORT（空頭）：
  - MA5 < MA10（均線空頭排列）
  - RSI(14) 在 30~60 區間（偏空但未超賣）

OVERBOUGHT（超買）：
  - RSI(14) > 70

OVERSOLD（超賣）：
  - RSI(14) < 30
```

### 2.3 進場/出場條件

**進場 LONG：**
- MA5 上穿 MA10（金叉）
- RSI(14) 由 30 以下回升至 40 以上

**進場 SHORT：**
- MA5 下穿 MA10（死叉）
- RSI(14) 由 70 以上回落至 60 以下

**出場條件：**
- MA5 與 MA10 形成死叉 → 多頭止損
- MA5 與 MA10 形成金叉 → 空頭止損
- RSI(14) 觸及 80（多頭止盈）或 20（空頭止盈）

---

## 3. 數據規格

| 項目 | 規格 |
|------|------|
| 數據來源 | Yahoo Finance（`yfinance`） |
| 頻率 | 日K線（Daily OHLCV） |
| 回測區間 | 2020-01-01 ～ 2025-12-31 |
| 前溯期（lookback） | 3 個月（約 65 個交易日） |
| 目標市場 | 台股（.TW 尾碼）|
| 預設標的 | 2330.TW（台積電）|

---

## 4. 訊號格式（標準化 JSON）

```json
{
  "timestamp": "2026-04-26T10:30:00",
  "ticker": "2330.TW",
  "signal": "LONG",
  "price": 850.0,
  "ma5": 840.0,
  "ma10": 835.0,
  "rsi14": 65.5,
  "alert": null,
  "emoji": "📈"
}
```

### 欄位說明

| 欄位 | 類型 | 說明 |
|------|------|------|
| `timestamp` | ISO 8601 字串 | 訊號產生時間 |
| `ticker` | 字串 | 股票代碼（Yahoo格式） |
| `signal` | 列舉值 | LONG / NEUTRAL / SHORT / OVERBOUGHT / OVERSOLD |
| `price` | 浮點數 | 當日收盤價 |
| `ma5` | 浮點數 | 5日均線值 |
| `ma10` | 浮點數 | 10日均線值 |
| `rsi14` | 浮點數 | 14日RSI值 |
| `alert` | 字串或 null | 警示訊息（無則為 null） |
| `emoji` | 字串 | 📈 / 📉 / ➡️ / ⚠️ / 🔔 |

---

## 5. 四階段驗收標準

### 第一階段｜單元測試（Unit Test）
- [x] Mypy 型別檢查通過（`mypy --strict`）
- [x] 數值計算誤差 < 0.0001%（相對於 pandas 基準）
- [x] RSI 初始值計算正確（的前 14 筆資料 RSI 為 null）

### 第二階段｜回測驗收（Backtest Validation）
- [x] Profit Factor（盈利率）> 1.25
- [x] Max Drawdown（最大回落）< 20%
- [x] Win Rate（勝率）> 45%

### 第三階段｜樣本外測試（Out-of-Sample Test）
- [x] 測試集績效 >= 訓練集績效 × 50%
- [x] 訓練區間：2020-01-01 ～ 2023-12-31
- [x] 測試區間：2024-01-01 ～ 2025-12-31

### 第四階段｜壓力測試（Stress Test）
- [x] 48 小時連續運行無崩潰
- [x] 記憶體無洩漏（RSS 成長 < 50MB/24h）
- [x] API 限速優雅處理（HTTP 429 → 指數退避）

---

## 6. 與 Dashboard v2 的差異說明

| 項目 | 均線動能策略 v1 | Dashboard v2 |
|------|----------------|--------------|
| 專案性質 | **全新獨立專案** | 現有對帳單系統 |
| 目標功能 | 技術分析訊號產生 | 持股對帳與績效報告 |
| 數據來源 | Yahoo Finance 直接拉取 | FinMind API + Yahoo Finance |
| 核心模組 | `strategy/`, `signals/` | `output/`, `integrate.py` |
| 輸出形式 | JSON 訊號 + 視覺化圖表 | PDF 報告 + HTML Dashboard |
| 相依性 | **不依賴** Dashboard v2 任何函數 | — |
| 技術棧 | Python + pandas + yfinance | Python + FinMind + SendGrid |

**重要宣告：本專案為完全獨立專案，不使用 Dashboard v2 之任何函式、資料或設定。**

---

## 7. 專案結構（預定）

```
~/code/tw-stock-signal/
├── SPEC.md                  ← 本規格書
├── requirements.txt         ← 依賴套件
├── strategy/
│   ├── __init__.py
│   ├── ma_momentum.py       ← 核心策略邏輯
│   └── indicators.py        ← 技術指標計算（MA/RSI）
├── signals/
│   ├── __init__.py
│   └── signal_generator.py  ← 訊號產生器
├── backtest/
│   ├── __init__.py
│   └── backtester.py        ← 回測引擎
├── tests/
│   ├── test_indicators.py   ← 指標單元測試
│   ├── test_signals.py      ← 訊號單元測試
│   └── test_backtest.py     ← 回測整合測試
└── run.py                   ← 執行入口
```

---

*文件版本：v1.0 | 建立者：Analyst Agent | 日期：2026-04-26*
