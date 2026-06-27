# Modules

本目录记录不同功能模块的设计文档。

## 当前模块

- `mcp-tools.md`：MCP 工具清单和输入输出约定。
- `database-inspection.md`：数据库洞察领域模型和能力边界。
- `security-boundary.md`：安全边界和只读防护模型。
- `configuration.md`：配置文件、环境变量和加密策略。
- `deployment.md`：本地安装和服务器部署策略。

## 使用规则

- 新增核心模块时，在本目录创建独立文档。
- 跨模块工程规则放到 `../standards/`。
- 模块文档应包含目标、边界、输入输出、风险和待确认项。
