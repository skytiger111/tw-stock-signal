# 均線動能策略 v2 部署計畫書

> 文件版本：v1.0 | 日期：2026-04-26 | 狀態：初稿

---

## 1. 部署架構

### 1.1 目標環境

| 項目 | 規格 |
|------|------|
| 主機 | Mac mini（M1/M2/M3， macOS） |
| 運行方式 | Docker 容器化（Docker Desktop） |
| 排程器 | 本機 cron |
| 通知 | Telegram Bot（@TigerMoniter_bot） |

### 1.2 系統架構圖

```
┌─────────────────────────────────────────────────────┐
│                   Mac mini Host                      │
│                                                     │
│  ┌───────────────────────────────────────────────┐  │
│  │            Docker Container                    │  │
│  │  tw-stock-signal:v2                           │  │
│  │                                                │  │
│  │  ├── strategy_ma_momentum.py                  │  │
│  │  ├── signals/ (JSON output)                   │  │
│  │  └── requirements.txt                        │  │
│  └───────────────────────────────────────────────┘  │
│           ▲                    ▲                    │
│           │ cron (14:30)      │ Telegram notify    │
│           │                    │                    │
│  ┌────────┴────────────────────┴──────────────┐    │
│  │         Monitor Agent (@TigerMoniter_bot)  │    │
│  │  - 影子交易比對                             │    │
│  │  - 48小時持倉監控                            │    │
│  │  - 停損/停利警示                            │    │
│  └─────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────┘
```

---

## 2. Docker 容器化設計

### 2.1 Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安裝系統依賴（TA-Lib / scipy 等）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 複製依賴檔案
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用程式
COPY . .

# 訊號輸出目錄
RUN mkdir -p /app/signals

# 預設執行指令
CMD ["python", "strategy_ma_momentum.py", "--all"]
```

### 2.2 docker-compose.yml

```yaml
version: '3.8'

services:
  tw-stock-signal:
    image: tw-stock-signal:v2
    container_name: tw-stock-signal
    build:
      context: .
      dockerfile: Dockerfile
    volumes:
      # 訊號輸出映射到主機
      - ./signals:/app/signals
      # 設定檔映射
      - ./config:/app/config:ro
      # 日誌映射
      - ./logs:/app/logs
    environment:
      - TZ=Asia/Taipei
    restart: unless-stopped

networks:
  default:
    name: tw-stock-network
```

### 2.3 requirements.txt

```
yfinance>=0.2.36
pandas>=2.0.0
numpy>=1.24.0
ta-lib>=0.4.28   # 或使用 ta（需編譯）
# 若 TA-Lib 安裝困難，改用：
# pandas-ta>=0.3.14
```

---

## 3. 每日執行流程

### 3.1 每日排程（14:30 訊號產生）

```bash
# crontab -e 設定
# 平日（週一至週五）14:30 執行
30 14 * * 1-5 cd ~/code/tw-stock-signal && docker compose up --rm tw-stock-signal >> logs/cron.log 2>&1
```

### 3.2 訊號產生流程

```
14:30 ────> 啟動 Container
              │
              ▼
         抓取即時報價（Yahoo Finance）
              │
              ▼
         計算指標（MA / RSI / KD / MACD / 布林帶）
              │
              ▼
         判斷訊號（LONG / NEUTRAL / SHORT）
              │
              ▼
         輸出 JSON（signals/YYYY-MM-DD.json）
              │
              ▼
         Monitor Agent 讀取並通知（Telegram）
              │
              ▼
         Container 自動終止
```

### 3.3 Monitor Agent 通知格式

```
📊 均線動能訊號 2026-04-26 14:30

📈 LONG 訊號
• 2330.TW 台積電 $850 (+1.2%)
• 00919.TW 群益高息 $23.4 (+0.8%)

⚠️ 警示
• 2330.TW RSI > 70（OVERBOUGHT）

• 停損：20% | 停利：20% | 持股過夜
```

---

## 4. 備份與還原機制

### 4.1 備份策略

| 項目 | 頻率 | 位置 |
|------|------|------|
| 訊號 JSON | 每日（自動） | `~/code/tw-stock-signal/signals/` |
| 設定檔 | 每次修改前 | `~/code/backups/tw-stock-signal/` |
| 完整專案 | 每次 major 版本 | GitHub remote |
| 歷史資料 | 每月歸檔 | `~/code/backups/tw-stock-signal/archive/` |

### 4.2 備份指令

```bash
# 設定檔備份（修改前自動執行）
cp ~/code/tw-stock-signal/strategy_ma_momentum.py \
   ~/code/backups/tw-stock-signal/strategy_ma_momentum.py.$(date +%Y%m%d)

