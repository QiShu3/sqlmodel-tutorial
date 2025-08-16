# 第七章：实践示例和最佳实践

## 实践示例

### 示例 1：文档分析助手

#### 项目结构
```
doc-analyzer/
├── fastagent.config.yaml
├── agents/
│   ├── analyzer.yaml
│   └── summarizer.yaml
├── workflows/
│   └── document_workflow.yaml
└── scripts/
    └── batch_process.py
```

#### 配置文件

```yaml
# fastagent.config.yaml
default_model: "anthropic.claude-3-sonnet-latest"
auto_sampling: true

anthropic:
  api_key: "${ANTHROPIC_API_KEY}"

mcp:
  servers:
    file_reader:
      transport: "stdio"
      command: "uvx"
      args: ["mcp-server-filesystem"]
      env:
        ALLOWED_DIRECTORIES: "/documents,/uploads"
```

#### 代理定义

```yaml
# agents/analyzer.yaml
name: "document_analyzer"
instructions: |
  你是一个专业的文档分析专家。你的任务是：
  1. 仔细阅读提供的文档内容
  2. 识别文档的类型、主题和关键信息
  3. 分析文档的结构和逻辑
  4. 提取重要的数据点和见解
  5. 评估文档的质量和完整性
  
  请以结构化的方式提供分析结果。
model: "anthropic.claude-3-sonnet-latest"
mcp_servers: ["file_reader"]
```

```yaml
# agents/summarizer.yaml
name: "document_summarizer"
instructions: |
  你是一个文档摘要专家。基于分析结果，你需要：
  1. 创建简洁而全面的文档摘要
  2. 突出关键发现和重要信息
  3. 提供可操作的建议或下一步行动
  4. 确保摘要易于理解和使用
  
  摘要应该包含：执行摘要、关键发现、建议和结论。
model: "anthropic.claude-3-haiku-latest"
```

#### 工作流定义

```yaml
# workflows/document_workflow.yaml
name: "document_analysis_workflow"
type: "chain"
steps:
  - agent: "document_analyzer"
    input_key: "document_content"
    output_key: "analysis_result"
  
  - agent: "document_summarizer"
    input_key: "analysis_result"
    output_key: "summary"
    
output_format: |
  # 文档分析报告
  
  ## 分析结果
  {analysis_result}
  
  ## 摘要
  {summary}
  
  ---
  生成时间: {timestamp}
```

#### 批处理脚本

```python
# scripts/batch_process.py
import asyncio
import os
from pathlib import Path
from fastagent import Workflow, Agent

async def process_documents(input_dir: str, output_dir: str):
    """批量处理文档"""
    
    # 加载工作流
    workflow = Workflow.from_file("workflows/document_workflow.yaml")
    
    # 创建输出目录
    Path(output_dir).mkdir(exist_ok=True)
    
    # 处理所有文档
    for file_path in Path(input_dir).glob("*.txt"):
        print(f"处理文件: {file_path.name}")
        
        try:
            # 读取文档内容
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 执行工作流
            result = await workflow.run({
                "document_content": content,
                "filename": file_path.name
            })
            
            # 保存结果
            output_file = Path(output_dir) / f"{file_path.stem}_analysis.md"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(result)
            
            print(f"✓ 完成: {output_file.name}")
            
        except Exception as e:
            print(f"✗ 错误处理 {file_path.name}: {e}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 3:
        print("用法: python batch_process.py <输入目录> <输出目录>")
        sys.exit(1)
    
    input_dir = sys.argv[1]
    output_dir = sys.argv[2]
    
    asyncio.run(process_documents(input_dir, output_dir))
```

#### 使用方法

```bash
# 设置环境
export ANTHROPIC_API_KEY="your_key"

# 单个文档分析
fast-agent --workflow document_analysis_workflow --input "请分析这个合同文档" --file contract.pdf

# 批量处理
python scripts/batch_process.py /documents/input /documents/output

# 交互式分析
fast-agent --agent document_analyzer
```

