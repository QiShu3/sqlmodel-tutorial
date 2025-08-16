# 第八章：故障排除和常见问题

## 常见问题诊断

### 1. 安装和配置问题

#### 问题：fast-agent 命令未找到

**症状**：
```bash
$ fast-agent
bash: fast-agent: command not found
```

**解决方案**：
```bash
# 检查是否已安装
pip list | grep fast-agent

# 如果未安装，进行安装
pip install fast-agent

# 或使用 uv
uv add fast-agent

# 检查 PATH 环境变量
echo $PATH

# 如果使用虚拟环境，确保已激活
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows
```

#### 问题：配置文件未找到

**症状**：
```
Error: Configuration file 'fastagent.config.yaml' not found
```

**解决方案**：
```bash
# 检查当前目录
ls -la | grep fastagent

# 创建基本配置文件
fast-agent config init

# 或手动创建
cat > fastagent.config.yaml << EOF
default_model: "anthropic.claude-3-haiku-latest"
auto_sampling: true

anthropic:
  api_key: "${ANTHROPIC_API_KEY}"
EOF

# 验证配置
fast-agent config validate
```

#### 问题：API 密钥配置错误

**症状**：
```
AuthenticationError: Invalid API key
```

**解决方案**：
```bash
# 检查环境变量
echo $ANTHROPIC_API_KEY
echo $OPENAI_API_KEY

# 设置环境变量
export ANTHROPIC_API_KEY="your_actual_key"
export OPENAI_API_KEY="your_actual_key"

# 或在配置文件中设置
cat > fastagent.secrets.yaml << EOF
anthropic:
  api_key: "your_actual_key"
openai:
  api_key: "your_actual_key"
EOF

# 测试连接
fast-agent check
```

### 2. 模型和提供商问题

#### 问题：模型不可用

**症状**：
```
ModelNotFoundError: Model 'gpt-5' not found
```

**解决方案**：
```bash
# 列出可用模型
fast-agent models list

# 检查提供商配置
fast-agent config show

# 使用正确的模型名称
# OpenAI: gpt-4, gpt-3.5-turbo
# Anthropic: claude-3-sonnet-latest, claude-3-haiku-latest
# 更新配置
fast-agent config set default_model "anthropic.claude-3-sonnet-latest"
```

#### 问题：速率限制

**症状**：
```
RateLimitError: Rate limit exceeded. Please try again later.
```

**解决方案**：
```yaml
# 在配置文件中添加重试设置
retry:
  max_attempts: 5
  backoff_strategy: "exponential"
  base_delay: 2
  max_delay: 120
  
  # 速率限制处理
  rate_limit:
    requests_per_minute: 50
    tokens_per_minute: 40000
    concurrent_requests: 5
```

```python
# 在代码中实现退避策略
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type(RateLimitError)
)
async def send_with_backoff(agent, message):
    return await agent.send(message)
```

### 3. MCP 服务器问题

#### 问题：MCP 服务器启动失败

**症状**：
```
MCPServerError: Failed to start server 'filesystem'
```

**诊断步骤**：
```bash
# 检查 MCP 服务器配置
fast-agent config show | grep -A 10 mcp

# 手动测试 MCP 服务器
uvx mcp-server-filesystem

# 检查依赖
pip list | grep mcp

# 检查权限
ls -la /path/to/mcp/server
```

**解决方案**：
```yaml
# 更新 MCP 配置
mcp:
  servers:
    filesystem:
      transport: "stdio"
      command: "uvx"
      args: ["mcp-server-filesystem"]
      read_timeout_seconds: 30
      env:
        ALLOWED_DIRECTORIES: "/safe/directory"
      cwd: "/working/directory"
```

#### 问题：MCP 工具调用失败

**症状**：
```
MCPToolError: Tool 'read_file' not available
```

**解决方案**：
```bash
# 列出可用工具
fast-agent mcp list-tools

# 测试特定工具
fast-agent mcp test-tool read_file --args '{"path": "/test/file.txt"}'

# 检查工具权限
fast-agent mcp check-permissions
```

### 4. 性能问题

#### 问题：响应时间过长

**诊断**：
```bash
# 启用性能分析
fast-agent --profile

# 检查网络延迟
ping api.anthropic.com
ping api.openai.com

# 监控资源使用
top -p $(pgrep fast-agent)
```

**优化方案**：
```yaml
# 配置连接池
performance:
  connection_pool:
    max_connections: 50
    max_keepalive_connections: 10
    keepalive_expiry: 5
  
  # 超时设置
  timeouts:
    connect: 10
    read: 60
    total: 120
  
  # 并发控制
  concurrency:
    max_concurrent_requests: 10
    semaphore_size: 5
```

