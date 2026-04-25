import unittest
import numpy as np
from unittest.mock import patch, MagicMock
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from strategy_ma_momentum import MAMomentumStrategy

class MockData:
    """模擬 yfinance 回傳的歷史數據"""
    @staticmethod
    def make(closes):
        mock = MagicMock()
        mock['Close'] = MagicMock()
        mock['Close'].values = np.array(closes, dtype=float)
        return mock

class TestMAMomentumStrategy(unittest.TestCase):

    def setUp(self):
        self.strategy = MAMomentumStrategy()

    # ─── 測試1：零成交量（len(data)=0 時不崩潰） ───
    def test_zero_data_no_crash(self):
        """len(data)=0 時 generate_signal 應回傳 ERROR，不拋例外"""
        with patch.object(self.strategy, 'on_data', return_value=None):
            result = self.strategy.generate_signal("9999.TW")
        self.assertEqual(result['signal'], 'ERROR')
        self.assertEqual(result['emoji'], '❌')
        self.assertEqual(result['alert'], '數據不足')

    # ─── 測試2：跳空開盤（大幅缺口時訊號正確） ───
    def test_gap_up_signal(self):
        """跳空上漲：MA5>MA10 且價格>MA5 → LONG"""
        closes = [90, 91, 92, 93, 94,
                  95, 96, 97, 98, 110,
                  110, 110, 112, 115, 120]
        mock_data = MockData.make(closes)
        result = self.strategy._compute_indicators(mock_data)
        # price=120, ma5≈(112+115+120+110+110)/5≈113.4, ma10≈(95+...+120)/10≈105.7
        self.assertGreater(result['price'], result['ma5'])
        self.assertGreater(result['ma5'], result['ma10'])

    def test_gap_down_signal(self):
        """跳空下跌：MA5<MA10 且價格<MA5 → SHORT"""
        closes = [120, 119, 118, 117, 116,
                  115, 114, 113, 112, 95,
                  94, 93, 92, 91, 90]
        mock_data = MockData.make(closes)
        result = self.strategy._compute_indicators(mock_data)
        # price=90, ma5≈(94+93+92+91+90)/5=92.0, ma10≈(115+...+90)/10=106.5
        self.assertLess(result['price'], result['ma5'])
        self.assertLess(result['ma5'], result['ma10'])

    # ─── 測試3：數值誤差 < 0.0001% ───
    def test_ma_accuracy(self):
        """MA 計算誤差 < 0.0001%"""
        closes = [100.0, 101.0, 102.0, 103.0, 104.0,
                  105.0, 106.0, 107.0, 108.0, 109.0,
                  110.0, 111.0, 112.0, 113.0, 114.0]
        mock_data = MockData.make(closes)
        result = self.strategy._compute_indicators(mock_data)
        # MA5 = (110+111+112+113+114)/5 = 112.0
        expected_ma5 = 112.0
        # MA10 = (105+...+114)/10 = 109.5
        expected_ma10 = 109.5
        error_ma5 = abs(result['ma5'] - expected_ma5) / expected_ma5
        error_ma10 = abs(result['ma10'] - expected_ma10) / expected_ma10
        self.assertLess(error_ma5, 0.0001)
        self.assertLess(error_ma10, 0.0001)

    def test_rsi_bounds(self):
        """RSI 落在 0~100 之間"""
        closes = list(range(80, 115))
        mock_data = MockData.make(closes)
        result = self.strategy._compute_indicators(mock_data)
        self.assertGreaterEqual(result['rsi14'], 0)
        self.assertLessEqual(result['rsi14'], 100)

    def test_rsi_extreme_oversold(self):
        """連續下跌 → RSI 趨近 0"""
        closes = [100.0, 99.0, 98.0, 97.0, 96.0, 95.0, 94.0, 93.0,
                  92.0, 91.0, 90.0, 89.0, 88.0, 87.0, 86.0, 85.0, 84.0]
        mock_data = MockData.make(closes)
        result = self.strategy._compute_indicators(mock_data)
        self.assertLess(result['rsi14'], 30)

    def test_rsi_extreme_overbought(self):
        """連續上漲 → RSI 趨近 100"""
        closes = [80.0, 81.0, 82.0, 83.0, 84.0, 85.0, 86.0, 87.0,
                  88.0, 89.0, 90.0, 91.0, 92.0, 93.0, 94.0, 95.0, 96.0]
        mock_data = MockData.make(closes)
        result = self.strategy._compute_indicators(mock_data)
        self.assertGreater(result['rsi14'], 70)

    def test_signal_cache_persistence(self):
        """shutdown() 寫入 signal_state.json"""
        strategy = MAMomentumStrategy()
        strategy.signal_cache = {
            "TEST.TW": {"price": 100.0, "ma5": 99.0, "ma10": 98.0, "rsi14": 55.0}
        }
        strategy.shutdown()
        import json
        with open("signal_state.json", "r") as f:
            saved = json.load(f)
        self.assertIn("TEST.TW", saved["cache"])
        self.assertEqual(saved["cache"]["TEST.TW"]["price"], 100.0)
        os.remove("signal_state.json")

if __name__ == "__main__":
    unittest.main(verbosity=2)
