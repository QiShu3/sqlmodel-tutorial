# 第五章：配置参考和高级设置

## 配置文件概述

fast-agent 可以通过 `fastagent.config.yaml` 文件进行配置，该文件应放置在项目的根目录中。对于敏感信息，您可以使用具有相同结构的 `fastagent.secrets.yaml` - 两个文件的值将被合并，密钥文件优先。

## 配置文件位置

fast-agent 自动在当前工作目录及其父目录中搜索配置文件。您也可以使用 `--config` 命令行参数指定配置文件路径。

```bash
# 指定自定义配置文件
fast-agent --config /path/to/custom-config.yaml
```

## 环境变量配置

配置也可以通过环境变量提供，命名模式为 `SECTION__SUBSECTION__PROPERTY`（注意双下划线）：

```bash
# 示例
export DEFAULT_MODEL="haiku"
export ANTHROPIC__API_KEY="your_key"
export MCP__SERVERS__FETCH__COMMAND="uvx"
```

## 通用设置

### 基本配置

```yaml
# 所有代理的默认模型
default_model: "haiku"  # 格式：provider.model_name.reasoning_effort

# 是否自动启用采样。模型选择优先级是 Agent > Default
auto_sampling: true

# 执行引擎（目前仅支持 asyncio）
execution_engine: "asyncio"
```

### 模型配置示例

```yaml
# 默认模型设置
default_model: "anthropic.claude-3-7-sonnet-latest"

# 自动采样设置
auto_sampling: true

# 推理努力设置
reasoning_effort: "medium"  # "low", "medium", "high", "minimal"
```

## 模型提供商配置

### Anthropic 配置

```yaml
anthropic:
  api_key: "your_anthropic_key"  # 也可以使用 ANTHROPIC_API_KEY 环境变量
  base_url: "https://api.anthropic.com/v1"  # 可选，仅在需要覆盖时包含
```

### OpenAI 配置

```yaml
openai:
  api_key: "your_openai_key"  # 也可以使用 OPENAI_API_KEY 环境变量
  base_url: "https://api.openai.com/v1"  # 可选，仅在需要覆盖时包含
  reasoning_effort: "medium"  # 默认推理努力："low", "medium", "high"
```

### Azure OpenAI 配置

#### 选项 1：使用 resource_name 和 api_key

```yaml
azure:
  api_key: "your_azure_openai_key"  # 除非使用 DefaultAzureCredential，否则必需
  resource_name: "your-resource-name"  # Azure 中的资源名称
  azure_deployment: "deployment-name"  # 必需 - Azure 的部署名称
  api_version: "2023-05-15"  # 可选 API 版本
  # 如果使用 resource_name，请不要包含 base_url
```

#### 选项 2：使用 base_url 和 api_key

```yaml
azure:
  api_key: "your_azure_openai_key"
  base_url: "https://your-endpoint.openai.azure.com/"
  azure_deployment: "deployment-name"
  api_version: "2023-05-15"
  # 如果使用 base_url，请不要包含 resource_name
```

#### 选项 3：使用 DefaultAzureCredential

```yaml
azure:
  use_default_azure_credential: true
  base_url: "https://your-endpoint.openai.azure.com/"
  azure_deployment: "deployment-name"
  api_version: "2023-05-15"
  # 在此模式下不要包含 api_key 或 resource_name
```

### 其他提供商配置

```yaml
# DeepSeek
deepseek:
  api_key: "your_deepseek_key"
  base_url: "https://api.deepseek.com/v1"

# Google
google:
  api_key: "your_google_key"
  base_url: "https://generativelanguage.googleapis.com/v1beta/openai"

# Generic (Ollama)
generic:
  api_key: "ollama"
  base_url: "http://localhost:11434/v1"

# OpenRouter
openrouter:
  api_key: "your_openrouter_key"
  base_url: "https://openrouter.ai/api/v1"

# TensorZero
tensorzero:
  base_url: "http://localhost:3000"

# AWS Bedrock
bedrock:
  region: "us-east-1"
  profile: "default"
```

