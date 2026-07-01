# db-lens-mcp

默认语言：中文  
English version: [README.en.md](README.en.md)

## 简介

`db-lens-mcp` 是一个给后端开发者和 AI 编程工具使用的数据库上下文 MCP 工具。

它让 Codex、Claude Code、Trae 等 AI 编程工具可以安全读取 MySQL / MariaDB 的表结构、索引、容量估算和 SELECT 执行计划，从而在写代码、改 SQL、排查潜在慢查询时获得数据库层上下文。

它不是通用 SQL 客户端，不提供任意 SQL 执行能力，也不会替你改表、建索引或修改数据。

## 应用场景

你可以把 `db-lens-mcp` 理解成给 AI 用的“只读数据库镜头”：AI 不需要登录数据库控制台，也不需要拿到完整连接串，就能通过 MCP 查看数据库上下文。

它主要用于：

- 查表结构：字段、类型、主键、注释。
- 查索引：索引字段、唯一性、顺序、类型和基数估算。
- 看表规模：行数估算、数据容量、索引容量。
- 分析 `SELECT`：查看执行计划，提示全表扫描、未走索引、扫描行数偏高等风险。
- 辅助 AI 写后端代码：在修改 DAO、Mapper、Repository、Service 或 SQL 前，让 AI 先理解真实数据库结构。

它不用于：

- 把它当作数据库管理工具或 SQL 控制台。
- 让 AI 自动执行 `INSERT`、`UPDATE`、`DELETE`、DDL 或运维操作。
- 替代 DBA 的完整慢查询诊断、容量规划或索引设计评审。
- 在第一版中作为完整团队 HTTP/SSE 服务使用；服务器部署目前只做基础预留。

## 安装

执行一条命令：

```bash
curl -fsSL https://raw.githubusercontent.com/MagicPelican/db-lens-mcp/master/scripts/install.sh | sh
```

安装完成后，按终端输出的下一步命令继续。正常情况下先检查安装：

```bash
db-lens doctor
```

查看可用命令：

```bash
db-lens help
```

## 配置流程

只需要三步。

### 1. 添加数据库

```bash
db-lens config add
```

按提示输入：

- profile 名称，例如 `local-dev`
- 数据库地址和端口
- database 名称，多个库用英文逗号分隔
- 用户名和密码

建议使用只读数据库账号。

### 2. 测试连接

```bash
db-lens config test local-dev
```

### 3. 接入 AI 客户端

Codex：

```bash
db-lens mcp install-codex
```

Claude Code：

```bash
db-lens mcp install-claude-code
```

Trae：

```bash
db-lens mcp install-trae
```

安装 MCP 配置后，重启对应客户端，再让 AI 使用 `db-lens` 查看数据库上下文。

如果你使用的 Agent 或 MCP 客户端还没有直接支持：

```bash
db-lens mcp handoff
```

把输出的整段内容发给对应 Agent，让它根据提示把 `db-lens` 加入自己的 MCP 配置。

## AI 可以使用的能力

MCP 工具只暴露固定白名单能力：

| 工具 | 作用 |
| --- | --- |
| `list_profiles` | 查看已配置的连接 profile，不返回密码 |
| `list_databases` | 查看当前 profile 可见的数据库 |
| `refresh_table_cache` | 刷新表到 database 的本地映射缓存 |
| `find_tables` | 通过表名或关键词查找表所在 database |
| `list_tables` | 查看指定 database 下的表列表 |
| `describe_table` | 查看表字段、主键和注释 |
| `list_indexes` | 查看表索引、唯一性、字段顺序、索引类型和基数估算 |
| `get_table_stats` | 查看行数估算、数据容量和索引容量 |
| `explain_select` | 对安全的单条 `SELECT` 执行工具内部生成的 `EXPLAIN` |
| `inspect_query` | 一次性返回 SQL 相关表结构、索引、统计、执行计划和基础风险提示 |

常用方式是直接让 AI 说明需求，例如：

```text
请用 db lens 检查 orders 表结构和索引。
```

