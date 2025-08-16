# 第九章：API 参考文档

## 核心类和方法

### Agent 类

#### 基本用法

```python
from fastagent import Agent

# 创建代理
agent = Agent(
    instructions="You are a helpful assistant",
    model="anthropic.claude-3-sonnet-latest",
    name="my_agent"
)
```

#### Agent 构造函数

```python
class Agent:
    def __init__(
        self,
        instructions: str = None,
        model: str = None,
        name: str = None,
        mcp_servers: List[str] = None,
        system_prompt: str = None,
        temperature: float = None,
        max_tokens: int = None,
        tools: List[Dict] = None,
        **kwargs
    ):
        """
        创建新的 Agent 实例
        
        Args:
            instructions: 代理的指令或角色描述
            model: 要使用的模型名称（如 "anthropic.claude-3-sonnet-latest"）
            name: 代理的名称，用于标识和日志
            mcp_servers: 要连接的 MCP 服务器列表
            system_prompt: 系统提示词（如果不使用 instructions）
            temperature: 生成温度 (0.0-1.0)
            max_tokens: 最大生成令牌数
            tools: 可用工具列表
            **kwargs: 其他模型特定参数
        """
```

#### 主要方法

##### send() 方法

```python
async def send(
    self,
    message: str,
    context: Dict[str, Any] = None,
    stream: bool = False,
    **kwargs
) -> str:
    """
    向代理发送消息并获取响应
    
    Args:
        message: 要发送的消息
        context: 上下文信息字典
        stream: 是否启用流式响应
        **kwargs: 其他参数
    
    Returns:
        代理的响应字符串
    
    Raises:
        AgentError: 代理执行错误
        ModelError: 模型调用错误
        MCPError: MCP 服务器错误
    """

# 使用示例
response = await agent.send("Hello, how are you?")
print(response)

# 带上下文
context = {"user_id": "123", "session_id": "abc"}
response = await agent.send("What's my order status?", context=context)

# 流式响应
async for chunk in agent.send("Tell me a story", stream=True):
    print(chunk, end="")
```

##### interact() 方法

```python
async def interact(
    self,
    initial_message: str = None,
    max_turns: int = None,
    exit_keywords: List[str] = None
) -> List[Dict[str, str]]:
    """
    启动交互式会话
    
    Args:
        initial_message: 初始消息
        max_turns: 最大轮次
        exit_keywords: 退出关键词列表
    
    Returns:
        对话历史列表
    """

# 使用示例
history = await agent.interact(
    initial_message="Hello!",
    max_turns=10,
    exit_keywords=["bye", "exit", "quit"]
)
```

##### apply_prompt() 方法

```python
async def apply_prompt(
    self,
    prompt_name: str,
    arguments: Dict[str, Any] = None
) -> str:
    """
    应用 MCP 提示
    
    Args:
        prompt_name: 提示名称
        arguments: 提示参数
    
    Returns:
        应用提示后的响应
    """

# 使用示例
response = await agent.apply_prompt(
    "analyze_code",
    arguments={"code": "def hello(): print('world')"}
)
```

##### use_resource() 方法

```python
async def use_resource(
    self,
    resource_uri: str,
    operation: str = "read"
) -> Any:
    """
    使用 MCP 资源
    
    Args:
        resource_uri: 资源 URI
        operation: 操作类型（read, write, list 等）
    
    Returns:
        资源内容或操作结果
    """

# 使用示例
content = await agent.use_resource("file:///path/to/file.txt")
files = await agent.use_resource("file:///path/to/directory", "list")
```

#### 属性和配置

```python
# 访问代理属性
print(agent.name)           # 代理名称
print(agent.model)          # 使用的模型
print(agent.instructions)   # 代理指令
print(agent.mcp_servers)    # 连接的 MCP 服务器

# 动态修改配置
agent.temperature = 0.7
agent.max_tokens = 2000

# 添加工具
agent.add_tool({
    "name": "calculator",
    "description": "Perform calculations",
    "parameters": {
        "type": "object",
        "properties": {
            "expression": {"type": "string"}
        }
    }
})
```

### Workflow 类

#### 基本用法

