# Fast-Agent 教程目录结构

基于 https://fast-agent.ai/ 网站内容整理的教程目录结构。

## 1. 快速开始 (Getting Started)

### 1.1 安装和设置
- 安装 fast-agent-mcp
- 使用 `fast-agent go` 开始交互式会话
- 使用 `fast-agent setup` 创建代理和配置文件
- 运行第一个代理

### 1.2 快速启动示例
- `fast-agent quickstart workflow` - 创建工作流示例
- `fast-agent quickstart researcher` - 创建研究员代理示例
- `fast-agent quickstart data-analysis` - 创建数据分析代理示例
- `fast-agent quickstart elicitations` - MCP Elicitations 快速入门

## 2. 代理开发 (Agents)

### 2.1 定义代理和工作流 (Defining Agents and Workflows)
- 基础代理定义
- 代理指令配置
- 使用路径作为指令
- 工作流和 MCP 服务器集成

### 2.2 工作流类型
- **Chain（链式）** - 按顺序调用代理
- **Parallel（并行）** - 同时向多个代理发送消息
- **Human Input（人工输入）** - 代理请求人工协助
- **Evaluator-Optimizer（评估器-优化器）** - 生成内容并评估反馈

### 2.3 部署和运行 (Deploy and Run)
- **交互模式** - 开发、调试和直接用户交互
- **命令行执行** - 脚本化和自动化
- **MCP 服务器部署** - 作为 MCP 服务器运行
- **Python 程序集成** - 嵌入到现有应用程序

## 3. 模型配置 (Models)

### 3.1 模型特性和历史保存 (Model Features and History Saving)
- 模型字符串格式：`provider.model_name.reasoning_effort`
- 模型优先级配置
- 推理努力级别设置
- 模型别名使用
- 对话历史保存

### 3.2 LLM 提供商 (LLM Providers)
- **Anthropic** - Claude 系列模型配置
- **OpenAI** - GPT 系列和 o1/o3 模型配置
- **Azure OpenAI** - Azure 环境下的 OpenAI 模型
- **DeepSeek** - DeepSeek 模型配置
- **Google** - Google 模型配置
- **Generic (Ollama等)** - 通用提供商配置
- **OpenRouter** - OpenRouter 服务配置
- **TensorZero** - TensorZero 集成
- **AWS Bedrock** - AWS Bedrock 模型配置

## 4. MCP 集成

### 4.1 MCP Elicitations 快速入门
- 交互式表单演示
- 工具调用期间的 Elicitation
- 自定义 Elicitation 处理器
- 配置选项（forms、auto-cancel、none 模式）

### 4.2 MCP 服务器配置
- STDIO 传输配置
- SSE 传输配置
- 环境变量设置
- 超时和错误处理

## 5. 配置参考 (Configuration Reference)

### 5.1 配置文件结构
- `fastagent.config.yaml` - 主配置文件
- `fastagent.secrets.yaml` - 敏感信息配置
- 环境变量配置模式
- 配置文件查找路径

### 5.2 通用设置
- 默认模型配置
- 自动采样设置
- 执行引擎配置

### 5.3 命令行选项 (Command Line Options)
- 代理应用程序选项
- `fast-agent go` 命令
- `fast-agent check` 诊断命令
- `fast-agent setup` 项目设置
- `fast-agent quickstart` 示例创建

## 6. 高级特性

### 6.1 多模态支持
- 图像处理（Prompts、Resources、MCP 工具调用结果）
- PDF 文档处理
- 视觉和音频功能（特定提供商）

### 6.2 测试和开发
- Echo 和 Playback LLM 用于测试
- 内置模型支持
- 无需 LLM 的直通模型测试
- 综合测试套件

### 6.3 生产部署
- 服务器模式部署
- HTTP/SSE/STDIO 传输选项
- 程序化服务器启动
- 与现有应用程序集成

## 7. 实践示例

### 7.1 基础示例
- 尺寸估算代理 (sizer.py)
- 社交媒体帖子生成器
- URL 内容获取和摘要

### 7.2 工作流示例
- 链式工作流（URL 获取 → 社交媒体帖子）
- 并行翻译工作流
- 评估器-优化器模式

### 7.3 高级应用
- 研究员代理（带评估器-优化器工作流）
- 数据分析代理（类似 ChatGPT 体验）
- MCP Roots 支持演示

---

*本目录基于 fast-agent.ai 官方文档整理，涵盖了从基础安装到高级部署的完整教程结构。*