```text
请用 db lens 分析这条 SQL 是否可能慢：
select * from orders where user_id = ? order by created_at desc limit 20
```

## 安全边界

`db-lens-mcp` 的安全设计重点是“只读上下文 + 白名单工具”。

- 不暴露通用 SQL 执行工具。
- 只允许分析单条 `SELECT`。
- 用户手写 `EXPLAIN` 会被拒绝；`EXPLAIN` 只能由工具内部生成。
- 多语句 SQL 会被拒绝。
- `INSERT`、`UPDATE`、`DELETE`、DDL、`CALL`、`LOAD DATA`、事务控制等语句会被拒绝。
- SQL 校验基于 MySQL 方言 AST 解析，不只依赖字符串前缀判断。
- 带占位符但未提供参数的 SQL，可以返回表结构和索引上下文，但不会为了执行 `EXPLAIN` 编造参数。
- MCP 返回给 AI 的错误信息会对常见密码、密钥和连接串做脱敏。
- `config list` 不展示密码、密文或 master key。

## 常用命令

```bash
db-lens doctor
db-lens help

db-lens config add
db-lens config update local-dev
db-lens config delete old-profile
db-lens config list
db-lens config test local-dev

db-lens cache refresh local-dev

db-lens mcp install-codex
db-lens mcp install-claude-code
db-lens mcp install-trae
db-lens mcp handoff

db-lens mcp config --client codex
db-lens mcp config --client claude-code
db-lens mcp config --client trae
db-lens mcp config
db-lens mcp run
```

说明：

- `db-lens mcp run` 是手动启动 MCP stdio server，主要用于排查问题。
- `db-lens mcp config` 只打印 MCP 配置片段，不自动写入客户端配置。
- `db-lens mcp install-*` 会尽量自动写入对应客户端配置。

## 高级配置

一般用户不需要手写配置文件。需要脚本化、Docker 或服务器预留部署时，可以使用配置文件和环境变量。

配置文件示例：

```toml
[profiles.local-dev]
driver = "mysql"
host = "127.0.0.1"
port = 3306
databases = ["app_db", "audit_db"]
username = "readonly_user"
password = "enc:v1:..."
connect_timeout_seconds = 5
read_timeout_seconds = 10
```

常用环境变量：

```text
DB_LENS_CONFIG_FILE=/path/to/config.toml
DB_LENS_MASTER_KEY=...
```

配置优先级：

```text
CLI 参数 > 环境变量 > config.toml > 默认值
```

交互式配置命令支持指定语言：

```bash
db-lens config add --language zh
db-lens config add --language en
```

`config add`、交互式 `config update` 和需要确认的 `config delete` 在未指定语言时，会先让用户选择中文或 English。

## 服务器部署状态

当前版本主路径是本地 MCP stdio 使用。服务器 / 团队部署方向只做基础预留：

- 支持通过环境变量指定配置文件和 master key。
- 后续可基于 Docker 运行。
- 完整 HTTP/SSE MCP Server、鉴权、多租户、审计和 Web 管理台不属于第一版范围。

## 排查问题

### 找不到 db-lens

重新执行安装命令，并保留终端输出。安装脚本应该打印可直接执行的 `db-lens` 路径；如果没有打印或打印后仍不可用，说明安装逻辑需要修复。

### MCP 客户端看不到 db-lens

先确认命令可用：

```bash
db-lens doctor
db-lens mcp config
```

然后重新运行对应客户端安装命令，并重启客户端：

```bash
db-lens mcp install-codex
```

### AI 找不到表

如果是刚新建或刚改名的表，刷新一次表缓存：

```bash
db-lens cache refresh local-dev
```

如果多个 database 有同名表，需要在请求中明确 database。

### SQL 没有执行 EXPLAIN

如果 SQL 使用 `?` 等占位符但没有提供参数，`db-lens-mcp` 不会猜测参数值，因此可能只返回表结构、索引和风险上下文，跳过 `EXPLAIN`。