### 示例 2：代码审查助手

#### 项目结构
```
code-reviewer/
├── fastagent.config.yaml
├── agents/
│   ├── security_reviewer.yaml
│   ├── performance_reviewer.yaml
│   └── style_reviewer.yaml
├── workflows/
│   └── code_review_workflow.yaml
└── tools/
    └── git_integration.py
```

#### 代理配置

```yaml
# agents/security_reviewer.yaml
name: "security_reviewer"
instructions: |
  你是一个网络安全专家，专门进行代码安全审查。重点关注：
  
  1. **安全漏洞检测**：
     - SQL 注入、XSS、CSRF 等常见漏洞
     - 输入验证和数据清理
     - 认证和授权问题
  
  2. **敏感信息泄露**：
     - 硬编码的密码、API 密钥
     - 敏感数据的不当处理
     - 日志中的敏感信息
  
  3. **加密和数据保护**：
     - 弱加密算法的使用
     - 不安全的随机数生成
     - 数据传输安全
  
  请提供具体的安全建议和修复方案。
model: "anthropic.claude-3-sonnet-latest"
```

```yaml
# agents/performance_reviewer.yaml
name: "performance_reviewer"
instructions: |
  你是一个性能优化专家，专门分析代码性能问题。关注点包括：
  
  1. **算法复杂度**：
     - 时间复杂度和空间复杂度分析
     - 低效的循环和递归
     - 数据结构选择
  
  2. **资源使用**：
     - 内存泄漏和资源未释放
     - 数据库查询优化
     - 网络请求效率
  
  3. **并发和异步**：
     - 线程安全问题
     - 异步操作的正确使用
     - 锁竞争和死锁
  
  提供具体的性能优化建议。
model: "anthropic.claude-3-sonnet-latest"
```

#### 工作流配置

```yaml
# workflows/code_review_workflow.yaml
name: "comprehensive_code_review"
type: "parallel"
steps:
  - agent: "security_reviewer"
    input_key: "code"
    output_key: "security_review"
    
  - agent: "performance_reviewer"
    input_key: "code"
    output_key: "performance_review"
    
  - agent: "style_reviewer"
    input_key: "code"
    output_key: "style_review"

post_process:
  agent: "report_generator"
  inputs: ["security_review", "performance_review", "style_review"]
  output_key: "final_report"
```

#### Git 集成工具

