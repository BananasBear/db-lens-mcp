# Change Record

## 背景

项目此前只提供 `db-lens mcp install-codex` 自动写入 Codex 配置。随着本地 Agent 使用场景扩展，需要补齐更多主流客户端的安装入口，并为未直接支持的 Agent 提供可转发的通用安装提示词，避免用户手写或解释 MCP 配置。

## 上下文

- 当前本地发布主路径仍是安装脚本 + `db-lens config add`。
- 仓库中已存在 `db-lens mcp config` 手动输出能力，以及 `install-codex` 的自动安装能力。
- 本次扩展覆盖 Claude Code、Trae，以及面向其他 Agent 的通用 handoff 输出。

## 影响范围

- CLI MCP 客户端安装命令。
- CLI MCP 手动配置输出格式。
- CLI 面向其他 Agent 的通用 handoff 输出。
- README、安装脚本和部署/配置文档中的用户接入说明。

## 实现摘要

- 新增 `db-lens mcp install-claude-code`，调用 Claude Code 原生 `claude mcp add-json` 安装本地 stdio server。
- 新增 `db-lens mcp install-trae`，调用 Trae 原生 `trae --add-mcp` 安装本地 stdio server。
- 扩展 `db-lens mcp config --client`，新增 `claude-code` 和 `trae` 两种手动配置输出。
- 新增 `db-lens mcp handoff`，输出中文自然语言提示词，并内嵌通用 `mcpServers` JSON，供用户直接转发给其他 Agent。
- 保持 `install-codex` 逻辑不变，只做 helper 抽取和共用配置生成。
- 更新 README、`scripts/install.sh`、`.harness/docs/modules/deployment.md`、`.harness/docs/modules/configuration.md` 的客户端接入说明。

## 验证结果

- 使用 Python 3.10 对 `src/db_lens_mcp/cli/main.py` 和 `tests/test_cli.py` 执行 `py_compile`，语法通过。
- 通过脚本级验证确认：
  - Claude Code 输出的 server payload 为 `type=stdio + command/args/env`。
  - Trae 输出的 server payload 为 `name + command/args/env`。
  - `install-claude-code` 和 `install-trae` 会调用预期的外部 CLI 参数。
  - `mcp handoff` 输出包含预期中文提示词与通用 `mcpServers` JSON。
- 未完成完整 `pytest` 回归：
  - 本机缺少项目要求的 Python 3.11 运行时。
  - 可用的 Python 3.8/3.10 环境与项目依赖不匹配，无法在本机完整跑通测试矩阵。

## 文档影响

- README 已补充 Claude Code / Trae 安装命令、handoff 命令与手动配置输出示例。
- 安装脚本 next steps 已从单一 Codex 提示扩展为多个已支持客户端，并增加 handoff 兜底路径。
- 部署与配置文档已同步更新“已支持客户端自动安装 + 其他 Agent 使用 handoff”的表述。

## 风险与回退

- Claude Code 和 Trae 当前依赖各自原生 CLI 的行为稳定；若客户端后续修改命令参数或输出格式，`install-*` 需要同步调整。
- `handoff` 只是对 Agent 的自然语言交付文本，不保证所有未知客户端都能自动安装成功。
- 回退方式直接：移除新增命令，并保留 `install-codex` + `mcp config` 的原有路径。

## 待确认项

- 是否为 `mcp handoff` 增加 `--language zh|en`。
- 是否为 Claude Code / Trae 增加更细的作用域或多实例安装选项。
