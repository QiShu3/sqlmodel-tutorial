# 第四章：MCP 集成和 Elicitations 功能

## MCP 集成概述

fast-agent 是首个支持工具、提示、资源、采样和根的 MCP 主机。它提供了与 Model Context Protocol (MCP) 的无缝集成，使您能够轻松使用 MCP 服务器或将代理部署为 MCP 服务器。

## MCP 服务器配置

### 基本配置格式

在 `fastagent.config.yaml` 中配置 MCP 服务器：

```yaml
mcp:
  servers:
    # STDIO 服务器示例
    server_name:
      transport: "stdio" # "stdio" 或 "sse"
      command: "npx" # 要执行的命令
      args: ["@package/server-name"] # 命令参数数组
      read_timeout_seconds: 60 # 可选超时（秒）
      env: # 可选环境变量
        ENV_VAR1: "value1"
        ENV_VAR2: "value2"
      sampling: # 可选采样设置
        model: "haiku" # 用于采样请求的模型
    
    # Streamable HTTP 服务器示例
    streamable_http_server:
      transport: "http"
      url: "http://localhost:8000/mcp"
      read_transport_sse_timeout_seconds: 300 # HTTP 连接超时
      headers: # 可选头部
        Authorization: "Bearer token"
```

### 常用 MCP 服务器示例

#### 1. Fetch 服务器（网页抓取）

```yaml
mcp:
  servers:
    fetch:
      command: "uvx"
      args: ["mcp-server-fetch"]
```

#### 2. 文件系统服务器

```yaml
mcp:
  servers:
    filesystem:
      command: "npx"
      args: ["@modelcontextprotocol/server-filesystem", "/path/to/directory"]
```

#### 3. GitHub 服务器

```yaml
mcp:
  servers:
    github:
      command: "npx"
      args: ["@modelcontextprotocol/server-github"]
      env:
        GITHUB_PERSONAL_ACCESS_TOKEN: "your_token"
```

## 在代理中使用 MCP 服务器

### 基本用法

```python
@fast.agent(
    "url_fetcher",
    "Given a URL, provide a complete and comprehensive summary",
    servers=["fetch"], # 引用配置文件中的服务器名称
)
async def main():
    async with fast.run() as agent:
        result = await agent.url_fetcher("https://example.com")
        print(result)
```

### 多服务器集成

```python
@fast.agent(
    "research_agent",
    "Research topics using web and file resources",
    servers=["fetch", "filesystem", "github"],
)
```

## 将代理部署为 MCP 服务器

### 命令行部署

```bash
# 启动为 Streamable HTTP 服务器
uv run agent.py --server --transport http --port 8080

# 启动为 SSE 服务器
uv run agent.py --server --transport sse --port 8080

# 启动为 stdio 服务器
uv run agent.py --server --transport stdio
```

### 编程方式部署

```python
import asyncio
from mcp_agent.core.fastagent import FastAgent

fast = FastAgent("Server Agent")

@fast.agent(instruction="You are an API agent")
async def main():
    # 编程方式启动服务器
    await fast.start_server(
        transport="sse",
        host="0.0.0.0",
        port=8080,
        server_name="API-Agent-Server",
        server_description="Provides API access to my agent"
    )

if __name__ == "__main__":
    asyncio.run(main())
```

### MCP 服务器功能

每个代理作为 MCP 服务器时会暴露：

1. **MCP 工具**：用于向代理发送消息
2. **提示**：返回对话历史
3. **状态传输**：通过 MCP 提示实现跨代理状态传输

## Elicitations 功能

Elicitations 允许 MCP 服务器在运行时请求用户的额外信息。

### Elicitations 快速入门

#### 设置演示环境

```bash
# 创建并进入新目录
mkdir fast-agent && cd fast-agent

# 创建并激活 Python 环境
uv venv
source .venv/bin/activate  # Linux/Mac
# 或
.venv\Scripts\activate     # Windows

# 安装 fast-agent
uv pip install fast-agent-mcp

# 设置 elicitations 演示
fast-agent quickstart elicitations

# 进入演示文件夹
cd elicitations
```

### Elicitations 演示类型

演示包含三个 MCP 服务器和三个 fast-agent 程序：

1. **交互式表单演示**：展示不同类型的表单、字段和验证
2. **工具调用演示**：在工具调用期间进行的 Elicitation 演示
3. **自定义处理器示例**：使用自定义 Elicitation 处理器的示例

### 1. 交互式表单演示

```bash
# 启动交互式表单演示
uv run forms_demo.py
```

#### 表单特性

- **导航**：可以使用 Tab 或箭头键（→\←）导航
- **实时验证**：具有实时验证功能
- **取消功能**：可以使用 Escape 键取消
- **多行文本输入**：支持长字段的多行文本输入
- **身份识别**：识别产生请求的代理和 MCP 服务器
- **取消所有选项**：取消 Elicitation 请求，并自动取消未来请求以避免行为不当的服务器造成不必要的中断

#### 支持的字段类型

`elicitation_forms_server.py` 文件包含所有字段类型和验证的示例：

- **数字**：Number 类型
- **布尔值**：Boolean 类型
- **枚举**：Enum 类型
- **字符串**：String 类型
- **格式支持**：Email、Uri、Date 和 Date/Time