```python
# 实现缓存
from functools import lru_cache
import hashlib

class ResponseCache:
    def __init__(self, max_size=1000, ttl=3600):
        self.cache = {}
        self.max_size = max_size
        self.ttl = ttl
    
    def get_key(self, prompt, model):
        content = f"{model}:{prompt}"
        return hashlib.md5(content.encode()).hexdigest()
    
    async def get_or_compute(self, agent, prompt):
        key = self.get_key(prompt, agent.model)
        
        # 检查缓存
        if key in self.cache:
            cached_item = self.cache[key]
            if time.time() - cached_item['timestamp'] < self.ttl:
                return cached_item['response']
        
        # 计算新响应
        response = await agent.send(prompt)
        
        # 存储到缓存
        self.cache[key] = {
            'response': response,
            'timestamp': time.time()
        }
        
        return response
```

#### 问题：内存使用过高

**诊断**：
```bash
# 监控内存使用
ps aux | grep fast-agent

# 使用内存分析工具
python -m memory_profiler your_script.py

# 检查对象引用
import gc
print(len(gc.get_objects()))
```

**解决方案**：
```python
# 实现内存管理
import gc
import weakref
from typing import Dict, Any

class MemoryManager:
    def __init__(self, max_memory_mb=1000):
        self.max_memory_mb = max_memory_mb
        self.objects = weakref.WeakSet()
    
    def register_object(self, obj):
        self.objects.add(obj)
    
    def cleanup(self):
        # 强制垃圾回收
        gc.collect()
        
        # 检查内存使用
        import psutil
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        
        if memory_mb > self.max_memory_mb:
            # 清理缓存
            self._clear_caches()
            gc.collect()
    
    def _clear_caches(self):
        # 清理各种缓存
        for obj in self.objects:
            if hasattr(obj, 'clear_cache'):
                obj.clear_cache()
```

### 5. 网络和连接问题

#### 问题：连接超时

**症状**：
```
TimeoutError: Request timed out after 30 seconds
```

**解决方案**：
```yaml
# 调整超时设置
timeouts:
  connect: 30      # 连接超时
  read: 120        # 读取超时
  total: 180       # 总超时
  
# 重试配置
retry:
  max_attempts: 3
  timeout_retry: true
  backoff_strategy: "exponential"
```

#### 问题：SSL/TLS 错误

**症状**：
```
SSLError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed
```

**解决方案**：
```yaml
# SSL 配置
ssl:
  verify: true
  ca_bundle: "/path/to/ca-bundle.crt"
  client_cert: "/path/to/client.crt"
  client_key: "/path/to/client.key"
  
# 或临时禁用验证（不推荐用于生产）
ssl:
  verify: false
```

```python
# 在代码中处理 SSL
import ssl
import aiohttp

# 创建自定义 SSL 上下文
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# 使用自定义连接器
connector = aiohttp.TCPConnector(ssl=ssl_context)
```

### 6. 工作流问题

#### 问题：工作流执行失败

**症状**：
```
WorkflowError: Step 'analyzer' failed with error: Invalid input format
```

**诊断步骤**：
```bash
# 验证工作流配置
fast-agent workflow validate my_workflow.yaml

# 测试单个步骤
fast-agent test-step analyzer --input '{"text": "test"}'

# 启用详细日志
fast-agent --verbose workflow run my_workflow.yaml
```

**解决方案**：
```yaml
# 添加错误处理
name: "robust_workflow"
type: "chain"
steps:
  - agent: "analyzer"
    input_key: "text"
    output_key: "analysis"
    error_handling:
      on_failure: "continue"  # continue, stop, retry
      max_retries: 3
      fallback_value: "Analysis failed"
  
  - agent: "summarizer"
    input_key: "analysis"
    output_key: "summary"
    conditions:
      - "analysis != 'Analysis failed'"  # 条件执行
```

#### 问题：数据传递错误

**症状**：
```
DataFlowError: Key 'analysis_result' not found in workflow context
```

**解决方案**：
```yaml
# 明确定义数据流
name: "data_flow_workflow"
type: "chain"
data_mapping:
  input_schema:
    text: "string"
    options: "object"
  
  output_schema:
    result: "string"
    metadata: "object"

steps:
  - agent: "processor"
    inputs:
      content: "${text}"           # 从输入映射
      config: "${options.config}"  # 嵌套访问
    outputs:
      processed_text: "analysis_result"  # 输出映射
  
  - agent: "formatter"
    inputs:
      data: "${analysis_result}"   # 从上一步获取
    outputs:
      formatted: "result"
```

