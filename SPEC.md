# 均線動能策略 v2（MA Momentum Strategy v2）策略規格書

## 1. 策略名稱與版本

- **策略名稱：** 均線動能策略（MA Momentum Strategy）
- **版本：** v2.0
- **建立日期：** 2026-04-26
- **基於版本：** v1.0（2026-04-26）
- **狀態：** 已確認，待 Coder 實作

---

## 2. 與 v1 的差異摘要

| 項目 | v1 | v2 |
|------|----|----|
| MA 週期 | 固定 MA5 + MA10 | ETF：MA10 > MA20／個股：MA5 > MA10 |
| 指標數量 | 3 個（MA5, MA10, RSI） | ETF：4 個／個股：5 個 |
| 新增指標 | — | MACD（過濾器）、布林帶（過濾器）、KD（僅個股） |
| 訊號邏輯 | 獨立判斷 | 核心指標（MA+RSI+KD）全滿足 + 過濾器（MACD+布林帶）否決 |
| 停損/停利 | RSI 20/80 主觀判斷 | 固定 20% |
| 持股方式 | 未定義 | 過夜 |
| 角色定位 | 未定義 | 輔助工具 |

---

## 3. 訊號邏輯（Signal Logic）

### 3.1 訊號類型

| 訊號 | 定義 |
|------|------|
| **LONG** | 核心指標（MA + RSI + KD）全部滿足多頭條件，且過濾器（MACD + 布林帶）**不通過**空頭條件 |
| **SHORT** | 核心指標（MA + RSI + KD）全部滿足空頭條件，且過濾器（MACD + 布林帶）**不通過**多頭條件 |
| **NEUTRAL** | 核心指標未全數滿足，或被過濾器否決 |
| **OVERBOUGHT** | RSI > 70（警示，不推翻訊號） |
| **OVERSOLD** | RSI < 30（警示，不推翻訊號） |

### 3.2 指標多頭/空頭條件

| 指標 | 多頭（LONG） | 空頭（SHORT） |
|------|-------------|--------------|
| **MA** | MA5 > MA10（個股）<br>MA10 > MA20（ETF） | MA5 < MA10（個股）<br>MA10 < MA20（ETF） |
| **RSI** | RSI > 50 | RSI < 50 |
| **KD** | K > D 且 K 在低檔反轉（個股專用）<br>ETF 不使用 KD | K < D 且 K 在高檔反轉（個股專用）<br>ETF 不使用 KD |
| **MACD**（過濾器） | DIF > 0 且 MACD > Signal | DIF < 0 且 MACD < Signal |
| **布林帶**（過濾器） | Bandwidth 擴張 且 突破上軌 | Bandwidth 擴張 且 跌破下軌 |

### 3.3 過濾器邏輯

- **LONG 的過濾：** 若 MACD 滿足空頭條件（見上表）或 布林帶滿足空頭條件，則 LONG 被否決，改為 NEUTRAL。
- **SHORT 的過濾：** 若 MACD 滿足多頭條件或 布林帶滿足多頭條件，則 SHORT 被否決，改為 NEUTRAL。
- 過濾器**不改寫** OVERBOUGHT / OVERSOLD 警示。

---

## 4. ETF vs 個股參數分工

| 參數 | ETF（0050 / 0052 / 00919 / 009816） | 個股（2330 / 2890 / 2881 / 2317） |
|------|-------------------------------------|-----------------------------------|
| MA | MA10 > MA20 | MA5 > MA10 |
| RSI | ✅ RSI > 50（LONG）／ RSI < 50（SHORT） | ✅ RSI > 50（LONG）／ RSI < 50（SHORT） |
| KD | ❌ 不使用 | ✅ K > D 且 K 在低檔反轉（LONG）<br>✅ K < D 且 K 在高檔反轉（SHORT） |
| MACD | ✅ 使用（過濾器） | ✅ 使用（過濾器） |
| 布林帶 | ✅ 使用（過濾器） | ✅ 使用（過濾器） |
| **核心指標數量** | **4 個**（MA + RSI + MACD + 布林帶） | **5 個**（MA + RSI + KD + MACD + 布林帶） |

> **ETF 判斷 LONG/SHORT：** MA + RSI + MACD + 布林帶，四個指標需全部滿足方向一致性，KD 不參與計算。

---

## 5. 風控參數

| 參數 | 數值 |
|------|------|
| 停損（Stop Loss） | 進場後下跌 20% |
| 停利（Take Profit） | 進場後上漲 20% |
| 持股方式 | 過夜（不留日內倉位） |
| 角色定位 | 輔助工具（不作主要決策依據） |

---

