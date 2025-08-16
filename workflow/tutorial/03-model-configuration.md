# 第三章：模型配置和 LLM 提供商

## 模型配置概述

fast-agent 支持多种 LLM 提供商，每个提供商都可以通过环境变量或 `fastagent.config.yaml` 文件进行配置。

## 通用配置格式

在 `fastagent.config.yaml` 中：

```yaml
<provider>:
  api_key: "your_api_key" # 可通过 API_KEY 环境变量覆盖
  base_url: "https://api.example.com" # API 调用的基础 URL
```

## 支持的 LLM 提供商

### 1. Anthropic

Anthropic 模型支持文本、视觉和 PDF 内容。

#### YAML 配置：

```yaml
anthropic:
  api_key: "your_anthropic_key" # 必需
  base_url: "https://api.anthropic.com/v1" # 默认值，仅在需要时包含
```

#### 环境变量：

- `ANTHROPIC_API_KEY`: 您的 Anthropic API 密钥
- `ANTHROPIC_BASE_URL`: 覆盖 API 端点

#### 模型别名：

| 模型别名 | 映射到 | 模型别名 | 映射到 |
|---------|--------|---------|--------|
| claude | claude-sonnet-4-0 | haiku | claude-3-5-haiku-latest |
| sonnet | claude-sonnet-4-0 | haiku3 | claude-3-haiku-20240307 |
| sonnet35 | claude-3-5-sonnet-latest | haiku35 | claude-3-5-haiku-latest |
| sonnet37 | claude-3-7-sonnet-latest | opus | claude-opus-4-1 |
| opus3 | claude-3-opus-latest | | |

### 2. OpenAI

fast-agent 支持 OpenAI gpt-5 系列、gpt-4.1 系列、o1-preview、o1 和 o3-mini 模型。

#### YAML 配置：

```yaml
openai:
  api_key: "your_openai_key" # 默认
  base_url: "https://api.openai.com/v1" # 默认值，仅在需要时包含
  reasoning_effort: "medium" # 默认推理努力："low"、"medium" 或 "high"
```

#### 环境变量：

- `OPENAI_API_KEY`: 您的 OpenAI API 密钥
- `OPENAI_BASE_URL`: 覆盖 API 端点

#### 推理模型

对于推理模型，可以指定 low、medium 或 high 努力：

```bash
fast-agent --model o3-mini.medium
fast-agent --model gpt-5.high
```

gpt-5 还支持 minimal 推理努力。

#### 模型别名：

| 模型别名 | 映射到 | 模型别名 | 映射到 |
|---------|--------|---------|--------|
| gpt-4o | gpt-4o | gpt-4.1 | gpt-4.1 |
| gpt-4o-mini | gpt-4o-mini | gpt-4.1-mini | gpt-4.1-mini |
| o1 | o1 | gpt-4.1-nano | gpt-4.1-nano |
| o1-mini | o1-mini | o1-preview | o1-preview |
| o3-mini | o3-mini | o3 | o3 |
| gpt-5 | gpt-5 | gpt-5-mini | gpt-5-mini |
| gpt-5-nano | gpt-5-nano | | |

### 3. Azure OpenAI

⚠️ **检查按区域的模型和功能可用性**

在 Azure 中部署 LLM 模型之前，请务必检查官方 Azure 文档以验证所需的模型和功能在您的区域中是否可用。

#### 配置选项

Azure OpenAI 支持三种身份验证方法：

##### 选项 1：使用 resource_name 和 api_key（标准方法）

```yaml
azure:
  api_key: "your_azure_openai_key" # 除非使用 DefaultAzureCredential，否则必需
  resource_name: "your-resource-name" # 资源名称（如果使用 base_url 则不要包含）
  azure_deployment: "deployment-name" # 必需 - 模型部署名称
  api_version: "2023-05-15" # 可选，显示默认值
  # 如果使用 resource_name，请不要包含 base_url
```

##### 选项 2：使用 base_url 和 api_key（自定义端点）

```yaml
azure:
  api_key: "your_azure_openai_key"
  base_url: "https://your-resource-name.openai.azure.com" # 完整端点 URL
  azure_deployment: "deployment-name"
  api_version: "2023-05-15" # 可选
  # 如果使用 base_url，请不要包含 resource_name
```

##### 选项 3：使用 DefaultAzureCredential（需要 azure-identity 包）

```yaml
azure:
  use_default_azure_credential: true
  base_url: "https://your-endpoint.openai.azure.com/"
  azure_deployment: "deployment-name"
  api_version: "2023-05-15"
  # 在此模式下不要包含 api_key 或 resource_name
```

#### 重要配置说明

- 使用 `resource_name` 或 `base_url`，不能同时使用两者
- 使用 DefaultAzureCredential 时，不要包含 `api_key` 或 `resource_name`
- 模型字符串格式是 `azure.deployment-name`

### 4. DeepSeek

```yaml
deepseek:
  api_key: "your_deepseek_key" # 也可以使用 DEEPSEEK_API_KEY 环境变量
  base_url: "https://api.deepseek.com/v1" # 可选，仅在需要覆盖时包含
```

### 5. Google

