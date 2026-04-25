# tw-stock-signal

台股技術面選股模組 - 均線動能策略 v1

## 策略邏輯

| 訊號 | 條件 | Emoji |
| LONG（多頭）| MA5 > MA10 且 RSI(14) 在 40~70 | 📈 |
| SHORT（空頭）| MA5 < MA10 且 RSI(14) 在 30~60 | 📉 |
| NEUTRAL（中性）| 其他情況 | ➖ |
| OVERBOUGHT（超買）| RSI(14) > 70 | ⚠️ |
| OVERSOLD（超賣）| RSI(14) < 30 | ⚠️ |

## 支援股票

2330.TW（台積電）、2890.TW（永豐金）、00919.TW（群益高息）、
2881.TW（富邦金）、0052.TW（富邦科技）、0050.TW（元大台灣50）、
009816.TW（凱基TOP50）、2317.TW（鴻海）

## 安裝

pip install -r requirements.txt

## 執行

python strategy_ma_momentum.py

## 測試

pytest test_strategy.py -v

## 版本演化

| 版本 | 狀態 | 說明 |
| v0.1 | ✅ | MVP，單元測試通過 |
| v0.2 | ⏳ | 歷史回測（2020-2025）|
| v0.3 | ⏳ | 自動化排程 + Telegram通知 |
| v1.0 | 🎯 | Docker部署 + 影子交易驗證 |

## 數據來源

Yahoo Finance（透過 yfinance）