## MCP 服务器配置

### STDIO 服务器配置

```yaml
mcp:
  servers:
    # 基本 STDIO 服务器
    fetch:
      transport: "stdio"
      command: "uvx"
      args: ["mcp-server-fetch"]
      read_timeout_seconds: 60  # 可选超时（秒）
      env:  # 可选环境变量
        DEBUG: "true"
        API_KEY: "your_api_key"
      
    # 带采样的服务器
    advanced_server:
      transport: "stdio"
      command: "npx"
      args: ["@package/server-name"]
      sampling:  # 可选采样设置
        model: "haiku"  # 用于采样请求的模型
      cwd: "/path/to/working/directory"  # 可选工作目录
```

### HTTP 服务器配置

```yaml
mcp:
  servers:
    # Streamable HTTP 服务器
    remote_server:
      transport: "http"
      url: "http://localhost:8000/mcp"
      read_transport_sse_timeout_seconds: 300  # HTTP 连接超时
      headers:  # 可选头部
        Authorization: "Bearer your_token"
        Content-Type: "application/json"
      
    # HTTPS 服务器
    secure_server:
      transport: "http"
      url: "https://api.example.com/mcp"
      headers:
        Authorization: "Bearer your_token"
        User-Agent: "fast-agent/1.0"
```

### SSE 服务器配置

```yaml
mcp:
  servers:
    sse_server:
      transport: "sse"
      url: "http://localhost:8080/sse"
      read_transport_sse_timeout_seconds: 300
      headers:
        Authorization: "Bearer token"
```

## Elicitations 配置

### 基本 Elicitations 设置

```yaml
mcp:
  servers:
    elicitation_server:
      command: "uv"
      args: ["run", "elicitation_server.py"]
      transport: "stdio"
      elicitation:
        mode: "forms"  # "forms", "auto-cancel", "none"
        timeout_seconds: 300  # 可选超时
        max_retries: 3  # 可选最大重试次数
```

### Elicitation 模式详解

```yaml
# 表单模式（默认）- 显示交互式表单
elicitation:
  mode: "forms"
  form_config:
    theme: "default"  # 表单主题
    validation: true  # 启用实时验证
    navigation: "tab"  # 导航方式："tab", "arrow", "both"

# 自动取消模式 - 宣传功能但自动取消请求
elicitation:
  mode: "auto-cancel"
  cancel_message: "Elicitation automatically cancelled"

# 禁用模式 - 不宣传 Elicitation 功能
elicitation:
  mode: "none"
```

## 高级配置选项

### 日志配置

```yaml
logging:
  level: "INFO"  # "DEBUG", "INFO", "WARNING", "ERROR"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: "fast-agent.log"  # 可选日志文件
  max_size: "10MB"  # 日志文件最大大小
  backup_count: 5  # 保留的备份文件数量
```

### 性能配置

```yaml
performance:
  max_concurrent_requests: 10  # 最大并发请求数
  request_timeout: 300  # 请求超时（秒）
  retry_attempts: 3  # 重试次数
  retry_delay: 1  # 重试延迟（秒）
  
  # 连接池设置
  connection_pool:
    max_connections: 100
    max_keepalive_connections: 20
    keepalive_expiry: 5
```

### 安全配置

```yaml
security:
  # API 密钥轮换
  api_key_rotation:
    enabled: true
    interval_hours: 24
  
  # 请求验证
  request_validation:
    enabled: true
    max_request_size: "10MB"
    allowed_content_types: ["application/json", "text/plain"]
  
  # SSL/TLS 设置
  tls:
    verify_ssl: true
    ca_bundle: "/path/to/ca-bundle.crt"
    client_cert: "/path/to/client.crt"
    client_key: "/path/to/client.key"
```

### 缓存配置

