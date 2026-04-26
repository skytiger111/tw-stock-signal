# 開發進度筆記

## 2026-04-26

### 完成項目
- ATR(14) 指標 → `strategy/indicators.py`（ecd7700）
- 2890 ATR 濾鏡（atr < atr_ma×0.40）→ `signals/signal_generator.py`（ecd7700）
- 2890 8% 停損（f412016）
- README.md 回測結果更新（3366ba0）

### equity bug 排查過程
**症狀**：MaxDD 顯示 5000%+，進場後 equity 從 100萬瞬間跌到 50萬

**數學公式（已驗證正確）**：
```python
LONG:  equity = cash + entry_capital * (current_price / entry_price)
SHORT: equity = cash + entry_capital * (2 - current_price / entry_price)
```

**問題根因**：`backtest/backtester.py` 的 `_compute_equity` call site（line 218）
- position 已經是 None，但傳入的 position.entry_capital 是舊值
- capital 在進場時被扣減（capital -= pos_cap），但 equity 計算沒正確加回 position_value
- 變數生命週期不一致導致

**下次修復方向**：
- 重構 `_compute_equity`，在進場時就把 position_value 算進 equity
- 或者用更簡單的方式：每次 equity = cash + position_value（如果有倉位）

### 重要發現
- 2890 PF=0.85 根本原因：**SHORT 逆勢**（股價 18→31 多頭，策略不斷發 SHORT）
- 2330 PF=0.73 同樣問題
- 00919 交易過頻（70筆，PF=1.01）

### 七檔回測結果（2024-01-01 → 2026-04-25）
| 代碼 | PF | MaxDD | WR | N |
|------|-----|-------|-----|---|
| 0052 | 3.08 ⭐ | 11.1% | 47.7% | 65 |
| 0050 | 2.14 ⭐ | 12.0% | 51.7% | 58 |
| 2317 | 1.40 | 4.7% | 50.0% | 4 |
| 00919 | 1.01 ⚠️ | 18.3% | 40.0% | 70 |
| 2881 | 1.18 ⚠️ | 3.2% | 28.6% | 7 |
| 2890 | 0.85 ⚠️ | 10.6% | 38.5% | 13 |
| 2330 | 0.73 ⚠️ | 12.1% | 33.3% | 6 |

### 下次優先順序
1. 🔴 **backtester equity bug** — 修 `_compute_equity` + call site
2. 🟡 **2330/2881/2890 SHORT 逆勢** — 加均線多頭濾鏡
3. 🟡 **00919 交易過頻** — 加 ATR 濾鏡
