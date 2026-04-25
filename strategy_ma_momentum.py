import yfinance as yf
import numpy as np
from datetime import datetime

class MAMomentumStrategy:
    def __init__(self):
        self.stocks = ["2330.TW", "2890.TW", "00919.TW", "2881.TW", 
                       "0052.TW", "0050.TW", "009816.TW", "2317.TW"]
        self.signal_cache = {}
        
    def initialize(self):
        """初始化：預先抓取各股最新資料"""
        for ticker in self.stocks:
            data = yf.Ticker(ticker).history(period="3mo")
            if len(data) >= 10:
                self.signal_cache[ticker] = self._compute_indicators(data)
        return True

    def _compute_indicators(self, data):
        """計算 MA5/MA10/RSI"""
        closes = data['Close'].values
        ma5 = np.mean(closes[-5:])
        ma10 = np.mean(closes[-10:])
        
        # RSI(14) - Wilder's RSI
        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        avg_gain = np.mean(gains[-14:]) if len(gains) >= 14 else 0
        avg_loss = np.mean(losses[-14:]) if len(losses) >= 14 else 0
        rs = avg_gain / avg_loss if avg_loss != 0 else 100
        rsi = 100 - (100 / (1 + rs)) if avg_loss != 0 else 100
        
        return {
            "price": closes[-1],
            "ma5": ma5,
            "ma10": ma10,
            "rsi14": rsi
        }
        
    def on_data(self, ticker):
        """處理即時/歷史數據，計算MA5/MA10/RSI"""
        data = yf.Ticker(ticker).history(period="3mo")
        if len(data) < 10:
            return None
        return self._compute_indicators(data)
        
    def generate_signal(self, ticker):
        """輸出標準化交易訊號 JSON"""
        if ticker not in self.signal_cache:
            self.signal_cache[ticker] = self.on_data(ticker)
            
        d = self.signal_cache[ticker]
        if d is None:
            return {
                "timestamp": datetime.now().isoformat(),
                "ticker": ticker,
                "signal": "ERROR",
                "price": None,
                "ma5": None,
                "ma10": None,
                "rsi14": None,
                "alert": "數據不足",
                "emoji": "❌"
            }
            
        price = d["price"]
        ma5 = d["ma5"]
        ma10 = d["ma10"]
        rsi = d["rsi14"]
        
        if price > ma5 and ma5 > ma10:
            signal = "LONG"
            emoji = "📈"
        elif price > ma5:
            signal = "NEUTRAL"
            emoji = "➖"
        else:
            signal = "SHORT"
            emoji = "📉"
            
        if rsi > 70:
            alert = "超買警訊"
        elif rsi < 30:
            alert = "超賣警訊"
        else:
            alert = None
            
        return {
            "timestamp": datetime.now().isoformat(),
            "ticker": ticker,
            "signal": signal,
            "price": round(price, 2),
            "ma5": round(ma5, 2),
            "ma10": round(ma10, 2),
            "rsi14": round(rsi, 2),
            "alert": alert,
            "emoji": emoji
        }
        
    def shutdown(self):
        """安全關閉：持久化狀態"""
        import json
        with open("signal_state.json", "w") as f:
            json.dump({
                "cache": self.signal_cache,
                "saved_at": datetime.now().isoformat()
            }, f, indent=2)
        return True

# 測試用主程序
if __name__ == "__main__":
    strategy = MAMomentumStrategy()
    strategy.initialize()
    results = []
    for ticker in strategy.stocks:
        sig = strategy.generate_signal(ticker)
        results.append(sig)
        print(f"{sig['emoji']} {ticker}: {sig['signal']} @ {sig['price']} | MA5={sig['ma5']} MA10={sig['ma10']} RSI={sig['rsi14']}")
        if sig['alert']:
            print(f"   ⚠️ {sig['alert']}")
    strategy.shutdown()
