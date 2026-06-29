# Architecture Plan

## 已确认目标

第一版构建一个 Python 实现的数据库洞察 MCP 项目，面向后端 AI 开发过程。项目用于补足 AI 无法感知数据库层上下文的问题，让 AI 在开发时可以了解表结构、索引设计、数据量估算、查询执行计划和潜在慢查询风险。

## 运行模式

- 本地模式：开发者本机运行 MCP stdio 服务，AI 工具通过 stdio 调用。
- 服务器模式：一期只通过 Dockerfile 做基础预留；完整 HTTP/SSE 团队服务放到后续迭代。

## 分层架构

```text
src/db_lens_mcp/
  cli/                 # 命令行入口：配置、诊断、启动 MCP
  mcp/                 # MCP stdio 工具入口和协议适配
  application/         # 应用服务：组织业务流程
  domain/              # 领域模型和规则：SQL 安全、风险提示、核心对象
  infrastructure/      # 外部适配：MySQL、配置、加密、日志
  config/              # 配置加载、覆盖、校验
```

## 建议目录

```text
src/db_lens_mcp/
  __init__.py
  cli/
    main.py
  mcp/
    server.py
    tools.py
    schemas.py
  application/
    database_inspection_service.py
    query_inspection_service.py
  domain/
    models.py
    sql_guard.py
    risk_rules.py
  infrastructure/
    mysql/
      metadata_reader.py
      explain_runner.py
      connection_factory.py
    secrets/
      secret_store.py
    config/
      config_loader.py
      config_models.py
  logging.py
  errors.py
```

该目录是一期建议结构，实际实现时可按复杂度轻微合并，但不能破坏 MCP 入口、应用服务、领域规则和基础设施的边界。

## 模块职责

### `cli/`

- 提供命令行入口。
- 负责 `config add`、`config list`、`config test`、`doctor`、`mcp run` 等命令。
- 不直接实现数据库元数据读取和 SQL 风险判断。

### `mcp/`

- 提供 MCP stdio 服务入口。
- 注册固定 MCP 工具。
- 负责 MCP 输入输出转换和基础参数校验。
- 不直接拼接 SQL，不直接调用数据库驱动。

### `application/`

- 负责编排业务流程。
  - `database_inspection_service.py` 组织表结构、索引、统计信息读取。
  - `table_locator_service.py` 维护表到 database 的映射缓存，并在工具缺少 database 时做唯一解析或返回歧义。
  - `query_inspection_service.py` 组织 `inspect_query` 主流程：SQL 安全校验、识别相关表、读取表上下文、执行 EXPLAIN、生成风险提示和 AI 摘要。
- 不处理底层数据库连接细节。

### `domain/`

- 存放项目核心领域对象和规则。
- `models.py` 定义连接配置、表结构、索引、执行计划、风险提示等对象。
- `sql_guard.py` 判断是否为单条 SELECT，并拒绝危险 SQL。
- `risk_rules.py` 根据 EXPLAIN 和表统计信息生成基础风险提示。
- 不依赖 MCP SDK、CLI 框架或 MySQL 驱动。

### `infrastructure/`

- 封装外部系统和技术细节。
- `mysql/metadata_reader.py` 读取 MySQL/MariaDB 元数据。
- `mysql/explain_runner.py` 只执行经过安全校验的 EXPLAIN。
- `mysql/connection_factory.py` 创建数据库连接。
- `secrets/secret_store.py` 处理本机 `master.key` 和环境变量密钥；系统钥匙串作为后续增强，不作为一期主路径。
- `config/` 负责配置文件加载、环境变量覆盖和配置模型。

## 设计原则

- MCP 协议入口和数据库核心能力分离。
- 本地模式和服务器模式复用同一套核心能力。
- 数据库访问层只暴露项目需要的白名单能力，不提供通用 SQL 执行入口。
- 不提供默认 profile 或默认 database 产品语义；缺少上下文时只能通过唯一配置、显式参数或表映射缓存唯一命中解析。
- 所有用户输入 SQL 必须经过安全校验。
- SQL 安全判断放在领域层，数据库执行层只接收已校验过的请求。
- MySQL/MariaDB 适配先做具体实现，不提前设计复杂多数据库插件系统。
- 第一版不做完整企业平台，不引入用户体系、多租户管理台或复杂审计报表。

## 关键调用链

### `inspect_query`

```text
MCP tool
  -> QueryInspectionService
    -> SqlGuard
    -> MetadataReader
    -> ExplainRunner
    -> RiskRules
  -> MCP response
```

### `describe_table`

```text
MCP tool
  -> DatabaseInspectionService
    -> MetadataReader
  -> MCP response
```

## 不做事项

- 不做通用 SQL 客户端。
- 不做自动改表、自动建索引、自动修复 SQL。
- 不做深层 repository/service/manager 套娃。
- 不做复杂插件系统。
- 不为了未来数据库类型提前抽象所有方言。
- 不让 MCP 工具层直接访问数据库驱动。

## 待确认

- Python MCP SDK 的具体选择。
- 连接池、并发和超时的默认参数。