## 6. 支援股票

| 代碼 | 名稱 | 類型 |
|------|------|------|
| 2330.TW | 台積電 | 個股 |
| 2890.TW | 永豐金 | 個股 |
| 2881.TW | 富邦金 | 個股 |
| 2317.TW | 鴻海 | 個股 |
| 0050.TW | 元大台灣50 | ETF |
| 0052.TW | 富邦科技 | ETF |
| 00919.TW | 群益台灣精選高息 | ETF |
| 009816.TW | 台新永續化趨勢 | ETF |

---

## 7. 數據規格

| 項目 | 規格 |
|------|------|
| 數據來源 | Yahoo Finance（`yfinance`） |
| 頻率 | 日K線（Daily OHLCV） |
| 指標前溯期 | 至少 30 個交易日（確保 MACD / KD 收斂） |
| 目標市場 | 台股（.TW 尾碼） |

---

## 8. 訊號格式（標準化 JSON）

```json
{
  "timestamp": "2026-04-26T10:30:00",
  "ticker": "2330.TW",
  "signal": "LONG",
  "price": 850.0,
  "indicators": {
    "ma5": 840.0,
    "ma10": 835.0,
    "ma20": 820.0,
    "rsi14": 65.5,
    "k": 72.3,
    "d": 68.1,
    "macd_dif": 5.2,
    "macd_signal": 3.1,
    "macd_histogram": 2.1,
    "bb_upper": 870.0,
    "bb_middle": 845.0,
    "bb_lower": 820.0,
    "bb_bandwidth": 50.0
  },
  "filters_passed": true,
  "stop_loss_pct": 20.0,
  "take_profit_pct": 20.0,
  "holding_overnight": true,
  "alert": null,
  "emoji": "📈"
}
```

### 欄位說明

| 欄位 | 類型 | 說明 |
|------|------|------|
| `timestamp` | ISO 8601 字串 | 訊號產生時間 |
| `ticker` | 字串 | 股票代碼（Yahoo 格式） |
| `signal` | 列舉值 | LONG / NEUTRAL / SHORT / OVERBOUGHT / OVERSOLD |
| `price` | 浮點數 | 當日收盤價 |
| `indicators` | 物件 | 完整指標數值（MA / RSI / KD / MACD / 布林帶） |
| `filters_passed` | 布林 | 過濾器是否通過（LONG/SHORT 時必為 true） |
| `stop_loss_pct` | 浮點數 | 停損百分比（固定 20） |
| `take_profit_pct` | 浮點數 | 停利百分比（固定 20） |
| `holding_overnight` | 布林 | 是否過夜（固定 true） |
| `alert` | 字串或 null | OVERBOUGHT / OVERSOLD 警示（無則為 null） |
| `emoji` | 字串 | 📈 / 📉 / ➡️ / ⚠️ / 🔔 |

---

## 9. 與 Dashboard v2 的差異說明

| 項目 | 均線動能策略 v2 | Dashboard v2 |
|------|----------------|--------------|
| 專案性質 | **獨立專案** | 現有對帳單系統 |
| 目標功能 | 技術分析訊號產生 | 持股對帳與績效報告 |
| 數據來源 | Yahoo Finance | FinMind API + Yahoo Finance |
| 核心模組 | `strategy_ma_momentum.py` | `output/`, `integrate.py` |
| 輸出形式 | JSON 訊號 | PDF 報告 + HTML Dashboard |
| 相依性 | **不依賴** Dashboard v2 任何函數 | — |

**重要宣告：本專案（均線動能策略 v2）為完全獨立專案，不使用 Dashboard v2 之任何函式、資料或設定。**

---

## 10. 專案結構

```
~/code/tw-stock-signal/
├── SPEC.md                      ← 本規格書（v2）
├── README.md
├── requirements.txt
├── strategy_ma_momentum.py      ← 核心策略實作（v2）
├── test_strategy.py             ← 測試
└── signals/                     ← 訊號輸出（JSON）
```

---

## 11. v2 實作約束

1. **不做未討論的假設：** 所有參數、邏輯皆來自本規格書，不自行發明。
2. **ETF / 個股分流：** 進策略前先判斷類型，套用對應參數表（見第 4 節）。
3. **過濾器順序：** 先算核心指標 → 斷言方向 → 再跑過濾器 否決。
4. **警示不覆寫：** OVERBOUGHT / OVERSOLD 為獨立警示，不因過濾器或核心指標而消失。
5. **停損停利：** 以**進場價**為基準計算 20%，非市價百分比。

---

*文件版本：v2.0 | 建立者：Analyst Agent | 日期：2026-04-26*