```python
# tools/git_integration.py
import subprocess
import json
from pathlib import Path
from fastagent import Workflow

class GitCodeReviewer:
    def __init__(self, workflow_path: str):
        self.workflow = Workflow.from_file(workflow_path)
    
    def get_diff(self, commit_hash: str = None) -> str:
        """获取 Git diff"""
        if commit_hash:
            cmd = ["git", "show", commit_hash]
        else:
            cmd = ["git", "diff", "HEAD~1"]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout
    
    def get_changed_files(self, commit_hash: str = None) -> list:
        """获取变更的文件列表"""
        if commit_hash:
            cmd = ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", commit_hash]
        else:
            cmd = ["git", "diff", "--name-only", "HEAD~1"]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout.strip().split('\n') if result.stdout.strip() else []
    
    async def review_commit(self, commit_hash: str = None) -> dict:
        """审查指定提交"""
        diff = self.get_diff(commit_hash)
        changed_files = self.get_changed_files(commit_hash)
        
        # 过滤代码文件
        code_files = [f for f in changed_files if f.endswith(('.py', '.js', '.java', '.cpp', '.c'))]
        
        reviews = {}
        
        for file_path in code_files:
            try:
                # 读取文件内容
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 执行代码审查
                review_result = await self.workflow.run({
                    "code": content,
                    "file_path": file_path,
                    "diff": diff
                })
                
                reviews[file_path] = review_result
                
            except Exception as e:
                reviews[file_path] = {"error": str(e)}
        
        return reviews
    
    def generate_pr_comment(self, reviews: dict) -> str:
        """生成 PR 评论"""
        comment = "## 🤖 自动代码审查报告\n\n"
        
        for file_path, review in reviews.items():
            if "error" in review:
                comment += f"### ❌ {file_path}\n错误: {review['error']}\n\n"
                continue
            
            comment += f"### 📁 {file_path}\n\n"
            
            if "security_review" in review:
                comment += "#### 🔒 安全审查\n"
                comment += review["security_review"] + "\n\n"
            
            if "performance_review" in review:
                comment += "#### ⚡ 性能审查\n"
                comment += review["performance_review"] + "\n\n"
            
            if "style_review" in review:
                comment += "#### 🎨 代码风格\n"
                comment += review["style_review"] + "\n\n"
        
        return comment

# 使用示例
async def main():
    reviewer = GitCodeReviewer("workflows/code_review_workflow.yaml")
    
    # 审查最新提交
    reviews = await reviewer.review_commit()
    
    # 生成报告
    comment = reviewer.generate_pr_comment(reviews)
    print(comment)
    
    # 保存到文件
    with open("code_review_report.md", "w", encoding="utf-8") as f:
        f.write(comment)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

### 示例 3：客户服务聊天机器人

#### 项目结构
```
customer-service-bot/
├── fastagent.config.yaml
├── agents/
│   ├── classifier.yaml
│   ├── support_agent.yaml
│   └── escalation_agent.yaml
├── workflows/
│   └── customer_service_workflow.yaml
├── knowledge/
│   ├── faq.json
│   └── product_info.json
└── app.py
```

#### 智能分类代理

```yaml
# agents/classifier.yaml
name: "intent_classifier"
instructions: |
  你是一个客户意图分类专家。分析客户消息并分类为以下类别之一：
  
  1. **技术支持** (technical_support)：
     - 产品使用问题
     - 技术故障
     - 配置和设置
  
  2. **账单咨询** (billing_inquiry)：
     - 费用问题
     - 付款相关
     - 账单解释
  
  3. **产品信息** (product_info)：
     - 功能咨询
     - 产品比较
     - 规格询问
  
  4. **投诉建议** (complaint_feedback)：
     - 服务投诉
     - 产品反馈
     - 改进建议
  
  5. **其他** (general)：
     - 不属于以上类别的问题
  
  请只返回分类结果，格式：{"category": "分类名称", "confidence": 0.95}
model: "anthropic.claude-3-haiku-latest"
```

#### 客服代理

```yaml
# agents/support_agent.yaml
name: "customer_support_agent"
instructions: |
  你是一个专业的客户服务代表。你的目标是：
  
  1. **友好专业**：始终保持礼貌和专业的语调
  2. **准确高效**：提供准确的信息和解决方案
  3. **主动服务**：预测客户需求，提供额外帮助
  4. **问题解决**：专注于解决客户的实际问题
  
  **服务原则**：
  - 首先表示理解客户的问题
  - 提供清晰的解决步骤
  - 确认客户是否满意解决方案
  - 如果无法解决，及时转接专家
  
  **可用资源**：
  - 产品知识库
  - FAQ 数据库
  - 技术文档
  
  请根据客户问题类型提供相应的帮助。
model: "anthropic.claude-3-sonnet-latest"
mcp_servers: ["knowledge_base"]
```

#### 工作流配置

```yaml
# workflows/customer_service_workflow.yaml
name: "customer_service_flow"
type: "router"
routing_agent: "intent_classifier"
routing_key: "category"

routes:
  technical_support:
    agent: "technical_support_agent"
    escalation_threshold: 2  # 2次未解决后升级
    
  billing_inquiry:
    agent: "billing_agent"
    escalation_threshold: 1
    
  product_info:
    agent: "product_specialist"
    escalation_threshold: 3
    
  complaint_feedback:
    agent: "escalation_agent"
    priority: "high"
    
  general:
    agent: "customer_support_agent"
    escalation_threshold: 2