```python
from fastagent import Workflow

# 从文件加载工作流
workflow = Workflow.from_file("my_workflow.yaml")

# 从字典创建工作流
workflow_config = {
    "name": "analysis_workflow",
    "type": "chain",
    "steps": [
        {"agent": "analyzer", "input_key": "text", "output_key": "analysis"},
        {"agent": "summarizer", "input_key": "analysis", "output_key": "summary"}
    ]
}
workflow = Workflow.from_dict(workflow_config)
```

#### Workflow 构造函数

```python
class Workflow:
    def __init__(
        self,
        name: str,
        workflow_type: str,
        steps: List[Dict],
        agents: Dict[str, Agent] = None,
        config: Dict[str, Any] = None
    ):
        """
        创建工作流实例
        
        Args:
            name: 工作流名称
            workflow_type: 工作流类型（chain, parallel, human_input 等）
            steps: 工作流步骤列表
            agents: 代理字典
            config: 工作流配置
        """
```

#### 主要方法

##### run() 方法

```python
async def run(
    self,
    input_data: Dict[str, Any],
    context: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    运行工作流
    
    Args:
        input_data: 输入数据
        context: 执行上下文
    
    Returns:
        工作流输出结果
    
    Raises:
        WorkflowError: 工作流执行错误
        ValidationError: 输入验证错误
    """

# 使用示例
result = await workflow.run({
    "text": "This is a document to analyze",
    "options": {"detailed": True}
})

print(result["summary"])  # 访问输出
```

##### validate() 方法

```python
def validate(self) -> List[str]:
    """
    验证工作流配置
    
    Returns:
        验证错误列表（空列表表示无错误）
    """

# 使用示例
errors = workflow.validate()
if errors:
    print("Workflow validation errors:")
    for error in errors:
        print(f"  - {error}")
else:
    print("Workflow is valid")
```

##### add_step() 方法

```python
def add_step(
    self,
    step_config: Dict[str, Any],
    position: int = None
) -> None:
    """
    添加工作流步骤
    
    Args:
        step_config: 步骤配置
        position: 插入位置（None 表示追加到末尾）
    """

# 使用示例
workflow.add_step({
    "agent": "validator",
    "input_key": "summary",
    "output_key": "validation_result",
    "conditions": ["summary != null"]
})
```

### 配置管理

#### Config 类

```python
from fastagent import Config

# 加载配置
config = Config.load()  # 从默认位置加载
config = Config.load("custom_config.yaml")  # 从指定文件加载

# 访问配置
print(config.default_model)
print(config.anthropic.api_key)
print(config.mcp.servers)

# 修改配置
config.default_model = "openai.gpt-4"
config.anthropic.api_key = "new_key"

# 保存配置
config.save()
config.save("backup_config.yaml")
```

#### 配置验证

```python
# 验证配置
errors = config.validate()
if errors:
    print("Configuration errors:")
    for error in errors:
        print(f"  - {error}")

# 检查特定提供商配置
if config.validate_provider("anthropic"):
    print("Anthropic configuration is valid")

# 测试连接
results = await config.test_connections()
for provider, result in results.items():
    print(f"{provider}: {'✓' if result['success'] else '✗'}")
```

### MCP 集成

#### MCPServer 类

```python
from fastagent.mcp import MCPServer

# 创建 MCP 服务器连接
server = MCPServer(
    name="filesystem",
    transport="stdio",
    command="uvx",
    args=["mcp-server-filesystem"],
    env={"ALLOWED_DIRECTORIES": "/safe/path"}
)

# 启动服务器
await server.start()

# 列出可用工具
tools = await server.list_tools()
print("Available tools:", [tool["name"] for tool in tools])

# 调用工具
result = await server.call_tool("read_file", {"path": "/path/to/file.txt"})

# 列出资源
resources = await server.list_resources()

# 获取资源
content = await server.get_resource("file:///path/to/file.txt")

# 关闭服务器
await server.close()
```

#### MCP 客户端

```python
from fastagent.mcp import MCPClient

# 创建客户端
client = MCPClient()

# 连接到服务器
await client.connect("stdio", command="uvx", args=["mcp-server-filesystem"])

# 使用客户端
tools = await client.list_tools()
result = await client.call_tool("read_file", {"path": "/file.txt"})

# 断开连接
await client.disconnect()
```

### 工具和实用函数

#### 模型管理

