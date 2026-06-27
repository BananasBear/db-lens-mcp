# Context Map

根据任务关键词选择必读上下文。命中多个关键词时，按任务风险从高到低读取。

| 关键词 | 必读文档 | 使用场景 |
| --- | --- | --- |
| MCP、工具、stdio、HTTP、SSE | `.harness/docs/modules/mcp-tools.md` | 设计或修改 MCP 工具、协议入口、客户端接入 |
| MySQL、MariaDB、表结构、索引、执行计划 | `.harness/docs/modules/database-inspection.md` | 设计数据库元数据读取、EXPLAIN、风险提示 |
| 安全、只读、SQL、EXPLAIN、权限 | `.harness/docs/standards/security.md`、`.harness/docs/modules/security-boundary.md` | 判断 SQL 是否可执行、数据库账号权限、危险操作拦截 |
| 配置、加密、密钥、环境变量、CLI | `.harness/docs/modules/configuration.md` | 设计配置文件、加密存储、环境变量覆盖、配置向导 |
| 安装、部署、Docker、本地、服务器 | `.harness/docs/modules/deployment.md` | 设计本地安装、服务器部署、运行模式 |
| Python、依赖、测试、日志、异常 | `.harness/docs/standards/engineering.md` | 工程实现、依赖选择、异常处理、测试策略 |
| 领域模型、模块封装、边界、过度设计、注释、可读性 | `.harness/docs/standards/domain-design.md`、`.harness/docs/standards/engineering.md` | 设计代码结构、领域边界、模块接口和可读性规则 |
| 方案、架构、模块边界 | `.harness/docs/architecture.md` | 设计或调整整体架构、模块职责 |
| 规划、里程碑、MVP、迭代 | `.harness/docs/roadmap.md` | 设计版本范围、拆分阶段目标 |

## 信息不足处理

- 如果文档不存在或内容不足，先说明“信息不足”，再基于当前已确认事实提出建议。
- 不要编造数据库权限、部署环境、团队流程或企业安全要求。
- 和用户确认过的结论应及时沉淀到 `.harness/docs/` 中对应文档。
