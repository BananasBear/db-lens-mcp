# Roadmap

## 第一版目标

构建一个 Python 实现的数据库洞察 MCP 项目，用于后端 AI 开发过程中的数据库上下文辅助。项目重点解决 AI 开发时不了解表结构、索引设计、查询执行计划和慢查询风险的问题。

一句话目标：

> 本地安装后，用户通过一个交互式命令配置数据库，然后 AI 工具能通过 MCP 安全获取 MySQL 表结构、索引、表统计和 SELECT 执行计划。

## MVP 范围

- 支持 MySQL / MariaDB。
- 支持本地 MCP stdio 使用。
- 支持 CLI 配置、配置文件和环境变量覆盖。
- 支持敏感配置加密。
- 支持表结构、索引、行数/容量估算。
- 支持 SELECT EXPLAIN。
- 支持 SQL 相关表识别和基础风险提示。
- 工具只暴露项目需要的白名单能力，不提供通用 SQL 执行入口。
- 提供 Dockerfile，作为后续服务器部署的基础。

## 一期开发阶段

### 阶段 1：项目骨架

- Python 包结构。
- `pyproject.toml`。
- CLI 基础入口。
- MCP stdio 基础入口。
- 测试框架。

### 阶段 2：配置与加密

- `config add`。
- `config list`。
- `config test`。
- `doctor`。
- TOML 配置、`master.key`、密码加密。

### 阶段 3：MySQL 元数据能力

- 表列表。
- 表结构。
- 索引。
- 表统计信息。

### 阶段 4：SQL 安全与 EXPLAIN

- `sqlglot` 校验。
- 单条 SELECT 判断。
- EXPLAIN。
- 占位符缺少参数时跳过 EXPLAIN。

### 阶段 5：MCP 工具接入

- `describe_table`。
- `list_indexes`。
- `explain_select`。
- `inspect_query`。

### 阶段 6：测试和文档

- SQL 安全规则单元测试。
- 配置加密单元测试。
- MySQL 集成测试可选。
- README 使用说明。
- Dockerfile。

## 暂不做

- 自动执行数据库变更。
- 通用 SQL 客户端能力。
- 自动创建或修改索引。
- 完整 HTTP/SSE MCP Server。
- token 鉴权。
- 完整 Web 管理台。
- 完整企业用户体系、多租户和复杂审计报表。
- `.dmg`、`.pkg`、`.msi` 等桌面安装器。

## 后续方向

- PostgreSQL 支持。
- 更完整的 SQL 风险分析。
- 索引建议和慢查询诊断报告。
- HTTP/SSE MCP Server。
- 团队服务器模式的认证、审计和权限隔离增强。

## 待确认

- 第一版是否需要 Docker Compose 示例。
- 第一版是否需要自动生成 AI 客户端配置。
