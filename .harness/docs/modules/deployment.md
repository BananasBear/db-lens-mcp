# Deployment Spec

## 设计目标

一期部署以本地使用简单为主，满足需要即可，不做过度设计。服务器方向只提供 Docker 基础预留，不在一期实现完整团队服务。

## 本地安装主路径

推荐路径：

- 使用 `uvx db-lens-mcp` 临时运行。
- 使用 `pipx install db-lens-mcp` 持久安装。
- 配置数据库时使用 `db-lens config add` 交互式向导。
- 启动本地 MCP 使用 `db-lens mcp run`。

典型流程：

```bash
uvx db-lens-mcp
db-lens config add
db-lens mcp run
```

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
- 第一版是否自动生成 AI 客户端配置。
