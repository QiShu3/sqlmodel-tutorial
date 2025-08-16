# 第二章：代理定义和工作流配置

## 基本代理定义

### 简单代理

定义一个代理非常简单：

```python
@fast.agent(
  instruction="Given an object, respond only with an estimate of its size."
)
```

### 完整代理应用示例

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
    asyncio.run(main()
```

### 使用文件作为指令

您也可以使用文件路径作为指令：

```python
from pathlib import Path

@fast.agent(
  instruction=Path("./sizing_prompt.md")
)
```

## 工作流类型

fast-agent 内置支持 Anthropic 的《构建有效代理》论文中引用的模式。

### 1. 链式工作流 (Chain)

链式工作流提供了按顺序调用代理的声明式方法：

```python
@fast.agent(
    "url_fetcher",
    "Given a URL, provide a complete and comprehensive summary",
    servers=["fetch"], # fastagent.config.yaml 中定义的 MCP 服务器名称
)
@fast.agent(
    "social_media",
    """
    Write a 280 character social media post for any given text.
    Respond only with the post, never use hashtags.
    """,
)
@fast.chain(
    name="post_writer",
    sequence=["url_fetcher", "social_media"],
)
async def main():
    async with fast.run() as agent:
        # 使用链式工作流
        await agent.post_writer("http://fast-agent.ai")
```

#### 链式工作流特性

- **声明式方法**：简单定义代理执行顺序
- **可嵌套**：链可以包含在其他工作流中，或包含其他工作流元素
- **交互式支持**：如果提示链，它会返回到与链中最后一个代理的聊天
- **代理切换**：通过输入 `@agent-name` 切换代理

#### 运行链式工作流

```bash
# 命令行运行
uv run workflow/chaining.py --agent post_writer --message "<url>"

# 交互式运行
async with fast.run() as agent:
  await agent.interactive(agent="post_writer")
```

### 2. 并行工作流 (Parallel)

并行工作流同时向多个代理发送相同消息（扇出），然后使用扇入代理处理合并的内容：

```python
@fast.agent("translate_fr", "Translate the text to French")
@fast.agent("translate_de", "Translate the text to German")
@fast.agent("translate_es", "Translate the text to Spanish")

@fast.parallel(
  name="translate",
  fan_out=["translate_fr","translate_de","translate_es"]
)

@fast.chain(
  "post_writer",
  sequence=["url_fetcher","social_media","translate"]
)
```

#### 并行工作流特性

- **扇出处理**：同时向多个代理发送消息
- **可选扇入**：如果不指定扇入代理，并行返回合并的代理结果
- **LLM 集成**：可用于集成来自不同 LLM 的想法
- **嵌套支持**：可在其他工作流中使用

### 3. 人工输入 (Human Input)

代理可以请求人工输入来协助任务或获取额外上下文：

```python
@fast.agent(
    instruction="An AI agent that assists with basic tasks. Request Human Input when needed.",
    human_input=True,
)

await agent("print the next number in the sequence")
```

在示例 `human_input.py` 中，代理会提示用户提供额外信息来完成任务。

### 4. 评估器-优化器 (Evaluator-Optimizer)

评估器-优化器结合了两个代理：一个生成内容（生成器），另一个判断内容并提供可操作的反馈（评估器）：

```python
@fast.evaluator_optimizer(
    name="content_optimizer",
    generator="content_generator",
    evaluator="content_evaluator",
    max_iterations=3
)
```

#### 工作流程

1. 消息首先发送给生成器
2. 生成器和评估器在循环中运行
3. 直到评估器满意质量或达到最大重试次数

### 5. 路由器 (Router)

路由器根据输入内容将消息路由到适当的代理：

```python
@fast.router(
    name="smart_router",
    agents={
        "technical": "technical_expert",
        "creative": "creative_writer",
        "analysis": "data_analyst"
    },
    instruction="Route messages to the most appropriate specialist agent"
)
```

### 6. 编排器 (Orchestrator)

编排器管理复杂的多代理交互：

```python
@fast.orchestrator(
    name="project_manager",
    agents=["researcher", "writer", "reviewer"],
    instruction="Coordinate a research and writing project"
)
```

## MCP 服务器集成

### 配置 MCP 服务器

在 `fastagent.config.yaml` 中定义 MCP 服务器：

```yaml
# STDIO 服务器示例
mcp:
  servers:
    fetch:
      command: "uvx"
      args: ["mcp-server-fetch"]
    
    # HTTP 服务器示例
    remote_server:
      transport: "http"
      url: "http://localhost:8000/mcp"
```

### 在代理中使用 MCP 服务器

```python
@fast.agent(
    "url_fetcher",
    "Given a URL, provide a complete and comprehensive summary",
    servers=["fetch"], # 引用配置文件中的服务器名称
)
```

## 代理交互方法

### 发送消息

```python
# 所有代理和工作流都响应 .send("message")
response = await agent.send("Hello, world!")

# 发送给特定代理
response = await agent.agent_name.send("Hello")
```

### 交互式会话

```python
# 启动交互式聊天会话
await agent.interactive()

# 与特定代理交互
await agent.interactive(agent="agent_name")
```

### 应用提示

```python
# 应用提示模板
response = await agent.apply_prompt(
    prompt_name="analysis_prompt",
    arguments={"data": "sample_data"},
    agent_name="data_analyst"
)
```

### 使用资源

```python
# 发送带有 MCP 资源的消息
response = await agent.with_resource(
    prompt_content="Analyze this document",
    resource_uri="file://path/to/document.pdf",
    server_name="document_server",
    agent_name="analyst"
)
```

## 模型配置

### 模型字符串格式

模型字符串格式：`provider.model_name.reasoning_effort`

```python
# 示例
"anthropic.claude-3-7-sonnet-latest"
"openai.gpt-4o"
"openai.o3-mini.high"
"azure.my-deployment"
"generic.llama3.2:latest"
```

### 模型优先级

1. 代理装饰器中明确设置
2. `--model` 标志的命令行参数
3. `fastagent.config.yaml` 中的默认模型

### 推理努力

对于支持的模型（o1、o1-preview 和 o3-mini），可以指定 `high`、`medium` 或 `low` 的推理努力：

```bash
fast-agent --model o3-mini.medium
fast-agent --model gpt-5.high
```

## 生成示例

使用快速入门命令生成工作流示例：

```bash
# 生成工作流示例
fast-agent quickstart workflow
```

这将创建包含所有工作流类型示例的完整项目结构。

## 下一步

了解了代理和工作流定义后，下一章将介绍如何配置不同的 LLM 提供商和模型设置。