escalation:
  agent: "human_agent"
  conditions:
    - "customer_satisfaction < 3"
    - "interaction_count > escalation_threshold"
    - "priority == 'high'"
```

#### Web 应用

```python
# app.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import json
import asyncio
from datetime import datetime
from fastagent import Workflow

app = FastAPI(title="Customer Service Bot")

# 加载工作流
workflow = Workflow.from_file("workflows/customer_service_workflow.yaml")

# 存储活跃连接
active_connections = {}

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = {
            "websocket": websocket,
            "session_data": {
                "messages": [],
                "context": {},
                "satisfaction_score": 5
            }
        }
    
    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
    
    async def send_message(self, client_id: str, message: dict):
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]["websocket"]
            await websocket.send_text(json.dumps(message))
    
    def get_session_data(self, client_id: str):
        return self.active_connections.get(client_id, {}).get("session_data", {})
    
    def update_session_data(self, client_id: str, data: dict):
        if client_id in self.active_connections:
            self.active_connections[client_id]["session_data"].update(data)

manager = ConnectionManager()

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    
    # 发送欢迎消息
    welcome_message = {
        "type": "bot_message",
        "content": "您好！我是智能客服助手，很高兴为您服务。请问有什么可以帮助您的吗？",
        "timestamp": datetime.now().isoformat()
    }
    await manager.send_message(client_id, welcome_message)
    
    try:
        while True:
            # 接收客户消息
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # 记录消息
            session_data = manager.get_session_data(client_id)
            session_data["messages"].append({
                "type": "user",
                "content": message_data["content"],
                "timestamp": datetime.now().isoformat()
            })
            
            # 处理消息
            response = await process_customer_message(
                client_id, 
                message_data["content"], 
                session_data
            )
            
            # 发送响应
            bot_message = {
                "type": "bot_message",
                "content": response["content"],
                "timestamp": datetime.now().isoformat(),
                "metadata": response.get("metadata", {})
            }
            
            await manager.send_message(client_id, bot_message)
            
            # 更新会话数据
            session_data["messages"].append({
                "type": "bot",
                "content": response["content"],
                "timestamp": datetime.now().isoformat()
            })
            
    except WebSocketDisconnect:
        manager.disconnect(client_id)
        print(f"Client {client_id} disconnected")

async def process_customer_message(client_id: str, message: str, session_data: dict) -> dict:
    """处理客户消息"""
    try:
        # 构建上下文
        context = {
            "message": message,
            "session_history": session_data.get("messages", [])[-5:],  # 最近5条消息
            "customer_context": session_data.get("context", {}),
            "satisfaction_score": session_data.get("satisfaction_score", 5)
        }
        
        # 执行工作流
        result = await workflow.run(context)
        
        # 检查是否需要升级
        if result.get("escalation_required"):
            return {
                "content": "我将为您转接到人工客服，请稍等...",
                "metadata": {
                    "escalation": True,
                    "reason": result.get("escalation_reason")
                }
            }
        
        return {
            "content": result.get("response", "抱歉，我暂时无法处理您的问题，请稍后再试。"),
            "metadata": {
                "category": result.get("category"),
                "confidence": result.get("confidence")
            }
        }
        
    except Exception as e:
        print(f"Error processing message: {e}")
        return {
            "content": "抱歉，系统出现了一些问题，请稍后再试或联系人工客服。",
            "metadata": {"error": True}
        }

# 静态文件服务
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def get_chat_page():
    return HTMLResponse(open("static/chat.html").read())

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## 最佳实践

### 1. 代理设计原则

#### 单一职责原则
```yaml
# ❌ 不好的设计 - 职责过多
name: "super_agent"
instructions: |
  你需要分析代码、写文档、测试功能、部署应用、监控性能...

# ✅ 好的设计 - 职责明确
name: "code_analyzer"
instructions: |
  你是一个专门的代码分析专家，专注于：
  1. 代码质量评估
  2. 潜在问题识别
  3. 改进建议提供
```

