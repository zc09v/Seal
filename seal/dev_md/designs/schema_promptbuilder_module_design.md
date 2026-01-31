# Schema 与 PromptBuilder 模块设计文档

## 1. 功能描述

本模块是 Seal 库的核心基础组件，负责：

1. **Schema 定义**：基于 Pydantic 提供结构化数据契约的定义能力
2. **Prompt 构建**：将 Pydantic Model 转换为 LLM 可理解的 JSON Schema 格式说明

### 核心价值
- 提供标准化的 Schema 定义方式，复用成熟的 Pydantic 生态
- 自动生成精确的格式说明，减少 LLM 输出格式错误
- 为后续的解析、校验、修正流程提供基础支撑

## 2. 接口设计

### 2.1 seal.schema 模块

#### SealModel 基类
```python
class SealModel(BaseModel):
    """增强的基类，提供示例生成等额外功能"""
    
    @classmethod
    def get_example(cls) -> Dict[str, Any]:
        """基于字段定义生成示例数据"""
        
    @classmethod
    def get_json_schema(cls) -> Dict[str, Any]:
        """获取模型的 JSON Schema 表示"""
        
    def to_dict(self) -> Dict[str, Any]:
        """将模型实例转换为字典"""
```

#### 模块导出
```python
# seal/schema/__init__.py
from pydantic import BaseModel, Field, validator

# 提供 SealModel 作为增强的基类
from .base import SealModel

# 导出核心组件
__all__ = ['SealModel', 'BaseModel', 'Field', 'validator']
```

### 2.2 seal.prompt 模块

#### PromptBuilder 类（泛型实现）
```python
class PromptBuilder(Generic[T]):
    """将 SealModel 转换为 LLM 格式说明的构建器"""
    
    def __init__(self, model: Type[T]):
        """
        初始化 PromptBuilder
        
        Args:
            model: SealModel 类（支持泛型类型）
        """
        
    @property
    def format_instructions(self) -> str:
        """
        生成格式说明文本
        
        Returns:
            包含 JSON Schema 描述的格式说明字符串
        """
        
    def to_json_schema(self) -> Dict[str, Any]:
        """
        将 SealModel 转换为 JSON Schema
        
        Returns:
            JSON Schema 字典
        """
```

#### 高层 API 函数
```python
def build_format_instructions(model: Type[SealModel]) -> str:
    """
    快速生成格式说明的便捷函数
    
    Args:
        model: SealModel 类
        
    Returns:
        格式说明字符串
    """
```

## 3. 实现设计

### 3.1 JSON Schema 转换策略

Pydantic Model 到 JSON Schema 的转换将利用 Pydantic 内置的 `model_json_schema()` 方法，确保：

- 类型映射正确（str, int, float, bool, list, dict, enum 等）
- 字段约束保留（min_length, max_length, ge, le, pattern 等）
- 嵌套模型支持
- 可选/必需字段标识

### 3.2 格式说明模板

格式说明将采用以下结构：
```
Please output data strictly according to the following JSON Schema format:

{schema_description}

{example_section}

Important notes:
- Ensure all field types are correct
- Required fields must be provided
- Enum values must be within the specified range
- Numerical constraints must be satisfied
- Output must be valid JSON format
```

其中 `{example_section}` 是可选的，当模型继承自 `SealModel` 且能生成有效示例时包含：
```
Example output format:
{example_output}
```

### 3.3 错误处理

- 对无效的 Pydantic Model 提供清晰的错误信息
- 对复杂的嵌套结构提供友好的提示
- 支持自定义格式说明模板

## 4. 文件目录结构

```
seal/
├── __init__.py
├── codes/                    # 新增：代码目录
│   ├── __init__.py
│   ├── schema/              # Schema 模块
│   │   ├── __init__.py
│   │   └── base.py          # 基础 Schema 定义
│   └── prompt/              # Prompt 模块
│       ├── __init__.py
│       ├── builder.py      # PromptBuilder 实现
│       └── templates.py     # 格式说明模板
├── main.py
└── play_groud.py
```

## 5. 使用示例

### 5.1 定义 Schema（推荐使用 SealModel）
```python
from seal.schema import SealModel, Field
from typing import List, Optional

class UserProfile(SealModel):
    name: str = Field(..., min_length=1, max_length=50, json_schema_extra={'example': '张三'})
    age: int = Field(..., ge=0, le=150, json_schema_extra={'example': 25})
    email: Optional[str] = Field(None, json_schema_extra={'example': 'zhangsan@example.com'})
    tags: List[str] = Field(default_factory=list)

# 生成示例数据
example = UserProfile.get_example()  # {'name': '张三', 'age': 25, ...}
```

### 5.2 传统 BaseModel 使用方式（向后兼容）
```python
from seal.schema import BaseModel, Field
from typing import List, Optional

class UserProfile(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    age: int = Field(..., ge=0, le=150)
    email: Optional[str] = Field(None)
    tags: List[str] = Field(default_factory=list)
```

### 5.2 生成 Prompt
```python
from seal.prompt import PromptBuilder

builder = PromptBuilder(UserProfile)
format_instructions = builder.format_instructions

# 或者使用便捷函数
from seal.prompt import build_format_instructions
instructions = build_format_instructions(UserProfile)
```

### 5.3 预期输出格式
```json
{
    "name": "张三",
    "age": 25,
    "email": "zhangsan@example.com",
    "tags": ["developer", "python"]
}
```

## 6. 测试策略

### 6.1 单元测试覆盖
- Schema 定义的正确性测试
- JSON Schema 转换的准确性测试
- 格式说明生成的完整性测试
- 边界情况和错误处理测试

### 6.2 集成测试
- 与真实 LLM 输出的兼容性测试
- 复杂嵌套结构的处理测试

## 7. 依赖管理

- 核心依赖：`pydantic >= 2.0`
- 开发依赖：`pytest`, `pytest-cov`
- 零额外运行时依赖

## 8. 后续扩展性

### 8.1 多格式支持
- XML Schema 格式说明
- TypeScript Interface 格式说明
- 自定义模板支持

### 8.2 高级特性
- 条件字段提示
- 增强 SealModel 示例生成功能
- 多语言提示支持
- 智能示例生成（基于业务语义推断）
- SealModel 扩展方法（如验证器、序列化器等）

## 9. 风险评估与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| Pydantic API 变更 | 高 | 锁定版本，定期更新测试 |
| JSON Schema 兼容性 | 中 | 充分测试，提供降级方案 |
| 复杂模型性能 | 低 | 优化转换算法，缓存结果 |

---

**设计确认**：请确认此设计方案是否符合项目预期，确认无误后我将开始具体实现。