# 多库配置与表映射缓存

## 背景

原配置模型把一个 profile 绑定到单个 `database`，并保留 `default_profile`。这会让 AI 在缺少上下文时倾向猜测 profile 或 database，不适合一个后端项目访问多个业务库的场景。

## 上下文

- profile 应表示连接身份和环境，不应表示单个业务库。
- 一个连接身份可以配置多个 databases。
- AI 查询表结构时应通过表名定位 database；同名表或多 profile 场景不能猜测。

## 影响范围

- 配置模型和 TOML 保存格式。
- CLI `config add/update/list/delete/test/doctor`。
- MCP 工具接口和工具注册清单。
- MySQL 连接工厂和 EXPLAIN database 校验。
- 项目 README 与 `.harness/docs/` 设计文档。

## 实现摘要

- 移除 `default_profile` 产品语义。
- 将 `ProfileConfig.database` 改为 `ProfileConfig.databases`。
- 旧配置 `database = "app_db"` 读取时兼容迁移为 `databases = ["app_db"]`，保存时统一输出新格式。
- 增加 `TableLocatorService` 与 `table-cache.json`，缓存 `profile -> database -> tables` 和 `table -> databases` 映射。
- 表缓存默认 TTL 为 7 天；自动刷新只在表未命中且缓存过期或不存在时触发。
- 新增 MCP 工具：`list_profiles`、`refresh_table_cache`、`find_tables`。
- 新增 CLI 命令：`db-lens cache refresh <profile>`。
- `describe_table`、`list_indexes`、`get_table_stats`、`explain_select`、`inspect_query` 支持在缺少 database 时通过表映射缓存唯一定位；无法唯一定位时返回歧义。

## 验证结果

- `pytest -q` 通过，71 个测试全部通过。

## 文档影响

- README 已补充多库配置和表映射缓存说明。
- `.harness/docs/modules/configuration.md` 已移除默认 profile/database 设计。
- `.harness/docs/modules/mcp-tools.md` 已更新工具清单、输入约定和不猜测规则。
- `.harness/docs/modules/database-inspection.md` 和 `.harness/docs/architecture.md` 已补充 Table Mapping Cache。

## 风险与回退

- MCP 工具参数顺序对直接调用测试和手写客户端有影响；真实 MCP JSON 调用应按字段名传参。
- 回退方式是恢复单 `database` 字段、移除表缓存服务和新增 MCP 工具；旧配置兼容迁移逻辑可保留一段时间。

## 待确认项

- 同名表的后续兼容策略，例如项目绑定、用户确认缓存、SQL 关系辅助判断。
- 表缓存刷新策略是否需要自动定时、按需 TTL 或 CLI 显式刷新。