#### 清晰的指令
```yaml
# ❌ 模糊的指令
instructions: "帮助用户解决问题"

# ✅ 具体的指令
instructions: |
  你是一个技术支持专家。当用户报告问题时：
  
  1. **问题诊断**：
     - 收集详细的错误信息
     - 了解用户的操作步骤
     - 确认环境配置
  
  2. **解决方案**：
     - 提供逐步的解决步骤
     - 解释每个步骤的目的
     - 提供替代方案
  
  3. **验证结果**：
     - 确认问题是否解决
     - 提供预防措施
     - 记录解决方案
```

### 2. 工作流设计模式

#### 管道模式（Pipeline）
```yaml
# 适用于：数据处理、内容生成
name: "content_pipeline"
type: "chain"
steps:
  - agent: "content_extractor"    # 提取原始内容
  - agent: "content_processor"    # 处理和清理
  - agent: "content_enhancer"     # 增强和优化
  - agent: "content_formatter"    # 格式化输出
```

#### 分支模式（Branching）
```yaml
# 适用于：条件处理、多路径决策
name: "conditional_workflow"
type: "router"
routing_agent: "decision_maker"
routes:
  urgent:
    workflow: "urgent_handling"
  normal:
    workflow: "standard_processing"
  complex:
    workflow: "expert_review"
```

#### 并行模式（Parallel）
```yaml
# 适用于：独立任务、性能优化
name: "parallel_analysis"
type: "parallel"
steps:
  - agent: "security_checker"     # 安全检查
  - agent: "performance_analyzer" # 性能分析
  - agent: "quality_assessor"     # 质量评估
```

### 3. 错误处理和重试

#### 配置重试策略
```yaml
# fastagent.config.yaml
retry:
  max_attempts: 3
  backoff_strategy: "exponential"  # linear, exponential, fixed
  base_delay: 1  # 秒
  max_delay: 60
  
  # 可重试的错误类型
  retryable_errors:
    - "RateLimitError"
    - "TimeoutError"
    - "ConnectionError"
  
  # 不可重试的错误
  non_retryable_errors:
    - "AuthenticationError"
    - "InvalidInputError"
```

#### 代理级别的错误处理
```yaml
name: "robust_agent"
instructions: |
  你是一个可靠的助手。如果遇到问题：
  1. 尝试理解问题的根本原因
  2. 提供可能的解决方案
  3. 如果无法解决，明确说明限制
  4. 建议用户寻求其他帮助

error_handling:
  on_failure: "graceful_degradation"
  fallback_response: "抱歉，我遇到了一些技术问题。请稍后再试或联系技术支持。"
  log_errors: true
```

### 4. 性能优化策略

#### 模型选择策略
```yaml
# 根据任务复杂度选择模型
model_selection:
  simple_tasks:
    model: "anthropic.claude-3-haiku-latest"  # 快速、便宜
    examples: ["分类", "简单问答", "格式转换"]
  
  complex_tasks:
    model: "anthropic.claude-3-sonnet-latest"  # 平衡性能和成本
    examples: ["分析", "创作", "推理"]
  
  critical_tasks:
    model: "anthropic.claude-3-opus-latest"   # 最高质量
    examples: ["重要决策", "复杂分析", "创意工作"]
```