```yaml
caching:
  enabled: true
  backend: "memory"  # "memory", "redis", "file"
  ttl: 3600  # 缓存生存时间（秒）
  max_size: 1000  # 最大缓存条目数
  
  # Redis 配置（如果使用 Redis 后端）
  redis:
    host: "localhost"
    port: 6379
    db: 0
    password: "your_redis_password"
  
  # 文件缓存配置
  file:
    directory: "/tmp/fast-agent-cache"
    max_file_size: "100MB"
```

## 开发和调试配置

### 开发模式设置

```yaml
development:
  debug: true
  hot_reload: true  # 代码更改时自动重新加载
  verbose_logging: true
  
  # 测试模式
  testing:
    mock_llm: true  # 使用模拟 LLM
    record_interactions: true  # 记录交互用于回放
    playback_file: "interactions.json"
```

### 监控和指标

```yaml
monitoring:
  enabled: true
  metrics:
    endpoint: "/metrics"
    port: 9090
    format: "prometheus"  # "prometheus", "json"
  
  health_check:
    endpoint: "/health"
    interval: 30  # 健康检查间隔（秒）
  
  tracing:
    enabled: true
    service_name: "fast-agent"
    jaeger_endpoint: "http://localhost:14268/api/traces"
```

## 部署配置

### 生产环境设置

```yaml
production:
  # 服务器设置
  server:
    host: "0.0.0.0"
    port: 8000
    workers: 4
    max_requests: 1000
    max_requests_jitter: 100
  
  # 负载均衡
  load_balancing:
    strategy: "round_robin"  # "round_robin", "least_connections", "weighted"
    health_check_interval: 30
  
  # 自动扩缩容
  autoscaling:
    enabled: true
    min_instances: 2
    max_instances: 10
    cpu_threshold: 70
    memory_threshold: 80
```

### Docker 配置

```yaml
docker:
  image: "fast-agent:latest"
  container_name: "fast-agent-app"
  
  # 资源限制
  resources:
    memory: "2G"
    cpu: "1.0"
  
  # 环境变量
  environment:
    - "ENVIRONMENT=production"
    - "LOG_LEVEL=INFO"
  
  # 卷挂载
  volumes:
    - "./config:/app/config"
    - "./logs:/app/logs"
```

## 配置验证

### 配置检查命令

```bash
# 检查配置文件语法
fast-agent config validate

# 检查 API 密钥
fast-agent check

# 测试 MCP 服务器连接
fast-agent test-servers

# 显示当前配置
fast-agent config show
```

### 配置模板生成

```bash
# 生成基本配置模板
fast-agent config init

# 生成特定提供商的配置
fast-agent config init --provider anthropic

# 生成完整配置示例
fast-agent config init --full
```

## 最佳实践

### 配置管理

1. **分离敏感信息**：使用 `fastagent.secrets.yaml` 存储 API 密钥
2. **环境特定配置**：为不同环境创建不同的配置文件
3. **版本控制**：将配置文件（除密钥文件外）纳入版本控制
4. **文档化**：为自定义配置添加注释说明

### 安全考虑

1. **密钥轮换**：定期轮换 API 密钥
2. **权限最小化**：只授予必要的权限
3. **加密传输**：在生产环境中使用 HTTPS
4. **审计日志**：启用详细的审计日志

### 性能优化

1. **连接池**：配置适当的连接池大小
2. **缓存策略**：根据使用模式配置缓存
3. **超时设置**：设置合理的超时值
4. **资源限制**：配置适当的资源限制

## 故障排除

### 常见配置问题

1. **YAML 语法错误**：使用 YAML 验证器检查语法
2. **路径问题**：确保文件路径正确且可访问
3. **权限问题**：检查文件和目录权限
4. **环境变量冲突**：检查环境变量是否覆盖了配置文件设置

### 调试技巧

```bash
# 启用详细日志
fast-agent --verbose

# 检查配置加载
fast-agent config debug

# 测试特定组件
fast-agent test --component mcp-servers
```

## 下一步

配置好系统后，下一章将介绍部署和运行的高级特性。