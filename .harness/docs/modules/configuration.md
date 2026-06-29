# Configuration Spec

## 设计目标

配置能力必须降低本地使用门槛。普通用户安装后，应主要通过交互式 CLI 完成数据库配置、密码加密、连通性测试和 MCP 客户端接入提示，不要求手写配置文件。

## 一期方案

- 配置格式：TOML。
- 默认配置文件：`~/.db-lens/config.toml`。
- 默认本机密钥文件：`~/.db-lens/master.key`。
- 本地使用：CLI 配置向导作为主路径。
- 服务器 / Docker：支持环境变量和挂载配置文件。
- 系统钥匙串：一期不作为主路径，后续增强。

## 傻瓜式 CLI 流程

### 添加配置

```bash
db-lens config add
```

交互流程：

1. 未显式传入 `--language` 时，先选择语言模式，支持 `中文` 和 `English`。
2. 输入 profile 名称，例如 `local-dev`。
3. 输入 host，默认 `127.0.0.1`。
4. 输入 port，默认 `3306`。
5. 输入 databases，多个库用英文逗号分隔。
6. 输入 username。
7. 安全输入 password，不回显。
8. 自动生成或复用 master key。
9. 加密 password 并写入 config.toml。
10. 自动执行一次连接测试。
11. 输出下一步命令，用户优先通过 `db-lens mcp install-codex`、`db-lens mcp install-claude-code` 或 `db-lens mcp install-trae` 自动写入已支持客户端的 MCP 配置；对其他未直接支持的 Agent，使用 `db-lens mcp handoff` 输出通用安装提示词；`db-lens mcp config` 仅作为手动配置备用。

### 修改配置

```bash
db-lens config update local-dev
```

交互流程：

1. 选择语言模式，支持 `中文` 和 `English`。
2. 读取已有 profile 当前配置并展示可修改项。
3. 逐项确认是否修改 `driver`、`host`、`port`、`databases`、`username`、`password` 等字段。
4. 未修改的字段保持原值。
5. 如修改 password，继续使用 master key 加密后写回 config.toml。
6. 默认执行一次连接测试。
7. 输出下一步命令，例如重新执行 `db-lens config test local-dev` 或继续安装 MCP 客户端配置。

### 删除配置

```bash
db-lens config delete local-dev
```

交互流程：

1. 选择语言模式，支持 `中文` 和 `English`。
2. 展示将要删除的 profile 基本信息，不展示密码或密文。
3. 要求用户二次确认，避免误删。
4. 删除对应 profile。
5. 输出下一步命令，例如 `db-lens config list` 或重新执行 `db-lens config add`。

### 查看配置

```bash
db-lens config list
```

只展示 profile、host、port、databases、username，不展示密码、密文和 master key。

### 测试配置

```bash
db-lens config test local-dev
```

检查：

- 配置是否存在。
- master key 是否可用。
- 密码是否可解密。
- 数据库是否能连接。
- 基础元数据查询是否可用。

不检查数据库账号权限是否过大。

### 刷新表映射缓存

```bash
db-lens cache refresh local-dev
```

刷新指定 profile 下已配置 databases 的表名映射。自动刷新只在“表未找到且缓存已过期或不存在”时触发；默认 TTL 为 7 天。不会定时刷新，不会在缓存命中时刷新。

### 语言模式

- `config add`、`config update`、`config delete` 作为主要交互式配置命令，需要支持 `中文` 和 `English` 两种引导模式。
- 中文模式下，只把引导文案、确认语、成功/失败提示和下一步建议切换为中文。
- `profile`、`driver`、`host`、`port`、`databases`、`username`、`password` 等专业名词和配置字段名保持英文，不做翻译。
- 支持显式参数 `--language zh` / `--language en`；未显式指定时，再通过交互式选择语言。
- 当前范围内，`config add`、交互式 `config update` 和需要确认的 `config delete` 会在主流程开始前先选择语言；纯 CLI 参数调用默认继续使用英文输出。
- `config list`、`config test` 和 `doctor` 的输出可逐步补充双语或中文引导，但第一优先级是补齐 `add` / `update` / `delete` 的交互流程。

### 诊断

```bash
db-lens doctor
```

检查：

- Python 运行环境。
- 配置文件是否存在。
- 配置文件和 master key 文件权限是否合理。
- 配置的 profile 是否可用。
- 配置的 databases 连通性。

## TOML 示例

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

配置文件不得保存明文数据库密码。

## 密钥策略

### 本地默认

- 首次 `config add` 时生成 `~/.db-lens/master.key`。
- 使用 master key 加密数据库密码。
- `config.toml` 只保存密文。
- master key 文件建议权限为 `0600`。

### 环境变量优先

如果存在 `DB_LENS_MASTER_KEY`，优先使用该环境变量解密配置。

适用场景：

- Docker。
- CI。
- 服务器部署。
- 不希望落盘 master key 的环境。

### 配置文件路径覆盖

支持通过环境变量指定配置文件：

```text
DB_LENS_CONFIG_FILE=/path/to/config.toml
```

## 配置覆盖优先级

```text
CLI 参数 > 环境变量 > config.toml > 默认值
```

常用环境变量：

- `DB_LENS_CONFIG_FILE`
- `DB_LENS_MASTER_KEY`

## 敏感信息规则

- 配置文件不保存明文密码。
- 日志不打印 password、master key、完整连接串。
- MCP 返回结果不包含密码、密钥或完整连接串。
- `config list` 不展示密文。
- 错误消息可以说明“解密失败”或“密钥不可用”，但不得输出敏感值。

## 不做事项

- 一期不做系统钥匙串默认主路径。
- 一期不做 Web 管理配置。
- 一期不做云端配置同步。
- 一期不做 Vault / KMS / Secret Manager 集成。
- 一期不做多用户配置权限模型。

## 已确认实现

- 加密库使用 `cryptography.Fernet`。
- master key 默认保存到 `~/.db-lens/master.key`，也可通过 `DB_LENS_MASTER_KEY` 提供。
- `config add` 支持交互式输入，也支持通过 CLI 参数非交互执行。
- `config update` 已实现：
  - 未提供更新字段时，进入交互式修改流程，并使用当前值作为默认值。
  - 提供部分 CLI 参数时，只更新显式传入的字段，未传字段保持原值。
  - `password` 只有在用户明确输入新值时才重新加密写回；否则继续保留已有密文。
- `config delete` 已实现：
  - 默认展示待删除 profile 的公开信息，并要求二次确认。
  - 支持 `--yes` 跳过确认，便于脚本化调用。
- 配置主路径语言模式已实现：
  - `config add`、`config update`、`config delete` 支持 `--language zh|en`。
  - 未显式指定时，`config add`、交互式 `config update` 和需要确认的 `config delete` 会先让用户选择语言。
  - 中文模式只翻译提示语、确认语、成功/失败提示和 next steps；专业字段保持英文。

## 待补齐能力

- `config list`、`config test` 和 `doctor` 的双语或中文引导。

## 待确认

- `config update` 是否需要开放 `connect_timeout_seconds`、`read_timeout_seconds` 等连接参数的用户可修改能力。

## 已废弃设计

- 不再提供 `default_profile` 产品语义。
- 不再把 profile 绑定到单个 `database`。
- 旧配置中的 `database = "app_db"` 会在读取时兼容迁移为 `databases = ["app_db"]`，保存时统一输出新格式。