### 2. 工具调用演示

```bash
# 运行工具调用演示
uv run tool_call.py

# 使用真实 LLM
uv run tool_call.py --model sonnet
```

#### 特性展示

- **直通模型**：支持无需 LLM 的测试
- **直接工具调用**：通过发送 `***CALL_TOOL` 消息直接调用 MCP 服务器工具

### 3. 自定义处理器示例

```bash
# 运行游戏角色生成器
uv run game_character.py
```

#### 自定义处理器实现

```python
# game_character.py
@fast.agent(
    "character-creator",
    servers=["elicitation_forms_server"],
    # 从 game_character_handler.py 注册我们的处理器
    elicitation_handler=game_character_elicitation_handler,
)
```

#### 自定义处理器用途

- **MCP 服务器开发者**：帮助完成自动化测试流程
- **生产使用**：发送通知或通过远程平台（如 Web 表单）请求输入

### Elicitations 配置

Elicitations 现在在 fast-agent 中默认启用，可以通过 `fastagent.config.yaml` 文件配置：

```yaml
mcp:
  servers:
    # 不同模式的 Elicitation 测试服务器
    elicitation_forms_mode:
      command: "uv"
      args: ["run", "elicitation_test_server_advanced.py"]
      transport: "stdio"
      cwd: "."
      elicitation:
        mode: "forms" # "forms"、"auto-cancel" 或 "none"
```

#### Elicitation 模式

1. **forms**（默认）：显示交互式表单
2. **auto-cancel**：fast-agent 宣传 Elicitation 功能，但自动取消来自 MCP 服务器的 Elicitation 请求
3. **none**：不向 MCP 服务器宣传 Elicitation 功能

## 状态传输

### 状态传输快速入门

```bash
# 创建状态传输示例
fast-agent quickstart state-transfer
```

### 步骤 1：设置代理一作为 MCP 服务器

```bash
# 启动 agent_one 作为 MCP 服务器
uv run agent_one.py --server --port 8001
```

### 步骤 2：使用 MCP Inspector 连接

```bash
# 运行 MCP inspector
npx @modelcontextprotocol/inspector
```

选择 "Streamable HTTP" 传输类型，URL 为 `http://localhost:8001/mcp`。

### 步骤 3：传输对话到代理二

```bash
# 启动 agent_two
uv run agent_two.py
```

在启动后，输入 `/prompts` 查看可用提示。选择 1 应用来自 agent_one 的提示到 agent_two，传输对话上下文。

### 配置概览

```yaml
# fastagent.config.yaml
mcp:
  servers:
    agent_one:
      transport: http
      url: http://localhost:8001/mcp
```

```python
# agent_two.py
@fast.agent(name="agent_two",
            instruction="You are a helpful AI Agent",
            servers=["agent_one"])
```

### 保存/重新加载对话

#### 保存对话历史

```bash
# 在 agent_two 聊天中输入
***SAVE_HISTORY history.json
```

#### 使用 prompt-server 重新加载

```yaml
# fastagent.config.yaml
mcp:
  servers:
    prompts:
      command: prompt-server
      args: ["history.json"]
```

```python
# 更新 agent_two.py
@fast.agent(name="agent_two",
            instruction="You are a helpful AI Agent",
            servers=["prompts"])
```

## MCP 类型兼容性

FastAgent 构建为与 MCP SDK 类型系统无缝集成：

### PromptMessageMultipart

与助手的对话基于 `PromptMessageMultipart` - 这是 MCP `PromptMessage` 类型的扩展，支持多个内容部分。

### 消息历史传输

```python
@fast.agent(name="haiku", model="haiku")
@fast.agent(name="openai", model="o3-mini.medium")

async def main() -> None:
    async with fast.run() as agent:
        # 与 "haiku" 开始交互式会话
        await agent.prompt(agent_name="haiku")
        # 将消息历史传输到 "openai"（使用 PromptMessageMultipart）
        await agent.openai.generate(agent.haiku.message_history)
        # 继续对话
        await agent.prompt(agent_name="openai")
```

## 最佳实践

### MCP 服务器配置

1. **超时设置**：为长时间运行的操作设置适当的超时
2. **环境变量**：使用环境变量管理敏感信息
3. **错误处理**：实现适当的错误处理和重试逻辑

### Elicitations 使用

1. **用户体验**：设计直观的表单和验证
2. **取消机制**：提供清晰的取消选项
3. **自定义处理器**：为特定用例实现自定义处理器

### 状态传输

1. **历史管理**：定期保存重要对话历史
2. **格式选择**：根据需要选择 JSON 或文本格式
3. **版本控制**：跟踪对话历史的版本

## 故障排除

### 常见问题

1. **连接超时**：检查网络连接和服务器状态
2. **权限错误**：验证 API 密钥和权限设置
3. **格式错误**：确保配置文件格式正确

### 调试技巧

```bash
# 检查 MCP 服务器状态
fast-agent check

# 详细日志输出
uv run agent.py --verbose

# 测试特定服务器
uv run agent.py --server-test server_name
```

## 下一步

了解了 MCP 集成和 Elicitations 功能后，下一章将介绍配置参考和高级设置。