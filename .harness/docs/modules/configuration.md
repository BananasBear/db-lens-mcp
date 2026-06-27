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

1. 输入 profile 名称，例如 `local-dev`。
2. 选择数据库类型，一期默认为 MySQL / MariaDB。
3. 输入 host，默认 `127.0.0.1`。
4. 输入 port，默认 `3306`。
5. 输入 database。
6. 输入 username。
7. 安全输入 password，不回显。
8. 自动生成或复用 master key。
9. 加密 password 并写入 config.toml。
10. 自动执行一次连接测试。
11. 输出下一步命令，用户通过 `db-lens mcp config` 生成 MCP 客户端配置示例。

### 查看配置

```bash
db-lens config list
```

只展示 profile、host、port、database、username，不展示密码、密文和 master key。

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

### 诊断

```bash
db-lens doctor
```

检查：

- Python 运行环境。
- 配置文件是否存在。
- 配置文件和 master key 文件权限是否合理。
- 默认 profile 是否可用。
- 数据库连通性。

## TOML 示例

```toml
default_profile = "local-dev"

[profiles.local-dev]
driver = "mysql"
host = "127.0.0.1"
port = 3306
database = "app_db"
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
