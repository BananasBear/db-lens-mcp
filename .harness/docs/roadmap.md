# Roadmap

## 第一版目标

构建一个 Python 实现的数据库洞察 MCP 项目，用于后端 AI 开发过程中的数据库上下文辅助。项目重点解决 AI 开发时不了解表结构、索引设计、查询执行计划和慢查询风险的问题。

一句话目标：

> 本地安装后，用户通过一个交互式命令配置数据库，然后 AI 工具能通过 MCP 安全获取 MySQL 表结构、索引、表统计和 SELECT 执行计划。

本地用户不需要理解 Python 版本、虚拟环境或依赖管理；这些细节优先由安装脚本屏蔽。Docker 和团队服务器部署放到后续阶段。

## MVP 范围

- 支持 MySQL / MariaDB。
- 支持本地 MCP stdio 使用。
- 支持 CLI 配置、配置文件和环境变量覆盖。
- 支持敏感配置加密。
- 支持表结构、索引、行数/容量估算。
- 支持 SELECT EXPLAIN。
- 支持 SQL 相关表识别和基础风险提示。
- 工具只暴露项目需要的白名单能力，不提供通用 SQL 执行入口。
- 提供远程一键安装脚本，作为普通用户本地安装主路径；源码安装只作为维护者路径。
- 服务器部署和 Dockerfile 放到后续阶段。

## 一期开发阶段

### 阶段 1：项目骨架

- Python 包结构。
- `pyproject.toml`。
- CLI 基础入口。
- MCP stdio 基础入口。
- 测试框架。

### 阶段 2：配置与加密

- `config add`。
- `config update`。
- `config delete`。
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
- 一键安装脚本。
- MCP 客户端配置生成命令。

### 阶段 7：本地安装与接入收尾

- Windows 本地安装主路径：提供 PowerShell 安装脚本、Windows PATH 刷新提示、Windows 下配置文件与客户端配置路径说明。
- 面向更多 Agent 的 MCP 接入：在保留 Codex 自动安装的基础上，补充统一的 MCP 客户端配置生成 / 安装流程，降低不同本地 Agent 的接入成本。
- 更人性化的安装引导与中文支持：优先补齐 `config update`、`config delete`，并优化安装完成后的 next steps、`doctor`、`config add`、`config update`、`config delete`、README 和常见错误提示，让普通用户按提示即可完成配置与接入。

## 当前完成状态

- 项目骨架、CLI、MCP stdio 入口已实现。
- 本地 TOML 配置、`master.key`、Fernet 密码加密已实现。
- 当前配置主路径已覆盖 `config add`、`config update`、`config delete`、`config list`、`config test`。
- `config add`、`config update`、`config delete` 已支持 `--language zh|en`，未显式指定时会在交互式主路径先选择语言。
- MySQL / MariaDB 连接工厂和固定 `information_schema` 元数据查询已实现。
- SQL 安全校验、单条 SELECT 限制、工具内部 EXPLAIN 已实现。
- `inspect_query` 已组合返回表结构、索引、表统计、EXPLAIN、风险提示和 metadata 错误。
- 默认从 GitHub 安装源安装的远程安装脚本和 `db-lens mcp config` 客户端配置生成命令已实现。
- 当前本地安装主路径仍偏向 macOS / Linux shell + Codex 场景，Windows 安装、更多 Agent 的 MCP 接入、更加人性化的中文引导仍待补齐。
- 当前验证命令：`rtk sh -n scripts/install.sh`、`rtk python -m pytest`、`rtk python -m compileall src tests`。
- 发布前必须验证 README 中的 raw GitHub 安装 URL 返回 `200 OK`。

## 当前收尾重点

- 任务 1：补齐 Windows 安装主路径。目标是让普通 Windows 用户无需理解 Python、虚拟环境或手动配 PATH，也能完成安装并拿到明确下一步。
- 任务 2：把 MCP 接入从“仅支持 Codex 自动安装”提升到“支持更多本地 Agent 的统一接入”。目标是保留 `install-codex`，同时补充可扩展的多客户端安装 / 配置出口。
- 任务 3：把配置流程从工程化说明提升为傻瓜式引导，重点补齐中文 / 英文引导模式。目标是让安装脚本、CLI 和 README 在成功路径与失败路径上都能告诉用户“下一步做什么”，并补齐中文主路径支持。

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
- PyPI 包发布后是否把默认安装目标从 GitHub Git URL 切换为包名。
- 仓库公开发布后，重新验证一行安装命令端到端可用。
- 第一版优先覆盖哪些本地 Agent / MCP 客户端，以及哪些客户端只提供配置生成、哪些提供自动安装。
- Windows 安装主路径是否只提供 PowerShell 脚本，还是同时补充 `winget` / Scoop / Chocolatey 方案。
- `config update` / `config delete` 的最终命令名是否保持当前规划命名，还是调整为 `edit` / `remove`。