# 完整專案 Git 備份
cd ~/code/tw-stock-signal && git add -A && git commit -m "backup: $(date +%Y%m%d)"
```

### 4.3 還原流程

```bash
# 1. 還原設定檔
cp ~/code/backups/tw-stock-signal/strategy_ma_momentum.py.YYYYMMDD \
   ~/code/tw-stock-signal/strategy_ma_momentum.py

# 2. 重新 build Docker image
docker compose build --no-cache tw-stock-signal

# 3. 驗證
docker compose up --rm tw-stock-signal
```

---

## 5. Monitor Agent 職責定義

### 5.1 影子交易比對

- **觸發時機：** 虎哥手動下單後，透過 Telegram 告知 Monitor
- **比對方式：** 比對虎哥實際成交與訊號方向
- **記錄格式：** 存入 `signals/trades.log`

```
[TIGER] 2330.TW LONG @ 850
[MONITOR] 影子比對 ✓ 訊號相符
```

### 5.2 48 小時持倉監控

| 時間點 | 檢查項目 |
|--------|----------|
| 进倉後 24h | 停損/停利條件是否觸及 |
| 进倉後 48h | 發送持仓報告至 Telegram |

### 5.3 停損/停利警示

- 當日跌幅 > 20% → 立即通知
- 當日漲幅 > 20% → 立即通知（建議分批獲利了結）

### 5.4 Monitor Agent 工作流程

```
14:30 ────> 接收訊號 JSON
              │
              ▼
         解析 LONG / SHORT
              │
              ▼
         發送訊號通知（TG）
              │
              ▼
         等待虎哥回覆（15min timeout）
              │
         ├── 有回覆 → 記錄交易
         │
         └── 無回覆 → 維持監控（48h）
              │
              ▼
         每 8h 檢查持倉狀態
```

---

## 6. 升級流程（不停機更新策略參數）

### 6.1 更新步驟

```
Step 1: 備份當前版本
Step 2: 修改 strategy_ma_momentum.py（新增參數）
Step 3: 修改 SPEC.md（對應更新）
Step 4: Git commit + push
Step 5: GitHub Actions 自動 rebuild Docker image
Step 6: 驗證新版本（新訊號已更新）
Step 7: 舊 Container 自然終止（下一次 cron 執行新版本）
```

### 6.2 參數更新對照表

| 參數 | 修改位置 | 範圍 |
|------|---------|------|
| MA 週期 | `strategy_ma_momentum.py` 第 30-40 行 | 5/10/20 |
| RSI 門檻 | `strategy_ma_momentum.py` 第 50 行 | 50（可調整） |
| 停損/停利 | `strategy_ma_momentum.py` 第 80 行 | 20%（可調整） |
| 支援股票 | `strategy_ma_momentum.py` 第 20 行 | 新增代碼 |

### 6.3 不停機原則

1. **不做還原（revert）覆蓋**，只做前向更新
2. Docker Image 使用 tag：`latest` + `YYYYMMDD`
3. 出問題時回覆到上一個 stable tag

---

## 7. Mac mini 資源需求

| 資源 | 需求 | 說明 |
|------|------|------|
| CPU | 極低（< 0.5 核） | 純計算，無 GUI |
| 記憶體 | < 512MB | Python runtime |
| 磁碟 | > 1GB | 訊號日誌 + Docker images |
| 網路 | 需要 | Yahoo Finance API 取價 |

---

## 8. 快速啟動指令集

```bash
# 啟動（首次）
cd ~/code/tw-stock-signal
docker compose up -d

# 手動執行訊號產生
docker compose up --rm tw-stock-signal

# 查看日誌
docker compose logs -f

# 停止服務
docker compose down

# 重建（如修改 Dockerfile）
docker compose build --no-cache && docker compose up -d
```

---

*文件版本：v1.0 | 建立者：Coder Agent | 日期：2026-04-26*