```python
from fastagent.models import ModelManager

# 创建模型管理器
manager = ModelManager()

# 列出可用模型
models = manager.list_models()
print("Available models:", models)

# 获取模型信息
info = manager.get_model_info("anthropic.claude-3-sonnet-latest")
print(f"Model: {info['name']}, Provider: {info['provider']}")

# 验证模型
if manager.validate_model("openai.gpt-4"):
    print("Model is valid and available")

# 获取推荐模型
recommended = manager.get_recommended_model(task="code_generation")
print(f"Recommended model for code generation: {recommended}")
```

#### 日志配置

```python
from fastagent.logging import setup_logging

# 基本日志设置
setup_logging(level="INFO")

# 详细日志设置
setup_logging(
    level="DEBUG",
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    file="fast-agent.log",
    max_size="10MB",
    backup_count=5
)

# 结构化日志
setup_logging(
    level="INFO",
    format="json",
    file="fast-agent.jsonl"
)
```

#### 性能监控

```python
from fastagent.monitoring import PerformanceMonitor

# 创建监控器
monitor = PerformanceMonitor()

# 监控代理调用
@monitor.track("agent_call")
async def monitored_agent_call():
    return await agent.send("Hello")

# 获取统计信息
stats = monitor.get_stats()
print(f"Total calls: {stats['total_calls']}")
print(f"Average duration: {stats['avg_duration']:.2f}s")
print(f"Error rate: {stats['error_rate']:.2%}")

# 导出指标
metrics = monitor.export_prometheus_metrics()
print(metrics)
```

### 异常处理

#### 异常类层次结构

```python
from fastagent.exceptions import (
    FastAgentError,      # 基础异常
    AgentError,          # 代理相关错误
    WorkflowError,       # 工作流错误
    ModelError,          # 模型错误
    MCPError,            # MCP 相关错误
    ConfigurationError,  # 配置错误
    ValidationError,     # 验证错误
    TimeoutError,        # 超时错误
    RateLimitError,      # 速率限制错误
    AuthenticationError  # 认证错误
)

# 异常处理示例
try:
    response = await agent.send("Hello")
except RateLimitError as e:
    print(f"Rate limit exceeded: {e}")
    # 实现退避策略
    await asyncio.sleep(e.retry_after)
except AuthenticationError as e:
    print(f"Authentication failed: {e}")
    # 检查 API 密钥
except ModelError as e:
    print(f"Model error: {e}")
    # 尝试备用模型
except FastAgentError as e:
    print(f"General error: {e}")
    # 通用错误处理
```

#### 自定义异常处理

```python
from fastagent.exceptions import FastAgentError

class CustomAgentError(FastAgentError):
    """自定义代理错误"""
    def __init__(self, message: str, error_code: str = None):
        super().__init__(message)
        self.error_code = error_code

# 使用自定义异常
def validate_input(data):
    if not data:
        raise CustomAgentError(
            "Input data is required",
            error_code="MISSING_INPUT"
        )
```

### 高级功能

#### 批处理

```python
from fastagent.batch import BatchProcessor

# 创建批处理器
processor = BatchProcessor(
    agent=agent,
    batch_size=10,
    max_concurrent=5
)

# 批量处理消息
messages = ["Hello", "How are you?", "What's the weather?"]
results = await processor.process_batch(messages)

for i, result in enumerate(results):
    print(f"Message {i}: {result}")
```

#### 缓存

```python
from fastagent.cache import ResponseCache

# 创建缓存
cache = ResponseCache(
    backend="redis",  # 或 "memory", "file"
    ttl=3600,         # 1小时过期
    max_size=1000     # 最大缓存条目
)

# 使用缓存的代理
cached_agent = Agent(
    instructions="You are a helpful assistant",
    model="anthropic.claude-3-sonnet-latest",
    cache=cache
)

# 第一次调用会缓存结果
response1 = await cached_agent.send("What is 2+2?")

# 第二次调用会从缓存返回
response2 = await cached_agent.send("What is 2+2?")  # 从缓存获取

# 清除缓存
await cache.clear()
```

#### 插件系统

