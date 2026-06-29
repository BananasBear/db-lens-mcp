# MCP Read-Only Tool Annotations

## 背景

本地使用 Codex 接入 db-lens MCP 时，只读查询类工具每次调用可能触发客户端审批弹窗。MCP 工具可以通过 annotations 向客户端声明工具风险属性，帮助客户端做更友好的展示和判断。

## 上下文

项目一期工具表面是固定白名单能力，大多数工具只读取配置或数据库元数据；`explain_select` 和 `inspect_query` 只允许单条 SELECT 分析或由工具内部执行 EXPLAIN。

`refresh_table_cache` 会刷新本地表映射缓存，虽然数据库侧仍是低风险读取，但会修改本地缓存状态，因此不标记为纯只读工具。

## 影响范围

- MCP 工具注册元数据。
- MCP client 看到的工具 annotations。
- 不改变工具入参、出参和数据库访问逻辑。

## 实现摘要

- 为纯查询/分析工具统一添加 `readOnlyHint=True`、`destructiveHint=False`、`idempotentHint=True`、`openWorldHint=True`。
- annotations 使用协议字段字典传入，避免顶层导入 `mcp.types.ToolAnnotations` 对部分本地安装或 IDE 解析不稳定。
- `refresh_table_cache` 保持无只读 annotations。
- 增加测试覆盖，确保只读工具 annotations 不被移除。

## 验证结果

- `.venv/bin/python` 直接执行 `tests/test_mcp_server.py` 中全部 `test_` 函数通过。
- `.venv/bin/python -m py_compile src/db_lens_mcp/mcp/tools.py tests/test_mcp_server.py` 通过。
- 已验证 FastMCP 会将 dict annotations 转换为 MCP `ToolAnnotations` 输出。
- 未运行 `pytest` 命令：当前 `.venv` 缺少 `pytest`，联网安装/同步 dev 依赖的授权未通过。

## 文档影响

已有 MCP 工具设计和安全边界仍然适用。本次仅补充协议元数据，不改变能力范围。

## 风险与回退

风险：客户端可能仍根据自身审批策略弹窗，annotations 只是工具侧提示，不保证自动免审批。

回退：移除工具注册上的 annotations 即可恢复原行为。

## 待确认项

后续是否要为 `refresh_table_cache` 使用非只读但非破坏性的 annotations，需要结合目标客户端行为再确认。
