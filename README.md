# JZT Dashboard V2

京准通数据看板第二版，支持历史数据日期选择和可读性改进。

**在线地址**：https://sevenlucas7.github.io/JZT-Dashboard-v2/

---

## V1 vs V2 对比

| 特性 | V1 | V2 |
|------|----|----|
| 历史数据选择 | ❌ | ✅ 动态加载 |
| 可读性改进 | 基础 | ✅ 字号加大、间距优化 |
| 环比展示 | ✅ | ✅ 保留 |

---

## 本地仓库

```
~/JZT-Dashboard-v2/
├── data/                  ← split.json 历史数据
│   ├── dates_index.json   ← 可用日期索引（V2 专用）
│   └── *_split.json       ← 历史 split 文件
├── index.html             ← V2 看板首页
├── html/index.html        ← 备份副本
├── jzt_dashboard_renderer_v2.py  ← V2 renderer
├── jzt_sync_v2.py         ← V2 sync 脚本
└── jzt_dashboard_renderer.py     ← V1 renderer（复用）
```

---

## Hermes Cron 同步

V2 有独立的 sync 脚本，需要在 Hermes cron 中添加调用：

```bash
# V2 sync（推荐每2小时运行）
python3 ~/JZT-Dashboard-v2/jzt_sync_v2.py \
    --data-dir ~/JZT报数/data \
    --output-dir ~/JZT-Dashboard-v2
```

**建议 cron 安排**（与 V1 预计算配合）：

| 时间 | 任务 |
|------|------|
| 每2小时 | `jzt_pipi_compute.sh` → 生成 V1 artifacts |
| 每2小时 | `jzt_sync_v2.py` → 同步 V2 数据 + 生成 index.html |

---

## 日期选择器说明

V2 使用 JavaScript 动态加载历史数据：

1. 页面加载时读取 `data/dates_index.json`
2. 用户选择日期后，fetch 对应的 `data/{date}_{slot}_split.json`
3. 动态更新页面 KPI、账户卡片、SKU 表格

**可用日期格式**：`YYYY-MM-DD`，每天取最后一份数据（如 2357）

---

## 本地开发测试

```bash
# 手动运行 V2 sync
cd ~/JZT-Dashboard-v2
python3 jzt_sync_v2.py --data-dir ~/JZT报数/data --output-dir ~/JZT-Dashboard-v2

# 本地查看（需启动 HTTP 服务器）
cd ~/JZT-Dashboard-v2
python3 -m http.server 8080
# 浏览器打开 http://localhost:8080
```

---

## GitHub 操作

```bash
cd ~/JZT-Dashboard-v2

# 推送到 GitHub（首次设置 remote）
git remote set-url origin https://github.com/sevenlucas7/JZT-Dashboard-v2.git
git push origin main

# 开启 GitHub Pages（仅首次）
curl -X POST -H "Authorization: token $GITHUB_TOKEN" \
  -d '{"source":{"branch":"main","path":"/"}}' \
  "https://api.github.com/repos/sevenlucas7/JZT-Dashboard-v2/pages"
```

---

## 文件说明

### jzt_sync_v2.py

- 从 V1 数据目录（`~/JZT报数/data`）读取 split.json
- 生成 `dates_index.json`（只保留日期格式正确的文件，跳过 `latest_split.json`）
- 复制所有 split.json 到 V2 的 data 目录
- 调用 V2 renderer 生成 `index.html`

### jzt_dashboard_renderer_v2.py

- 复用 V1 renderer 的所有函数
- 新增 V2 专用 CSS（可读性改进）
- 新增日期选择器 HTML + JavaScript
- 动态数据加载逻辑

---

## 已知问题

- suggestions 生成使用 V1 的 `jzt_deliver_feishu.py`，需确认参数兼容
