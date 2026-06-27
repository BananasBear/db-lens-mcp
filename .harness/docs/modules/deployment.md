# Deployment Spec

## 设计目标

一期部署以本地使用简单为主，满足需要即可，不做过度设计。服务器方向只提供 Docker 基础预留，不在一期实现完整团队服务。

## 本地用户主路径

推荐路径：

- 使用一键安装脚本安装 `db-lens` 命令。
- 配置数据库时使用 `db-lens config add` 交互式向导。
- 使用 `db-lens mcp config` 生成 AI 客户端 MCP 配置。

发布后的用户流程：

```bash
curl -fsSL https://raw.githubusercontent.com/MagicPelican/db-lens-mcp/master/scripts/install.sh | sh
```

用户只复制这一条安装命令。安装完成后，安装脚本打印可直接执行的 `db-lens` 命令路径和下一步：

1. `db-lens doctor`
2. `db-lens config add`
3. `db-lens mcp config`

用户不需要理解 Python 版本、虚拟环境或依赖管理。安装脚本负责检测并准备运行时，并处理当前 shell PATH 可能未刷新的提示。

发布门禁：

- `scripts/install.sh` 必须已推送到公开可访问地址。
- README 中的 raw GitHub 安装 URL 必须返回 `200 OK`。
- 安装脚本默认安装源必须可访问。
- 安装完成后的 `Next steps` 必须打印当前终端可直接执行的 `db-lens` 命令路径。

## 开发者备用路径

面向懂命令行的开发者，可保留：

```bash
git clone https://github.com/MagicPelican/db-lens-mcp.git
cd db-lens-mcp
DB_LENS_INSTALL_TARGET=. ./scripts/install.sh
```

这不是普通用户主路径。

## 安装脚本职责

- 检测是否已有 `uv`。
- 没有 `uv` 时，优先通过官方安装脚本安装 `uv`，无 `curl` 时再尝试 Python user site。
- 使用 `uv tool install` 安装默认 GitHub 发布源 `git+https://github.com/MagicPelican/db-lens-mcp.git`；后续 PyPI 发布后可切换为包名。
- 默认不得把当前源码目录作为用户安装目标。
- 支持通过 `DB_LENS_INSTALL_TARGET` 指定包名、Git 地址或本地目录。
- 安装完成后输出可执行的 `db-lens` 路径，避免用户当前 shell PATH 未刷新。
- 输出 `db-lens doctor`、`db-lens config add`、`db-lens mcp config` 作为下一步。
- 不要求用户手动选择 Python 版本。

## Docker 基础预留

推荐路径：

- 提供 Dockerfile。
- 支持挂载配置文件。
- 支持通过 `DB_LENS_MASTER_KEY` 注入 master key。
- 支持通过 `DB_LENS_CONFIG_FILE` 指定配置文件。

一期 Docker 主要用于后续服务器部署打基础，不承诺完整 HTTP/SSE 团队服务。

## 不建议第一版实现

- `.dmg`、`.pkg`、`.msi` 等桌面安装器。
- 完整 HTTP/SSE MCP Server。
- token 鉴权。
- 完整 Web 管理台。
- 完整企业用户体系和多租户权限模型。
- 复杂审计。
- Vault / KMS / Secret Manager 集成。

## 待确认

- Docker 镜像基础镜像。
- 第一版是否需要 Docker Compose 示例。
- 安装脚本发布地址。