#### 缓存策略
```python
# 实现智能缓存
from functools import lru_cache
import hashlib

class SmartCache:
    def __init__(self, max_size=1000, ttl=3600):
        self.cache = {}
        self.max_size = max_size
        self.ttl = ttl
    
    def get_cache_key(self, agent_name: str, input_data: str) -> str:
        """生成缓存键"""
        content = f"{agent_name}:{input_data}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def should_cache(self, input_data: str) -> bool:
        """判断是否应该缓存"""
        # 不缓存包含敏感信息的请求
        sensitive_keywords = ['password', 'token', 'key', 'secret']
        return not any(keyword in input_data.lower() for keyword in sensitive_keywords)
    
    async def get_or_compute(self, agent, input_data: str):
        """获取缓存或计算结果"""
        if not self.should_cache(input_data):
            return await agent.send(input_data)
        
        cache_key = self.get_cache_key(agent.name, input_data)
        
        # 检查缓存
        if cache_key in self.cache:
            cached_item = self.cache[cache_key]
            if time.time() - cached_item['timestamp'] < self.ttl:
                return cached_item['result']
        
        # 计算结果
        result = await agent.send(input_data)
        
        # 存储到缓存
        self.cache[cache_key] = {
            'result': result,
            'timestamp': time.time()
        }
        
        # 清理过期缓存
        self._cleanup_cache()
        
        return result
```

### 5. 安全最佳实践

#### 输入验证和清理
```python
import re
from typing import Any, Dict

class InputValidator:
    def __init__(self):
        self.max_length = 10000
        self.forbidden_patterns = [
            r'<script[^>]*>.*?</script>',  # XSS 防护
            r'javascript:',
            r'data:text/html',
            r'eval\s*\(',
        ]
    
    def validate_input(self, text: str) -> Dict[str, Any]:
        """验证和清理输入"""
        result = {
            'is_valid': True,
            'cleaned_text': text,
            'warnings': []
        }
        
        # 长度检查
        if len(text) > self.max_length:
            result['is_valid'] = False
            result['warnings'].append(f'Input too long: {len(text)} > {self.max_length}')
            return result
        
        # 恶意模式检查
        for pattern in self.forbidden_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                result['is_valid'] = False
                result['warnings'].append(f'Forbidden pattern detected: {pattern}')
                return result
        
        # 清理文本
        result['cleaned_text'] = self._clean_text(text)
        
        return result
    
    def _clean_text(self, text: str) -> str:
        """清理文本"""
        # 移除潜在的恶意字符
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        
        # 标准化空白字符
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text

# 在代理中使用
validator = InputValidator()

async def safe_agent_call(agent, user_input: str):
    validation_result = validator.validate_input(user_input)
    
    if not validation_result['is_valid']:
        return {
            'error': 'Invalid input',
            'warnings': validation_result['warnings']
        }
    
    return await agent.send(validation_result['cleaned_text'])
```

#### 敏感信息保护
```python
import re
from typing import List, Tuple

class SensitiveDataProtector:
    def __init__(self):
        self.patterns = {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
            'credit_card': r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
            'api_key': r'\b[A-Za-z0-9]{32,}\b',
        }
    
    def detect_sensitive_data(self, text: str) -> List[Tuple[str, str]]:
        """检测敏感数据"""
        findings = []
        
        for data_type, pattern in self.patterns.items():
            matches = re.findall(pattern, text)
            for match in matches:
                findings.append((data_type, match))
        
        return findings
    
    def mask_sensitive_data(self, text: str) -> str:
        """掩码敏感数据"""
        masked_text = text
        
        for data_type, pattern in self.patterns.items():
            if data_type == 'email':
                masked_text = re.sub(pattern, '[EMAIL_REDACTED]', masked_text)
            elif data_type == 'phone':
                masked_text = re.sub(pattern, '[PHONE_REDACTED]', masked_text)
            elif data_type == 'ssn':
                masked_text = re.sub(pattern, '[SSN_REDACTED]', masked_text)
            elif data_type == 'credit_card':
                masked_text = re.sub(pattern, '[CARD_REDACTED]', masked_text)
            elif data_type == 'api_key':
                masked_text = re.sub(pattern, '[KEY_REDACTED]', masked_text)
        
        return masked_text
```

### 6. 监控和日志