```python
from fastagent.plugins import Plugin, PluginManager

# 创建自定义插件
class LoggingPlugin(Plugin):
    def __init__(self):
        super().__init__(name="logging")
    
    async def before_send(self, agent, message, context):
        print(f"Sending message to {agent.name}: {message[:50]}...")
    
    async def after_send(self, agent, message, response, context):
        print(f"Received response from {agent.name}: {response[:50]}...")
    
    async def on_error(self, agent, error, context):
        print(f"Error in {agent.name}: {error}")

# 注册插件
manager = PluginManager()
manager.register(LoggingPlugin())

# 使用插件的代理
agent = Agent(
    instructions="You are a helpful assistant",
    model="anthropic.claude-3-sonnet-latest",
    plugin_manager=manager
)
```

### 命令行接口

#### 基本命令

```bash
# 版本信息
fast-agent --version

# 帮助信息
fast-agent --help
fast-agent <command> --help

# 配置管理
fast-agent config init                    # 初始化配置
fast-agent config show                    # 显示当前配置
fast-agent config validate               # 验证配置
fast-agent config set key value          # 设置配置值

# 模型管理
fast-agent models list                    # 列出可用模型
fast-agent models test <model>            # 测试模型
fast-agent models info <model>            # 模型信息

# MCP 管理
fast-agent mcp list                       # 列出 MCP 服务器
fast-agent mcp start <server>             # 启动 MCP 服务器
fast-agent mcp stop <server>              # 停止 MCP 服务器
fast-agent mcp test <server>              # 测试 MCP 服务器

# 工作流管理
fast-agent workflow validate <file>       # 验证工作流
fast-agent workflow run <file>            # 运行工作流
fast-agent workflow list                  # 列出工作流

# 快速开始
fast-agent quickstart                     # 基本快速开始
fast-agent quickstart workflow           # 工作流示例
fast-agent quickstart elicitations       # Elicitations 示例
fast-agent quickstart state-transfer     # 状态传输示例
```

#### 高级命令选项

```bash
# 全局选项
fast-agent --config <file>               # 指定配置文件
fast-agent --log-level <level>           # 设置日志级别
fast-agent --debug                       # 启用调试模式
fast-agent --profile                     # 启用性能分析
fast-agent --no-cache                    # 禁用缓存

# 交互模式
fast-agent chat                          # 启动聊天模式
fast-agent chat --agent <name>           # 使用特定代理
fast-agent chat --model <model>          # 使用特定模型
fast-agent chat --system <prompt>        # 设置系统提示

# 批处理模式
fast-agent batch <input_file>            # 批量处理文件
fast-agent batch --output <file>         # 指定输出文件
fast-agent batch --format json          # 指定输出格式

# 服务器模式
fast-agent serve                         # 启动 HTTP 服务器
fast-agent serve --port 8000             # 指定端口
fast-agent serve --host 0.0.0.0         # 指定主机
fast-agent serve --workers 4             # 指定工作进程数

# MCP 服务器模式
fast-agent mcp-server                    # 启动为 MCP 服务器
fast-agent mcp-server --transport stdio  # 指定传输方式
fast-agent mcp-server --agent <name>     # 指定代理
```

### 环境变量

#### 配置环境变量

```bash
# 基本配置
export FAST_AGENT_CONFIG_FILE="/path/to/config.yaml"
export FAST_AGENT_LOG_LEVEL="INFO"
export FAST_AGENT_DEBUG="true"

# API 密钥
export ANTHROPIC_API_KEY="your_key"
export OPENAI_API_KEY="your_key"
export AZURE_OPENAI_API_KEY="your_key"
export GOOGLE_API_KEY="your_key"
export GROQ_API_KEY="your_key"
export DEEPSEEK_API_KEY="your_key"

# 模型配置
export FAST_AGENT_DEFAULT_MODEL="anthropic.claude-3-sonnet-latest"
export FAST_AGENT_TEMPERATURE="0.7"
export FAST_AGENT_MAX_TOKENS="4000"

# MCP 配置
export FAST_AGENT_MCP_TIMEOUT="30"
export FAST_AGENT_MCP_RETRY_ATTEMPTS="3"

# 性能配置
export FAST_AGENT_CACHE_ENABLED="true"
export FAST_AGENT_CACHE_TTL="3600"
export FAST_AGENT_MAX_CONCURRENT="10"

# 安全配置
export FAST_AGENT_ALLOWED_HOSTS="localhost,127.0.0.1"
export FAST_AGENT_CORS_ORIGINS="*"
export FAST_AGENT_API_KEY_REQUIRED="false"
```

