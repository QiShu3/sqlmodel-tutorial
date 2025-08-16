# 第六章：部署和运行

## 运行模式概述

fast-agent 提供多种运行模式，适应不同的使用场景：

1. **交互模式**：直接与代理对话
2. **命令行执行**：一次性执行任务
3. **MCP 服务器部署**：作为 MCP 服务器运行
4. **Python 程序集成**：嵌入到 Python 应用中
5. **Web 服务部署**：作为 HTTP API 服务运行

## 交互模式

### 基本交互

```bash
# 启动交互式会话
fast-agent

# 使用特定代理
fast-agent --agent my_agent

# 使用特定配置文件
fast-agent --config custom-config.yaml

# 启用详细输出
fast-agent --verbose
```

### 交互式选项

```bash
# 设置默认模型
fast-agent --model anthropic.claude-3-sonnet-latest

# 启用自动采样
fast-agent --auto-sampling

# 设置推理努力
fast-agent --reasoning-effort high

# 指定工作目录
fast-agent --cwd /path/to/project
```

### 会话管理

```bash
# 保存会话
fast-agent --save-session session_name

# 加载会话
fast-agent --load-session session_name

# 列出保存的会话
fast-agent --list-sessions

# 删除会话
fast-agent --delete-session session_name
```

## 命令行执行

### 单次执行

```bash
# 执行单个提示
fast-agent "分析这个文件的内容" --file data.txt

# 使用管道输入
echo "Hello, world!" | fast-agent "翻译成中文"

# 处理多个文件
fast-agent "总结这些文档" --files *.md
```

### 批处理模式

```bash
# 从文件读取任务列表
fast-agent --batch tasks.txt

# 并行处理
fast-agent --batch tasks.txt --parallel 4

# 输出到文件
fast-agent "生成报告" --output report.md
```

### 脚本集成

```bash
#!/bin/bash
# 自动化脚本示例

# 设置环境
export ANTHROPIC_API_KEY="your_key"

# 处理输入文件
for file in *.txt; do
    echo "处理文件: $file"
    fast-agent "分析并总结" --file "$file" --output "summary_${file%.txt}.md"
done

# 生成最终报告
fast-agent "基于所有总结生成最终报告" --files summary_*.md --output final_report.md
```

## MCP 服务器部署

### 作为 MCP 服务器运行

```bash
# 启动 MCP 服务器
fast-agent serve-mcp

# 指定端口
fast-agent serve-mcp --port 8080

# 指定主机
fast-agent serve-mcp --host 0.0.0.0 --port 8080

# 使用特定代理
fast-agent serve-mcp --agent my_agent
```

### MCP 服务器配置

```yaml
# fastagent.config.yaml
mcp_server:
  host: "0.0.0.0"
  port: 8080
  max_connections: 100
  timeout: 300
  
  # 认证设置
  auth:
    enabled: true
    api_key: "your_api_key"
    
  # CORS 设置
  cors:
    enabled: true
    origins: ["*"]
    methods: ["GET", "POST"]
    headers: ["*"]
```

### 客户端连接示例

```python
# Python 客户端
import asyncio
from mcp import ClientSession, StdioServerParameters

async def main():
    # 连接到 fast-agent MCP 服务器
    server_params = StdioServerParameters(
        command="fast-agent",
        args=["serve-mcp", "--agent", "my_agent"]
    )
    
    async with ClientSession(server_params) as session:
        # 初始化
        await session.initialize()
        
        # 调用工具
        result = await session.call_tool(
            "process_text",
            {"text": "Hello, world!", "task": "translate to Chinese"}
        )
        print(result)

if __name__ == "__main__":
    asyncio.run(main())
```

## Python 程序集成

### 基本集成

```python
from fastagent import Agent, Workflow

# 创建代理
agent = Agent(
    instructions="你是一个有用的助手",
    model="anthropic.claude-3-sonnet-latest"
)

# 发送消息
response = agent.send("你好，请介绍一下自己")
print(response)

# 交互式会话
for message in agent.interactive():
    user_input = input("用户: ")
    if user_input.lower() == 'quit':
        break
    response = agent.send(user_input)
    print(f"助手: {response}")
```

### 异步集成

