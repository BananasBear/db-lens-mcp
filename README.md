# db-lens-mcp

Database context for AI-assisted backend development.

`db-lens-mcp` lets an AI coding tool safely inspect MySQL / MariaDB schema, indexes, table stats, and SELECT execution plans through MCP. It does not expose a general SQL execution tool.

## Quick Start

After release, users install with one command:

```bash
curl -fsSL https://raw.githubusercontent.com/MagicPelican/db-lens-mcp/master/scripts/install.sh | sh
```

When the installer finishes, follow the `Next steps` printed in your terminal. The normal flow is:

```bash
db-lens help
db-lens config add
db-lens mcp install-codex
```

Release requirement: the install URL above must return `200 OK` before this README is used as public user documentation.

## What The AI Can Use

- `list_databases`: list visible databases.
- `list_tables`: list tables in a database.
- `describe_table`: read table columns, primary key, and comments.
- `list_indexes`: read table indexes.
- `get_table_stats`: read estimated row count and size metadata.
- `explain_select`: run tool-generated `EXPLAIN` for a safe single SELECT.
- `inspect_query`: return related table schema, indexes, stats, EXPLAIN, and risk hints for a safe SELECT.

## Safety

- No generic SQL execution tool is exposed.
- Only a single SELECT can be inspected.
- User-written `EXPLAIN`, multi-statement SQL, INSERT, UPDATE, DELETE, DDL, CALL, and LOAD DATA are blocked.
- Database passwords are encrypted in the local config file.
- Error messages returned to MCP clients are redacted for common password, key, and connection-string patterns.

## Install Notes

The install script installs `db-lens` with `uv tool install` and defaults to Python 3.11. If `uv` is missing, the script installs it automatically.

If `db-lens` is not found after installation, open a new terminal or run:

```bash
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
```

## Useful Commands

```bash
db-lens doctor
db-lens config add
db-lens config list
db-lens config test local-dev
db-lens mcp install-codex
db-lens mcp config --client codex
db-lens mcp config
db-lens mcp run  # manual MCP server start, mainly for troubleshooting
```

## Server Deployment

Server/team deployment is planned for a later phase. The current release path focuses on local MCP stdio usage.

## Development

Source checkout install is only for maintainers and internal preview:

```bash
git clone https://github.com/MagicPelican/db-lens-mcp.git
cd db-lens-mcp
DB_LENS_INSTALL_TARGET=. ./scripts/install.sh
uv sync --extra dev
uv run db-lens doctor
uv run pytest
```

---

# 中文快速指南

`db-lens-mcp` 是一个面向后端 AI 开发的数据库上下文 MCP 工具。它可以让 AI 安全读取 MySQL / MariaDB 的表结构、索引、表统计和 SELECT 执行计划，但不提供通用 SQL 执行能力。

## 快速开始

发布后，用户只需要复制并执行一条命令：

```bash
curl -fsSL https://raw.githubusercontent.com/MagicPelican/db-lens-mcp/master/scripts/install.sh | sh
```

安装完成后，按照终端里打印的 `Next steps` 继续操作。正常流程是：

```bash
db-lens help
db-lens config add
db-lens mcp install-codex
```

发布要求：公开使用本文档前，上面的安装地址必须返回 `200 OK`。

## AI 可以使用的能力

- 查看数据库列表。
- 查看表列表。
- 查看表字段、主键和注释。
- 查看表索引。
- 查看表行数和容量估算。
- 对安全的单条 SELECT 执行工具内部生成的 `EXPLAIN`。
- 使用 `inspect_query` 一次性获取 SQL 相关表结构、索引、统计、执行计划和风险提示。

## 安全边界

- 不暴露通用 SQL 执行工具。
- 只允许分析单条 SELECT。
- 阻止用户手写 `EXPLAIN`、多语句 SQL、INSERT、UPDATE、DELETE、DDL、CALL、LOAD DATA 等高风险语句。
- 本地配置文件中的数据库密码会加密保存。
- MCP 返回给 AI 的错误信息会做敏感信息脱敏。

## 常用命令

```bash
db-lens doctor
db-lens config add
db-lens config list
db-lens config test local-dev
db-lens mcp install-codex
db-lens mcp config --client codex
db-lens mcp config
db-lens mcp run  # 手动启动 MCP server，主要用于排查问题
```

当前版本主要支持本地 MCP stdio 使用；服务器/团队部署会在后续阶段支持。

源码安装只面向维护者和内部预览：

```bash
git clone https://github.com/MagicPelican/db-lens-mcp.git
cd db-lens-mcp
DB_LENS_INSTALL_TARGET=. ./scripts/install.sh
```