### 类型定义

#### 核心类型

```python
from typing import Dict, List, Any, Optional, Union, Callable, AsyncGenerator
from dataclasses import dataclass
from enum import Enum

# 消息类型
@dataclass
class Message:
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None

# 工具定义
@dataclass
class Tool:
    name: str
    description: str
    parameters: Dict[str, Any]
    function: Optional[Callable] = None

# 模型配置
@dataclass
class ModelConfig:
    provider: str
    model: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    timeout: Optional[int] = None

# 工作流步骤
@dataclass
class WorkflowStep:
    agent: str
    input_key: str
    output_key: str
    conditions: Optional[List[str]] = None
    error_handling: Optional[Dict[str, Any]] = None

# 工作流类型
class WorkflowType(Enum):
    CHAIN = "chain"
    PARALLEL = "parallel"
    HUMAN_INPUT = "human_input"
    EVALUATOR_OPTIMIZER = "evaluator_optimizer"
    ROUTER = "router"
    ORCHESTRATOR = "orchestrator"

# MCP 传输类型
class MCPTransport(Enum):
    STDIO = "stdio"
    HTTP = "http"
    SSE = "sse"

# 响应类型
ResponseType = Union[str, Dict[str, Any], List[Any]]
StreamResponse = AsyncGenerator[str, None]
```

### 配置模式

#### YAML 配置模式

```yaml
# fastagent.config.yaml 完整模式
default_model: string                    # 默认模型
auto_sampling: boolean                   # 自动采样
temperature: number                      # 默认温度
max_tokens: integer                      # 默认最大令牌

# 模型提供商配置
anthropic:
  api_key: string
  base_url: string
  timeout: integer
  max_retries: integer

openai:
  api_key: string
  organization: string
  base_url: string
  timeout: integer

azure_openai:
  api_key: string
  endpoint: string
  api_version: string
  deployment_name: string

# MCP 服务器配置
mcp:
  servers:
    server_name:
      transport: "stdio" | "http" | "sse"
      command: string
      args: [string]
      env: {string: string}
      cwd: string
      timeout: integer
      retry_attempts: integer

# Elicitations 配置
elicitations:
  forms:
    form_name:
      title: string
      description: string
      fields:
        field_name:
          type: "text" | "number" | "select" | "checkbox"
          label: string
          required: boolean
          options: [string]  # for select type
          default: any

# 日志配置
logging:
  level: "DEBUG" | "INFO" | "WARNING" | "ERROR"
  format: "text" | "json"
  file: string
  max_size: string
  backup_count: integer

# 性能配置
performance:
  cache:
    enabled: boolean
    backend: "memory" | "redis" | "file"
    ttl: integer
    max_size: integer
  
  connection_pool:
    max_connections: integer
    max_keepalive_connections: integer
    keepalive_expiry: integer
  
  timeouts:
    connect: integer
    read: integer
    total: integer
  
  concurrency:
    max_concurrent_requests: integer
    semaphore_size: integer

# 安全配置
security:
  allowed_hosts: [string]
  cors_origins: [string]
  api_key_required: boolean
  rate_limiting:
    requests_per_minute: integer
    burst_size: integer
```

## 总结

本 API 参考文档涵盖了 `fast-agent` 的所有核心功能：

1. **核心类**：Agent、Workflow、Config 等主要类的详细 API
2. **方法和属性**：所有公共方法的参数、返回值和使用示例
3. **异常处理**：完整的异常类层次结构和处理策略
4. **高级功能**：批处理、缓存、插件等高级特性
5. **命令行接口**：所有 CLI 命令和选项
6. **配置管理**：环境变量和配置文件的完整参考
7. **类型定义**：TypeScript 风格的类型注解

这个参考文档可以作为开发时的快速查询手册，帮助您充分利用 `fast-agent` 的所有功能。

---

**教程系列完成！** 🎉

您现在已经掌握了 `fast-agent` 的完整知识体系，从基础入门到高级应用，从配置管理到故障排除，应有尽有。开始构建您的智能代理应用吧！