```python
import asyncio
from fastagent import AsyncAgent

async def main():
    agent = AsyncAgent(
        instructions="你是一个代码分析专家",
        model="anthropic.claude-3-sonnet-latest"
    )
    
    # 异步发送消息
    response = await agent.send("分析这段代码的复杂度")
    print(response)
    
    # 流式响应
    async for chunk in agent.stream("解释这个算法"):
        print(chunk, end="", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
```

### 工作流集成

```python
from fastagent import Workflow, Agent

# 定义工作流
workflow = Workflow([
    Agent(
        name="analyzer",
        instructions="分析输入文本的情感",
        model="haiku"
    ),
    Agent(
        name="summarizer",
        instructions="基于分析结果生成摘要",
        model="sonnet"
    )
])

# 执行工作流
result = workflow.run("今天天气真好，我很开心！")
print(result)
```

## Web 服务部署

### FastAPI 集成

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastagent import Agent

app = FastAPI(title="Fast-Agent API")

# 初始化代理
agent = Agent(
    instructions="你是一个API助手",
    model="anthropic.claude-3-sonnet-latest"
)

class ChatRequest(BaseModel):
    message: str
    model: str = None

class ChatResponse(BaseModel):
    response: str
    model_used: str

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        if request.model:
            agent.model = request.model
        
        response = await agent.send(request.message)
        return ChatResponse(
            response=response,
            model_used=agent.model
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### Flask 集成

```python
from flask import Flask, request, jsonify
from fastagent import Agent

app = Flask(__name__)

# 初始化代理
agent = Agent(
    instructions="你是一个Flask API助手",
    model="anthropic.claude-3-sonnet-latest"
)

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        message = data.get('message')
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        response = agent.send(message)
        return jsonify({
            'response': response,
            'model': agent.model
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False)
```

## Docker 部署

### Dockerfile

```dockerfile
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建非 root 用户
RUN useradd -m -u 1000 fastuser && chown -R fastuser:fastuser /app
USER fastuser

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动命令
CMD ["fast-agent", "serve", "--host", "0.0.0.0", "--port", "8000"]
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  fast-agent:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - LOG_LEVEL=INFO
    volumes:
      - ./config:/app/config:ro
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - fast-agent
    restart: unless-stopped

volumes:
  redis_data:
```

### 构建和运行

```bash
# 构建镜像
docker build -t fast-agent:latest .

# 运行容器
docker run -d \
  --name fast-agent \
  -p 8000:8000 \
  -e ANTHROPIC_API_KEY="your_key" \
  -v $(pwd)/config:/app/config \
  fast-agent:latest

# 使用 docker-compose
docker-compose up -d

# 查看日志
docker-compose logs -f fast-agent

# 停止服务
docker-compose down
```

## Kubernetes 部署

### Deployment 配置

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fast-agent
  labels:
    app: fast-agent
spec:
  replicas: 3
  selector:
    matchLabels:
      app: fast-agent
  template:
    metadata:
      labels:
        app: fast-agent
    spec:
      containers:
      - name: fast-agent
        image: fast-agent:latest
        ports:
        - containerPort: 8000
        env:
        - name: ANTHROPIC_API_KEY
          valueFrom:
            secretKeyRef:
              name: fast-agent-secrets
              key: anthropic-api-key
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: fast-agent-secrets
              key: openai-api-key
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        volumeMounts:
        - name: config
          mountPath: /app/config
          readOnly: true
      volumes:
      - name: config
        configMap:
          name: fast-agent-config
```

### Service 配置

```yaml
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: fast-agent-service
spec:
  selector:
    app: fast-agent
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8000
  type: LoadBalancer
```

### ConfigMap 和 Secret

```yaml
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fast-agent-config
data:
  fastagent.config.yaml: |
    default_model: "anthropic.claude-3-sonnet-latest"
    auto_sampling: true
    execution_engine: "asyncio"
    
    logging:
      level: "INFO"
      format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

---
apiVersion: v1
kind: Secret
metadata:
  name: fast-agent-secrets
type: Opaque
data:
  anthropic-api-key: <base64-encoded-key>
  openai-api-key: <base64-encoded-key>
```

### 部署命令

```bash
# 创建命名空间
kubectl create namespace fast-agent

# 应用配置
kubectl apply -f configmap.yaml -n fast-agent
kubectl apply -f deployment.yaml -n fast-agent
kubectl apply -f service.yaml -n fast-agent

# 检查部署状态
kubectl get pods -n fast-agent
kubectl get services -n fast-agent

# 查看日志
kubectl logs -f deployment/fast-agent -n fast-agent

# 扩缩容
kubectl scale deployment fast-agent --replicas=5 -n fast-agent
```

## 监控和日志

### 日志配置

```yaml
# fastagent.config.yaml
logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  handlers:
    - type: "file"
      filename: "fast-agent.log"
      max_bytes: 10485760  # 10MB
      backup_count: 5
    - type: "console"
      stream: "stdout"
    - type: "syslog"
      address: "localhost:514"
      facility: "local0"
```

### Prometheus 监控

```python
# 添加 Prometheus 指标
from prometheus_client import Counter, Histogram, Gauge, start_http_server

# 定义指标
REQUEST_COUNT = Counter('fast_agent_requests_total', 'Total requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('fast_agent_request_duration_seconds', 'Request duration')
ACTIVE_CONNECTIONS = Gauge('fast_agent_active_connections', 'Active connections')

# 在应用中使用
@REQUEST_DURATION.time()
def process_request(request):
    REQUEST_COUNT.labels(method=request.method, endpoint=request.path).inc()
    # 处理请求逻辑
    return response

# 启动指标服务器
start_http_server(9090)
```

### Grafana 仪表板

```json
{
  "dashboard": {
    "title": "Fast-Agent Monitoring",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(fast_agent_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ]
      },
      {
        "title": "Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(fast_agent_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          }
        ]
      }
    ]
  }
}
```

## 性能优化

### 连接池优化

```python
# 配置连接池
import aiohttp
from fastagent import Agent