### 7. 调试工具和技巧

#### 启用调试模式

```bash
# 全局调试
export FAST_AGENT_DEBUG=true
fast-agent --debug

# 特定组件调试
fast-agent --debug-components mcp,workflow,agent

# 详细日志
fast-agent --log-level DEBUG
```

#### 使用调试代理

```python
# 创建调试代理
from fastagent import Agent
import logging

class DebugAgent(Agent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger(f"DebugAgent.{self.name}")
        self.logger.setLevel(logging.DEBUG)
    
    async def send(self, message, **kwargs):
        self.logger.debug(f"Input: {message[:100]}...")
        
        try:
            response = await super().send(message, **kwargs)
            self.logger.debug(f"Output: {response[:100]}...")
            return response
        except Exception as e:
            self.logger.error(f"Error: {e}")
            raise

# 使用调试代理
debug_agent = DebugAgent(
    instructions="Debug assistant",
    model="anthropic.claude-3-haiku-latest"
)
```

#### 性能分析

```python
# 性能分析装饰器
import time
import functools
from typing import Callable, Any

def profile_performance(func: Callable) -> Callable:
    @functools.wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        start_time = time.time()
        
        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start_time
            
            print(f"Function {func.__name__} took {duration:.2f} seconds")
            return result
        except Exception as e:
            duration = time.time() - start_time
            print(f"Function {func.__name__} failed after {duration:.2f} seconds: {e}")
            raise
    
    return wrapper

# 使用装饰器
@profile_performance
async def slow_operation():
    # 模拟慢操作
    await asyncio.sleep(2)
    return "Done"
```

### 8. 日志分析

#### 结构化日志查询

```bash
# 使用 jq 分析 JSON 日志
cat fast-agent.log | jq '.[] | select(.level == "ERROR")'

# 查找特定错误
cat fast-agent.log | jq '.[] | select(.error_type == "RateLimitError")'

# 性能分析
cat fast-agent.log | jq '.[] | select(.event_type == "performance") | .duration_seconds' | sort -n

# 统计错误类型
cat fast-agent.log | jq -r '.[] | select(.level == "ERROR") | .error_type' | sort | uniq -c
```

#### 日志聚合和监控

```python
# 简单的日志聚合器
import json
from collections import defaultdict, Counter
from datetime import datetime, timedelta

class LogAnalyzer:
    def __init__(self, log_file: str):
        self.log_file = log_file
        self.logs = []
        self._load_logs()
    
    def _load_logs(self):
        with open(self.log_file, 'r') as f:
            for line in f:
                try:
                    log_entry = json.loads(line)
                    self.logs.append(log_entry)
                except json.JSONDecodeError:
                    continue
    
    def get_error_summary(self, hours=24):
        """获取错误摘要"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        recent_errors = [
            log for log in self.logs
            if log.get('level') == 'ERROR' and 
               datetime.fromisoformat(log.get('timestamp', '')) > cutoff_time
        ]
        
        error_types = Counter(log.get('error_type') for log in recent_errors)
        
        return {
            'total_errors': len(recent_errors),
            'error_types': dict(error_types),
            'recent_errors': recent_errors[-10:]  # 最近10个错误
        }
    
    def get_performance_stats(self, operation: str = None):
        """获取性能统计"""
        perf_logs = [
            log for log in self.logs
            if log.get('event_type') == 'performance' and
               (operation is None or log.get('operation') == operation)
        ]
        
        if not perf_logs:
            return None
        
        durations = [log.get('duration_seconds', 0) for log in perf_logs]
        
        return {
            'count': len(durations),
            'avg_duration': sum(durations) / len(durations),
            'min_duration': min(durations),
            'max_duration': max(durations),
            'total_duration': sum(durations)
        }

# 使用分析器
analyzer = LogAnalyzer('fast-agent.log')
error_summary = analyzer.get_error_summary()
perf_stats = analyzer.get_performance_stats('agent_send')

print(f"Errors in last 24h: {error_summary['total_errors']}")
print(f"Average response time: {perf_stats['avg_duration']:.2f}s")
```

### 9. 健康检查和监控

#### 系统健康检查