#### 结构化日志
```python
import logging
import json
from datetime import datetime
from typing import Dict, Any

class StructuredLogger:
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # 创建格式化器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # 添加处理器
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    def log_agent_interaction(self, 
                            agent_name: str, 
                            input_text: str, 
                            output_text: str, 
                            metadata: Dict[str, Any] = None):
        """记录代理交互"""
        log_data = {
            'event_type': 'agent_interaction',
            'timestamp': datetime.now().isoformat(),
            'agent_name': agent_name,
            'input_length': len(input_text),
            'output_length': len(output_text),
            'metadata': metadata or {}
        }
        
        self.logger.info(json.dumps(log_data))
    
    def log_error(self, error: Exception, context: Dict[str, Any] = None):
        """记录错误"""
        log_data = {
            'event_type': 'error',
            'timestamp': datetime.now().isoformat(),
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context or {}
        }
        
        self.logger.error(json.dumps(log_data))
    
    def log_performance(self, operation: str, duration: float, metadata: Dict[str, Any] = None):
        """记录性能指标"""
        log_data = {
            'event_type': 'performance',
            'timestamp': datetime.now().isoformat(),
            'operation': operation,
            'duration_seconds': duration,
            'metadata': metadata or {}
        }
        
        self.logger.info(json.dumps(log_data))
```

### 7. 测试策略

#### 单元测试
```python
import pytest
import asyncio
from fastagent import Agent

class TestAgent:
    @pytest.fixture
    def agent(self):
        return Agent(
            instructions="你是一个测试助手",
            model="anthropic.claude-3-haiku-latest"
        )
    
    @pytest.mark.asyncio
    async def test_basic_response(self, agent):
        """测试基本响应"""
        response = await agent.send("Hello")
        assert response is not None
        assert len(response) > 0
    
    @pytest.mark.asyncio
    async def test_error_handling(self, agent):
        """测试错误处理"""
        # 测试空输入
        with pytest.raises(ValueError):
            await agent.send("")
        
        # 测试过长输入
        long_input = "x" * 100000
        with pytest.raises(ValueError):
            await agent.send(long_input)
    
    @pytest.mark.asyncio
    async def test_response_quality(self, agent):
        """测试响应质量"""
        test_cases = [
            {
                'input': '2 + 2 = ?',
                'expected_keywords': ['4', 'four']
            },
            {
                'input': '什么是Python？',
                'expected_keywords': ['编程', '语言', 'Python']
            }
        ]
        
        for case in test_cases:
            response = await agent.send(case['input'])
            assert any(keyword in response.lower() for keyword in case['expected_keywords'])
```

#### 集成测试
```python
import pytest
from fastagent import Workflow

class TestWorkflow:
    @pytest.fixture
    def workflow(self):
        return Workflow.from_file("test_workflow.yaml")
    
    @pytest.mark.asyncio
    async def test_workflow_execution(self, workflow):
        """测试工作流执行"""
        input_data = {
            'text': 'This is a test document.',
            'task': 'analyze'
        }
        
        result = await workflow.run(input_data)
        
        assert 'analysis' in result
        assert 'summary' in result
        assert len(result['summary']) > 0
    
    @pytest.mark.asyncio
    async def test_workflow_error_recovery(self, workflow):
        """测试工作流错误恢复"""
        # 模拟错误输入
        invalid_input = {'invalid': 'data'}
        
        result = await workflow.run(invalid_input)
        
        # 应该有错误处理机制
        assert 'error' in result or 'fallback' in result
```

## 下一步

通过这些实践示例和最佳实践，您应该能够：

1. **设计高效的代理系统**：遵循单一职责原则，编写清晰的指令
2. **构建可靠的工作流**：选择合适的模式，实现错误处理
3. **优化性能**：合理选择模型，实现缓存策略
4. **确保安全**：验证输入，保护敏感数据
5. **监控运行状态**：实现结构化日志，跟踪性能指标
6. **保证质量**：编写全面的测试，持续改进

下一章将介绍故障排除和常见问题的解决方案。