# db-lens-mcp

Database context for AI-assisted backend development.

`db-lens-mcp` lets an AI coding tool safely inspect MySQL / MariaDB schema, indexes, table stats, and SELECT execution plans through MCP. It does not expose a general SQL execution tool.

## Quick Start

From the project directory:

```bash
./scripts/install.sh
db-lens doctor
db-lens config add
db-lens mcp config
```

Then paste the JSON printed by `db-lens mcp config` into your AI client's MCP settings.

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

The install script uses `uv tool install` and defaults to Python 3.11. If `uv` is missing, the script bootstraps it with:

```bash
python3 -m pip install --user --upgrade uv
```

For release or custom installs, set `DB_LENS_INSTALL_TARGET`:

```bash
DB_LENS_INSTALL_TARGET=db-lens-mcp ./scripts/install.sh
```

`DB_LENS_INSTALL_TARGET` can be a package name, Git URL, or local path.

## Useful Commands

```bash
db-lens doctor
db-lens config add
db-lens config list
db-lens config test local-dev
db-lens mcp config
db-lens mcp run
```

## Server Deployment

Server/team deployment is planned for a later phase. The current release path focuses on local MCP stdio usage.

## Development

Developer-only commands:

```bash
uv sync --extra dev
uv run db-lens doctor
uv run pytest
```

---

# 中文快速指南

`db-lens-mcp` 是一个面向后端 AI 开发的数据库上下文 MCP 工具。它可以让 AI 安全读取 MySQL / MariaDB 的表结构、索引、表统计和 SELECT 执行计划，但不提供通用 SQL 执行能力。

## 快速开始

在项目目录下执行：

```bash
./scripts/install.sh
db-lens doctor
db-lens config add
db-lens mcp config
```

然后把 `db-lens mcp config` 输出的 JSON 放到 AI 客户端的 MCP 配置中。

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
db-lens mcp config
db-lens mcp run
```

当前版本主要支持本地 MCP stdio 使用；服务器/团队部署会在后续阶段支持。