```python
# 健康检查脚本
import asyncio
import aiohttp
import time
from typing import Dict, Any

class HealthChecker:
    def __init__(self):
        self.checks = {
            'api_connectivity': self._check_api_connectivity,
            'mcp_servers': self._check_mcp_servers,
            'memory_usage': self._check_memory_usage,
            'disk_space': self._check_disk_space,
        }
    
    async def run_all_checks(self) -> Dict[str, Any]:
        """运行所有健康检查"""
        results = {}
        
        for check_name, check_func in self.checks.items():
            try:
                start_time = time.time()
                result = await check_func()
                duration = time.time() - start_time
                
                results[check_name] = {
                    'status': 'healthy' if result['healthy'] else 'unhealthy',
                    'details': result,
                    'duration': duration
                }
            except Exception as e:
                results[check_name] = {
                    'status': 'error',
                    'error': str(e),
                    'duration': time.time() - start_time
                }
        
        return results
    
    async def _check_api_connectivity(self) -> Dict[str, Any]:
        """检查 API 连接"""
        endpoints = {
            'anthropic': 'https://api.anthropic.com/v1/messages',
            'openai': 'https://api.openai.com/v1/models'
        }
        
        results = {}
        all_healthy = True
        
        async with aiohttp.ClientSession() as session:
            for name, url in endpoints.items():
                try:
                    async with session.get(url, timeout=10) as response:
                        results[name] = {
                            'status_code': response.status,
                            'healthy': response.status < 500
                        }
                        if response.status >= 500:
                            all_healthy = False
                except Exception as e:
                    results[name] = {
                        'error': str(e),
                        'healthy': False
                    }
                    all_healthy = False
        
        return {
            'healthy': all_healthy,
            'endpoints': results
        }
    
    async def _check_mcp_servers(self) -> Dict[str, Any]:
        """检查 MCP 服务器"""
        # 实现 MCP 服务器健康检查
        return {'healthy': True, 'servers': []}
    
    async def _check_memory_usage(self) -> Dict[str, Any]:
        """检查内存使用"""
        import psutil
        
        memory = psutil.virtual_memory()
        threshold = 0.9  # 90% 阈值
        
        return {
            'healthy': memory.percent < threshold * 100,
            'usage_percent': memory.percent,
            'available_gb': memory.available / (1024**3),
            'threshold_percent': threshold * 100
        }
    
    async def _check_disk_space(self) -> Dict[str, Any]:
        """检查磁盘空间"""
        import shutil
        
        total, used, free = shutil.disk_usage('/')
        usage_percent = (used / total) * 100
        threshold = 90  # 90% 阈值
        
        return {
            'healthy': usage_percent < threshold,
            'usage_percent': usage_percent,
            'free_gb': free / (1024**3),
            'threshold_percent': threshold
        }

# 使用健康检查
async def main():
    checker = HealthChecker()
    results = await checker.run_all_checks()
    
    print("Health Check Results:")
    for check_name, result in results.items():
        status = result['status']
        duration = result.get('duration', 0)
        print(f"  {check_name}: {status} ({duration:.2f}s)")
        
        if status != 'healthy':
            print(f"    Details: {result}")

if __name__ == "__main__":
    asyncio.run(main())
```

### 10. 故障恢复策略

#### 自动重启机制

```python
# 自动重启装饰器
import asyncio
import functools
from typing import Callable, Any

def auto_restart(max_failures=3, restart_delay=5):
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            failures = 0
            
            while failures < max_failures:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    failures += 1
                    print(f"Function {func.__name__} failed (attempt {failures}/{max_failures}): {e}")
                    
                    if failures < max_failures:
                        print(f"Restarting in {restart_delay} seconds...")
                        await asyncio.sleep(restart_delay)
                    else:
                        print(f"Max failures reached for {func.__name__}")
                        raise
        
        return wrapper
    return decorator

# 使用自动重启
@auto_restart(max_failures=3, restart_delay=10)
async def critical_service():
    # 关键服务逻辑
    pass
```

#### 断路器模式

```python
# 断路器实现
import time
from enum import Enum
from typing import Callable, Any

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.timeout:
                self.state = CircuitState.HALF_OPEN
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _on_success(self):
        self.failure_count = 0
        self.state = CircuitState.CLOSED
    
    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN

# 使用断路器
breaker = CircuitBreaker(failure_threshold=3, timeout=30)

async def protected_api_call():
    return await breaker.call(some_unreliable_function)
```

## 总结

通过本章的故障排除指南，您应该能够：

1. **快速诊断问题**：使用系统化的方法识别问题根源
2. **解决常见问题**：处理配置、网络、性能等常见问题
3. **实施监控**：建立健康检查和日志分析机制
4. **提高系统可靠性**：实现自动重启和断路器等恢复策略
5. **优化性能**：识别和解决性能瓶颈

记住，良好的故障排除实践包括：
- 详细的日志记录
- 系统化的诊断方法
- 预防性监控
- 自动化的恢复机制
- 持续的性能优化

下一章将提供完整的 API 参考文档。