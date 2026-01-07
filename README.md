# OnaniMemo-Chan ✨

简约的 Telegram 手冲记录机器人，健康手冲，从我做起！

## 功能 🚀

- 交互式手冲打卡（评分 / 时长 / 量 / 稠度）
- 时区设置与本地时间记录
- 周 / 月统计与常用时段统计

## 部署 📦

### 方式一：Docker（推荐） 🐳

```bash
docker run -d --name onani_memo_chan \
  -e BOT_TOKEN=your_bot_token \
  -v /path/to/data:/app/data \
  iam57ao/onani-memo-chan:latest
```

### 方式二：源码运行（uv） ⚡

1) 安装依赖

```bash
uv sync
```

2) 准备环境变量（示例）

```bash
set BOT_TOKEN=your_bot_token
set ONANI_DB_PATH=data/onani_memo.db
```

3) 启动

```bash
uv run python -m onani_memo_chan
```

## 机器人指令 🧭

- `/start` 欢迎与状态
- `/timezone` 选择时区
- `/do` 开始记录
- `/week` 最近 7 天统计
- `/month` 最近 30 天统计

## 配置 ⚙️

| 配置项 | 是否必填 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `BOT_TOKEN` | 是（与 `TELEGRAM_BOT_TOKEN` 二选一） | 无 | Telegram 机器人 Token |
| `TELEGRAM_BOT_TOKEN` | 是（与 `BOT_TOKEN` 二选一） | 无 | Telegram 机器人 Token |
| `ONANI_DB_PATH` | 否 | `data/onani_memo.db` | SQLite 路径 |
| `SESSION_TTL_MINUTES` | 否 | `30` | 会话过期分钟数 |
| `SESSION_CLEANUP_MINUTES` | 否 | `5` | 过期清理间隔分钟数 |