# 创建自定义连接器
connector = aiohttp.TCPConnector(
    limit=100,  # 总连接数限制
    limit_per_host=30,  # 每个主机的连接数限制
    ttl_dns_cache=300,  # DNS 缓存 TTL
    use_dns_cache=True,
    keepalive_timeout=30,
    enable_cleanup_closed=True
)

# 使用自定义连接器创建代理
agent = Agent(
    instructions="优化的代理",
    model="anthropic.claude-3-sonnet-latest",
    connector=connector
)
```

### 缓存策略

```python
from functools import lru_cache
import redis

# 内存缓存
@lru_cache(maxsize=1000)
def cached_response(prompt_hash):
    # 缓存响应逻辑
    pass

# Redis 缓存
redis_client = redis.Redis(host='localhost', port=6379, db=0)

def get_cached_response(prompt):
    cache_key = f"response:{hash(prompt)}"
    cached = redis_client.get(cache_key)
    if cached:
        return cached.decode('utf-8')
    return None

def set_cached_response(prompt, response, ttl=3600):
    cache_key = f"response:{hash(prompt)}"
    redis_client.setex(cache_key, ttl, response)
```

### 负载均衡

```python
# 简单的轮询负载均衡
class LoadBalancer:
    def __init__(self, agents):
        self.agents = agents
        self.current = 0
    
    def get_agent(self):
        agent = self.agents[self.current]
        self.current = (self.current + 1) % len(self.agents)
        return agent
    
    async def send(self, message):
        agent = self.get_agent()
        return await agent.send(message)

# 使用负载均衡器
agents = [
    Agent(model="anthropic.claude-3-sonnet-latest"),
    Agent(model="openai.gpt-4"),
    Agent(model="anthropic.claude-3-haiku-latest")
]

balancer = LoadBalancer(agents)
response = await balancer.send("Hello, world!")
```

## 故障排除

### 常见问题

1. **端口占用**
```bash
# 检查端口使用情况
netstat -tulpn | grep :8000

# 杀死占用端口的进程
kill -9 $(lsof -t -i:8000)
```

2. **内存不足**
```bash
# 监控内存使用
top -p $(pgrep fast-agent)

# 设置内存限制
ulimit -m 2097152  # 2GB
```

3. **API 限制**
```python
# 实现重试机制
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
async def send_with_retry(agent, message):
    return await agent.send(message)
```

### 调试工具

```bash
# 启用调试模式
fast-agent --debug

# 检查配置
fast-agent config validate

# 测试连接
fast-agent test-connection

# 性能分析
fast-agent profile --duration 60
```

## 下一步

部署完成后，下一章将介绍实践示例和最佳实践。