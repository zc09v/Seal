# LLM Adapter 模块设计文档

## 1. 功能描述

LLM Adapter 模块是 Seal 库中 Active Engine 模式的核心组件，负责：

1. **LLM 后端抽象**：提供统一的接口来对接不同的 LLM 服务提供商
2. **请求/响应标准化**：将不同 LLM 的 API 差异统一为标准的调用格式
3. **错误处理**：处理网络错误、API 限制、认证失败等异常情况
4. **配置管理**：管理 API 密钥、模型参数、超时设置等配置

### 核心价值
- 实现 LLM 后端的可插拔性，支持多种 LLM 服务提供商
- 为 Seal Engine 提供稳定的 LLM 调用接口
- 简化用户配置，提供统一的参数管理

## 2. 接口设计

### 2.1 seal.llm 模块结构

```
seal/llm/
├── __init__.py          # 模块导出
├── base.py              # 抽象基类定义
├── adapters/            # 具体适配器实现
│   ├── __init__.py
│   ├── deepseek.py      # DeepSeek AI 适配器
│   └── openai.py        # OpenAI 适配器（预留）
└── types.py             # 类型定义
```

### 2.2 核心抽象基类

#### LLMAdapter 抽象基类
```python
class LLMAdapter(ABC):
    """LLM 适配器抽象基类"""
    
    @abstractmethod
    async def chat_completion(
        self,
        prompt: str,
        **kwargs
    ) -> LLMResponse:
        """异步聊天补全调用"""
        
    @abstractmethod
    def chat_completion_sync(
        self,
        prompt: str,
        **kwargs
    ) -> LLMResponse:
        """同步聊天补全调用"""
        

```

#### LLMResponse 数据类
```python
@dataclass
class LLMResponse:
    """LLM 响应标准化结构"""
    content: str                    # 模型返回的文本内容
    model: str                     # 使用的模型名称
    usage: Optional[Dict[str, int]] # token 使用情况
    finish_reason: Optional[str]   # 完成原因
    raw_response: Any              # 原始响应对象（用于调试）
```



### 2.3 DeepSeekAIAdapter 实现

#### 配置参数
```python
@dataclass
class DeepSeekConfig:
    """DeepSeek AI 配置"""
    api_key: str                    # API 密钥
    base_url: str = "https://api.deepseek.com"  # API 基础 URL
    model: str = "deepseek-chat"   # 默认模型
```

#### 适配器实现
```python
class DeepSeekAIAdapter(LLMAdapter):
    """DeepSeek AI 适配器实现"""
    
    def __init__(self, config: DeepSeekConfig):
        self.config = config
        self._client = None  # 延迟初始化
        
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> LLMResponse:
        """异步调用 DeepSeek AI API"""
        
    def chat_completion_sync(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> LLMResponse:
        """同步调用 DeepSeek AI API"""
        

```

## 3. 设计原则

### 3.1 抽象与实现分离
- **LLMAdapter** 作为抽象基类，定义统一接口
- 具体适配器实现特定 LLM 服务的 API 调用细节
- 用户可以通过配置轻松切换不同的 LLM 后端

### 3.2 错误处理策略
- 网络错误：自动重试（基于配置的最大重试次数）
- API 限制：等待后重试或抛出明确异常
- 认证失败：立即失败并提供清晰的错误信息

### 3.3 性能考虑
- 支持异步和同步两种调用方式
- 连接池管理，避免频繁创建销毁连接
- 延迟初始化，按需创建客户端

### 3.4 可扩展性
- 预留 OpenAI、Anthropic 等主流 LLM 服务接口
- 支持本地模型部署（如 Ollama、vLLM）
- 易于添加新的 LLM 服务提供商

## 4. 使用示例

### 4.1 基本使用
```python
from seal.llm import DeepSeekAIAdapter, DeepSeekConfig

# 配置 DeepSeek AI
config = DeepSeekConfig(api_key="your-api-key")
adapter = DeepSeekAIAdapter(config)

# 直接调用 LLM
prompt = "Hello, world!"
response = adapter.chat_completion_sync(prompt)
print(response.content)
```

### 4.2 异步使用
```python
import asyncio

async def main():
    config = DeepSeekConfig(api_key="your-api-key")
    adapter = DeepSeekAIAdapter(config)
    
    prompt = "Hello, world!"
    response = await adapter.chat_completion(prompt)
    print(response.content)

# 运行异步函数
asyncio.run(main())
```

## 5. 集成计划

### 5.1 与 Seal Engine 集成
- LLMAdapter 将作为 SealEngine 的依赖组件
- SealEngine 通过 LLMAdapter 调用 LLM，不直接处理具体 API
- 支持运行时切换不同的 LLM 后端

### 5.2 配置管理
- 支持环境变量配置 API 密钥
- 支持配置文件管理多个 LLM 后端配置
- 提供配置验证和错误提示

## 6. 测试策略

### 6.1 单元测试
- 测试抽象基类的接口定义
- 测试 DeepSeekAIAdapter 的具体实现
- 模拟网络错误和 API 限制场景

### 6.2 集成测试
- 实际调用 DeepSeek AI API（需要有效 API 密钥）
- 验证响应解析和错误处理
- 性能基准测试

## 7. 后续扩展

### 7.1 更多适配器支持
- OpenAI GPT 系列
- Anthropic Claude 系列
- 本地模型（Ollama、vLLM）
- 阿里云通义千问、百度文心一言等国内服务

### 7.2 高级功能
- 流式响应支持
- 函数调用（Function Calling）
- 多模态输入支持
- 成本监控和限制