# mcp handoff design

## 背景

当前项目已经支持两类 MCP 客户端接入方式：

- 对已支持客户端，使用 `db-lens mcp install-*` 直接安装。
- 对手动配置场景，使用 `db-lens mcp config` 输出配置片段。

这两类能力都还缺一个“面向其他 Agent 的交付出口”。用户希望拿到一段可以直接发给其他 Agent 的文本，让 Agent 自己把 `db-lens` 配置进它所使用的 MCP 客户端，而不是让用户自己解释配置含义。

## 目标

- 新增一个明确面向“其他 Agent”的 CLI 命令。
- 输出内容默认是自然语言提示词，用户可以直接整段复制给其他 Agent。
- 输出中携带通用 MCP server 配置，复用当前项目已经存在的 `command` / `args` / `env` 结构。
- 不假设目标 Agent 的具体配置文件路径、客户端品牌或宿主格式。
- 不暴露数据库 password、master key、连接串等敏感信息。

## 非目标

- 不替代 `db-lens mcp config` 现有的纯配置片段输出。
- 不为未知客户端直接改本地配置文件。
- 不新增新的 MCP server 配置语义。
- 不在一期支持多种 handoff 模板、富格式、Markdown/HTML 多渲染目标。

## CLI 设计

新增命令：

```bash
db-lens mcp handoff
```

一期复用现有 MCP 配置相关参数：

- `--server-name`：默认 `db-lens`
- `--command`：默认自动解析 `db-lens`
- `--config-file`：可选，映射为 `DB_LENS_CONFIG_FILE`

一期默认只输出文本，不引入新的输出格式参数。命令定位是“生成一段发给 Agent 的安装说明”，而不是机器接口。

## 输出设计

输出是一段完整自然语言提示词，包含三部分：

1. 任务说明
2. 通用 MCP 配置 JSON
3. 安装完成后的确认要求

一期固定输出中文文本，不引入 `--language` 参数。

默认文本结构：

```text
请把下面这个 MCP server 配置到你当前使用的 MCP 客户端中，并完成安装。

要求：
- server 名称保持为 db-lens
- 使用下面的 command、args 和 env
- 不要修改配置中的字段名
- 如果你的客户端不支持自动安装，请把下面的 JSON 配置粘贴到对应的 MCP 配置位置
- 安装完成后，确认你已经能看到 db-lens 提供的 MCP tools

配置：
{
  "mcpServers": {
    "db-lens": {
      "command": "/path/to/db-lens",
      "args": ["mcp", "run"],
      "env": {
        "DB_LENS_CONFIG_FILE": "/path/to/config.toml"
      }
    }
  }
}
```

如果没有传入 `--config-file`，则 `env` 字段整体省略，而不是输出空对象。

## 架构与复用

`mcp handoff` 不单独维护 server 配置拼装逻辑，而是直接复用现有基础 helper：

- `_resolve_db_lens_command`
- `_base_server_config`

新增一个面向 handoff 的字符串渲染 helper，例如：

- `_handoff_message(server_name, command, config_file)`

这样可以保证：

- `install-*`
- `mcp config`
- `mcp handoff`

三类入口底层使用同一份 server 配置数据，避免字段漂移。

## 数据流

命令执行流程：

1. 解析 CLI 参数。
2. 用 `_resolve_db_lens_command` 得到可执行 command。
3. 用 `_base_server_config` 构造通用 server 配置对象。
4. 把配置对象嵌入 handoff 文本模板。
5. 输出最终文本。

该流程不访问客户端配置文件，不调用外部客户端 CLI，不写磁盘。

## 错误处理

- 如果 `db-lens` 可执行路径无法解析，沿用当前 `ConfigurationError` 文案和退出行为。
- 如果 `--server-name` 或 `--command` 为空，沿用现有 CLI 参数校验。
- 输出中不得包含 password、master key、完整连接串。

## 测试设计

需要新增 CLI 测试覆盖：

- `db-lens mcp handoff` 默认输出包含自然语言说明。
- 输出中包含 `mcpServers`、`command`、`args`。
- 传入 `--config-file` 时输出包含 `DB_LENS_CONFIG_FILE`。
- 未传入 `--config-file` 时输出不包含 `DB_LENS_CONFIG_FILE`，也不输出空 `env`。
- 输出不包含 `password`、`master_key`、`mysql://` 等敏感词。

## 文档影响

需要同步更新：

- `README.md`
- `scripts/install.sh` 的 next steps 说明
- `.harness/docs/modules/configuration.md`
- `.harness/docs/modules/deployment.md`
- `.harness/changes/` 变更记录

## 风险与取舍

- `handoff` 输出的是“给 Agent 的说明文本”，不是标准协议；不同 Agent 的执行效果取决于对方是否具备 MCP 配置与本地文件编辑能力。
- 该命令的价值在于降低用户解释成本，而不是保证所有未知 Agent 都能自动安装成功。
- 保持 `handoff` 与 `config` 分离，可以避免纯配置输出被自然语言污染，也能让命令语义清晰。

## 结论

一期采用最小实现：

- 新增 `db-lens mcp handoff`
- 默认输出中文自然语言提示词
- 内嵌通用 JSON MCP 配置
- 与现有 `mcp config`、`install-*` 共享底层配置生成逻辑

该方案能补齐“其他 Agent”场景，又不会把项目扩成新的客户端适配层。
