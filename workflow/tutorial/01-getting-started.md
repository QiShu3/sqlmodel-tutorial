# 第一章：快速开始和安装指南

## 概述

fast-agent 是一个 MCP 原生的代理和工作流框架，让您能够在几分钟内创建和交互复杂的代理和工作流。它支持多模态功能，包括在提示、资源和 MCP 工具调用结果中支持图像和 PDF。

## 主要特性

### 🚀 5分钟快速设置
使用 uv 安装 fast-agent-mcp，几分钟内即可启动运行。

### 🔋 开箱即用
提供复杂代理、工作流和高级 MCP 使用的现成示例。

### 🆕 Elicitation 快速入门指南
开始使用 MCP Elicitations 进行用户交互。

### 🧪 全面测试套件
全面的测试自动化，加速交付并确保质量。

### 🔧 MCP 功能支持
首个支持工具、提示、资源、采样和根的 MCP 主机。

### 👨‍💻 开发者友好
轻量级部署 - 内置 Echo 和 Playback LLM 允许强大的代理应用程序测试。

## 安装步骤

### 1. 安装 fast-agent

```bash
# 安装 fast-agent-mcp
uv pip install fast-agent-mcp
```

### 2. 快速命令

```bash
# 启动交互式会话
fast-agent go

# 使用远程 MCP 启动
fast-agent go --url https://hf.co/mcp

# 创建代理和配置文件
fast-agent setup

# 运行您的第一个代理
uv run agent.py

# 创建代理工作流示例
fast-agent quickstart workflow
```

## 基本使用示例

### 创建简单代理

创建一个名为 `sizer.py` 的文件：

```python
import asyncio
from mcp_agent.core.fastagent import FastAgent

# 创建应用程序
fast = FastAgent("Agent Example")

@fast.agent(
  instruction="Given an object, respond only with an estimate of its size."
)
async def main():
  async with fast.run() as agent:
    await agent()

if __name__ == "__main__":
    asyncio.run(main())
```

### 运行代理

```bash
# 基本运行
uv run sizer.py

# 指定模型
uv run sizer.py --model sonnet
```

### 发送消息给代理

```python
async with fast.run() as agent:
  moon_size = await agent("the moon")
  print(moon_size)
```

### 启动交互式聊天

```python
async with fast.run() as agent:
  await agent.interactive()
```

## 配置文件

### fastagent.config.yaml

创建配置文件来设置默认模型和 MCP 服务器：

```yaml
# 默认模型
default_model: "haiku"

# MCP 服务器配置
mcp:
  servers:
    fetch:
      command: "uvx"
      args: ["mcp-server-fetch"]
```

### fastagent.secrets.yaml

为敏感信息创建单独的密钥文件：

```yaml
# API 密钥配置
anthropic:
  api_key: "your_anthropic_key"

openai:
  api_key: "your_openai_key"
```

## 快速入门命令

### 创建工作流示例

```bash
# 生成工作流示例
fast-agent quickstart workflow
```

这将创建包含以下内容的示例：
- 链式工作流
- 并行处理
- 评估器-优化器
- 人工输入集成

### 创建 Elicitations 演示

```bash
# 设置 elicitations 演示
fast-agent quickstart elicitations
```

### 创建状态传输示例

```bash
# 创建状态传输示例
fast-agent quickstart state-transfer
```

## 验证安装

### 检查配置

```bash
# 检查 API 密钥问题
fast-agent check
```

### 测试基本功能

```bash
# 发送消息给特定代理
uv run agent.py --agent default --message "Analyze this dataset"

# 覆盖默认模型
uv run agent.py --model gpt-4o --agent default --message "Complex question"

# 静默运行
uv run agent.py --quiet --agent default --message "Background task"
```

## 下一步

安装完成后，您可以：

1. 探索预构建的代理示例
2. 学习如何定义自定义代理和工作流
3. 配置不同的 LLM 提供商
4. 集成 MCP 服务器
5. 部署代理作为 MCP 服务器

继续阅读下一章节了解如何定义和配置代理。