```yaml
google:
  api_key: "your_google_key" # 也可以使用 GOOGLE_API_KEY 环境变量
  base_url: "https://generativelanguage.googleapis.com/v1beta/openai" # 可选
```

### 6. Generic (Ollama 等)

```yaml
generic:
  api_key: "ollama" # Ollama 的默认值，根据需要更改
  base_url: "http://localhost:11434/v1" # Ollama 的默认值
```

### 7. OpenRouter

```yaml
openrouter:
  api_key: "your_openrouter_key" # 也可以使用 OPENROUTER_API_KEY 环境变量
  base_url: "https://openrouter.ai/api/v1" # 可选，仅在需要覆盖时包含
```

### 8. TensorZero

```yaml
tensorzero:
  base_url: "http://localhost:3000" # 可选，仅在需要覆盖时包含
```

#### TensorZero 快速入门

```bash
# 创建 TensorZero 示例
fast-agent quickstart tensorzero

# 运行示例
uv run agent.py --model=tensorzero.test_chat
```

### 9. AWS Bedrock

```yaml
bedrock:
  region: "us-east-1" # 必需 - Bedrock 可用的 AWS 区域
  profile: "default" # 可选 - 要使用的 AWS 配置文件（默认为 "default"）
```

#### AWS 身份验证

AWS Bedrock 通过 boto3 凭证提供程序链使用标准 AWS 身份验证：

1. **AWS CLI**: 运行 `aws configure` 设置凭证（推荐本地开发使用 AWS SSO）
2. **环境变量**: `AWS_ACCESS_KEY_ID`、`AWS_SECRET_ACCESS_KEY`、`AWS_SESSION_TOKEN`
3. **IAM 角色**: 在 EC2 或其他 AWS 服务上运行时使用 IAM 角色
4. **AWS 配置文件**: 使用 `profile` 设置或 `AWS_PROFILE` 环境变量的命名配置文件

#### 附加环境变量

- `AWS_REGION` 或 `AWS_DEFAULT_REGION`: 覆盖区域设置
- `AWS_PROFILE`: 覆盖配置文件设置

模型字符串格式是 `bedrock.model-id`（例如，`bedrock.amazon.nova-lite-v1:0`）

## 模型字符串格式

### 基本格式

```
provider.model_name.reasoning_effort
```

- `provider`: LLM 提供商（例如，anthropic、openai、azure、deepseek）
- `model_name`: API 调用中使用的特定模型（对于 Azure，这是您的部署名称）
- `reasoning_effort`（可选）: 控制支持模型的推理努力

### 示例

```
anthropic.claude-3-7-sonnet-latest
openai.gpt-4o
openai.o3-mini.high
azure.my-deployment
generic.llama3.2:latest
openrouter.google/gemini-2.5-pro-exp-03-25:free
tensorzero.my_tensorzero_function
bedrock.amazon.nova-lite-v1:0
```

## 模型优先级

fast-agent 中的模型规范遵循此优先级顺序（从高到低）：

1. 在代理装饰器中明确设置
2. 带有 `--model` 标志的命令行参数
3. `fastagent.config.yaml` 中的默认模型

### 示例

```python
# 1. 在代理中明确设置（最高优先级）
@fast.agent(
    instruction="You are a helpful assistant",
    model="anthropic.claude-3-7-sonnet-latest"
)

# 2. 命令行参数
# uv run agent.py --model gpt-4o

# 3. 配置文件默认值（最低优先级）
# fastagent.config.yaml
default_model: "openai.gpt-4o"
```

## 推理努力

对于支持的模型（o1、o1-preview、o3-mini 和 gpt-5），可以指定推理努力：

- `high`: 最大推理努力
- `medium`: 中等推理努力（默认）
- `low`: 最小推理努力
- `minimal`: 仅适用于 gpt-5

### 使用示例

```bash
# 命令行
fast-agent --model o3-mini.high
fast-agent --model gpt-5.minimal

# 配置文件
default_model: "openai.o3-mini.medium"

# 代理定义
@fast.agent(
    instruction="Complex reasoning task",
    model="openai.gpt-5.high"
)
```

## 结构化输出

OpenAI 模型的结构化输出使用 OpenAI API 结构化输出功能。

## 配置验证

### 检查配置

```bash
# 检查 API 密钥问题
fast-agent check
```

### 测试模型连接

```bash
# 测试特定模型
uv run agent.py --model anthropic.claude --message "Hello"

# 测试默认模型
uv run agent.py --message "Test message"
```

## 环境变量配置

配置也可以通过环境变量提供，命名模式为 `SECTION__SUBSECTION__PROPERTY`（注意双下划线）：

```bash
# 示例
export ANTHROPIC__API_KEY="your_key"
export OPENAI__BASE_URL="https://custom.openai.com/v1"
export DEFAULT_MODEL="anthropic.claude"
```

## 最佳实践

1. **使用密钥文件**: 将敏感信息放在 `fastagent.secrets.yaml` 中
2. **环境变量**: 在生产环境中使用环境变量
3. **模型别名**: 使用别名简化模型引用
4. **推理努力**: 根据任务复杂性选择适当的推理努力
5. **区域检查**: 对于 Azure，验证模型在您的区域中可用

## 下一步

配置好模型后，下一章将介绍 MCP 集成和 Elicitations 功能。