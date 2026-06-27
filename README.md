# db-lens-mcp

面向后端 AI 开发过程的数据库上下文 MCP 工具。

一期目标：本地安装后，用户通过交互式命令配置 MySQL / MariaDB 连接，然后 AI 工具通过 MCP 安全获取表结构、索引、表统计和 SELECT 执行计划。

## 当前状态

项目处于骨架阶段，尚未实现数据库连接、配置加密和 MCP 工具真实逻辑。

## 本地开发

```bash
uv sync --extra dev
uv run db-lens doctor
uv run db-lens mcp run
uv run pytest
```

## 一期安全边界

- 不提供通用 SQL 执行入口。
- 只允许工具内部对单条 SELECT 执行 EXPLAIN。
- 不执行 INSERT、UPDATE、DELETE、DDL、CALL、LOAD DATA 等高风险语句。
- 配置文件不得保存明文数据库密码。
