# Fast-Agent 完整教程系列

欢迎来到 `fast-agent` 的完整教程系列！本教程基于 [fast-agent.ai](https://fast-agent.ai/) 官方文档，提供了从入门到精通的完整学习路径。

## 📚 教程目录

### [教程目录结构](./fast-agent-tutorial-directory.md)
- 网站内容调研总结
- 教程目录整理
- 学习路径规划

### [第一章：快速开始](./01-getting-started.md)
- `fast-agent` 概述和主要特性
- 安装和环境配置
- 基本使用示例
- 配置文件设置
- 快速入门命令
- 安装验证

### [第二章：代理和工作流](./02-agents-and-workflows.md)
- 代理定义和配置
- 工作流类型详解
  - 链式工作流 (Chain)
  - 并行工作流 (Parallel)
  - 人工输入工作流 (Human Input)
  - 评估器-优化器工作流 (Evaluator-Optimizer)
  - 路由器和编排器
- MCP 服务器集成
- 代理交互方法
- 模型配置和优先级

### [第三章：模型配置](./03-model-configuration.md)
- 支持的 LLM 提供商
  - Anthropic Claude
  - OpenAI GPT
  - Azure OpenAI
  - DeepSeek
  - Google Gemini
  - Generic (Ollama)
  - OpenRouter
  - TensorZero
  - AWS Bedrock
- 模型配置格式
- 环境变量设置
- 模型别名和优先级
- 结构化输出
- 配置验证和最佳实践

### [第四章：MCP 集成](./04-mcp-integration.md)
- MCP 服务器配置和管理
- 在代理中使用 MCP 服务器
- 将代理部署为 MCP 服务器
- Elicitations 功能
  - 交互式表单
  - 字段类型和验证
  - 工具调用集成
  - 自定义处理器
- 状态传输和会话管理
- MCP 类型兼容性
- 最佳实践和故障排除

### [第五章：配置参考](./05-configuration-reference.md)
- 配置文件详解
  - `fastagent.config.yaml`
  - `fastagent.secrets.yaml`
- 环境变量配置
- 通用设置和模型提供商配置
- MCP 服务器配置 (STDIO, HTTP, SSE)
- Elicitations 配置
- 高级配置选项
  - 日志和性能设置
  - 安全和缓存配置
- 开发和调试配置
- 部署配置 (生产环境, Docker)
- 配置验证和最佳实践

### [第六章：部署和运行](./06-deployment-and-running.md)
- 多种运行模式
  - 交互模式
  - 命令行执行
  - MCP 服务器部署
  - Python 程序集成
  - Web 服务部署
- 会话管理和脚本集成
- Python 程序集成 (基本、异步、工作流)
- Web 服务部署 (FastAPI 和 Flask)
- Docker 部署
  - Dockerfile 编写
  - docker-compose.yml 配置
  - 构建和运行
- Kubernetes 部署
  - Deployment 和 Service
  - ConfigMap 和 Secret
  - 部署命令
- 监控和日志
  - 日志配置
  - Prometheus 监控
  - Grafana 仪表板
- 性能优化和故障排除

### [第七章：实践示例和最佳实践](./07-examples-and-best-practices.md)
- 实践示例
  - 文档分析助手
  - 代码审查助手
  - 客户服务聊天机器人
- 最佳实践
  - 代理设计原则
  - 工作流设计模式
  - 错误处理和重试策略
  - 性能优化策略
  - 安全最佳实践
  - 监控和日志策略
  - 测试策略
- 下一步学习方向

### [第八章：故障排除和常见问题](./08-troubleshooting.md)
- 常见问题诊断
  - 安装和配置问题
  - 模型和提供商问题
  - MCP 服务器问题
  - 性能问题
  - 网络和连接问题
  - 工作流问题
- 调试工具和技巧
  - 调试模式启用
  - 调试代理使用
  - 性能分析
- 日志分析
  - 结构化日志查询
  - 日志聚合和监控
- 健康检查和监控
  - 系统健康检查
  - 自动化监控
- 故障恢复策略
  - 自动重启机制
  - 断路器模式

### [第九章：API 参考文档](./09-api-reference.md)
- 核心类和方法
  - Agent 类详解
  - Workflow 类详解
  - Config 类详解
- MCP 集成 API
  - MCPServer 类
  - MCP 客户端
- 工具和实用函数
  - 模型管理
  - 日志配置
  - 性能监控
- 异常处理
  - 异常类层次结构
  - 自定义异常处理
- 高级功能
  - 批处理
  - 缓存
  - 插件系统
- 命令行接口
  - 基本命令
  - 高级命令选项
- 环境变量配置
- 类型定义和配置模式

## 🚀 快速导航

### 新手入门路径
1. [快速开始](./01-getting-started.md) - 了解基础概念和安装
2. [代理和工作流](./02-agents-and-workflows.md) - 学习核心功能
3. [模型配置](./03-model-configuration.md) - 配置您的 LLM 提供商
4. [实践示例](./07-examples-and-best-practices.md) - 通过示例学习

### 进阶开发路径
1. [MCP 集成](./04-mcp-integration.md) - 掌握 MCP 功能
2. [配置参考](./05-configuration-reference.md) - 深入了解配置选项
3. [部署和运行](./06-deployment-and-running.md) - 生产环境部署
4. [API 参考](./09-api-reference.md) - 完整 API 文档

### 问题解决路径
1. [故障排除](./08-troubleshooting.md) - 常见问题解决
2. [最佳实践](./07-examples-and-best-practices.md) - 避免常见陷阱
3. [API 参考](./09-api-reference.md) - 查找具体方法

## 📖 学习建议

### 适合人群
- **初学者**：从第一章开始，按顺序学习
- **有经验的开发者**：可以直接跳到感兴趣的章节
- **系统管理员**：重点关注第五、六、八章
- **AI 应用开发者**：重点关注第二、四、七章

### 学习方式
- **理论与实践结合**：每章都包含实际示例，建议边学边练
- **循序渐进**：从简单概念开始，逐步深入高级功能
- **问题驱动**：遇到问题时查阅相应章节
- **参考查询**：将 API 参考作为开发时的查询手册

### 前置知识
- 基本的 Python 编程经验
- 了解 YAML 配置文件格式
- 熟悉命令行操作
- 对 AI/LLM 有基本了解（推荐但非必需）

## 🛠️ 实践环境

### 推荐开发环境
- Python 3.8+
- 支持 YAML 的代码编辑器
- 终端/命令行工具
- Git（用于版本控制）

### 必需的 API 密钥
根据您选择的 LLM 提供商，准备相应的 API 密钥：
- Anthropic API Key
- OpenAI API Key
- Google API Key
- 等等

## 📝 文档说明

### 文档特点
- **全面性**：涵盖从入门到高级的所有功能
- **实用性**：每个概念都配有实际示例
- **结构化**：清晰的章节划分和导航
- **可查询**：详细的 API 参考和索引

### 文档更新
本教程基于 `fast-agent.ai` 官方文档编写，会根据官方更新进行同步。如果发现内容过时或有错误，请参考最新的官方文档。

### 贡献和反馈
如果您在学习过程中发现问题或有改进建议，欢迎提供反馈。

## 🎯 学习目标

完成本教程系列后，您将能够：

1. **熟练使用 fast-agent**：掌握所有核心功能和高级特性
2. **设计智能代理**：根据需求设计和实现各种类型的 AI 代理
3. **构建复杂工作流**：创建多步骤、多代理的复杂工作流
4. **集成 MCP 服务器**：利用 MCP 协议扩展代理能力
5. **部署生产应用**：将代理应用部署到生产环境
6. **解决常见问题**：独立诊断和解决使用中的问题
7. **优化性能**：提高代理应用的性能和可靠性

---

**开始您的 fast-agent 学习之旅吧！** 🚀

选择适合您的学习路径，从 [快速开始](./01-getting-started.md) 开始，或者直接跳到您感兴趣的章节。祝您学习愉快！