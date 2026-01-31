# Validator 模块设计文档

## 1. 功能描述

Validator 模块是 Seal 库的核心校验组件，负责验证从 LLM 输出中解析出的结构化数据是否符合预定义的 Schema 契约。

### 核心功能
1. **语法校验 (Syntactic Validation)**: 验证数据类型、格式等基础约束
2. **语义校验 (Semantic Validation)**: 验证业务规则、字段约束等高级约束
3. **错误报告**: 提供结构化的错误信息，便于后续修正处理
4. **批量校验**: 支持单条数据和批量数据的校验

### 核心价值
- 确保 LLM 输出数据符合业务契约要求
- 提供详细的错误信息，支持智能修正策略
- 为后续的 Corrector 模块提供准确的输入

## 2. 接口设计

### 2.1 seal.validation 模块

#### Validator 类（泛型实现）
```python
class Validator(Generic[T]):
    """
    数据校验器，基于 Pydantic 模型进行数据验证
    
    支持 Pydantic 内置验证和自定义验证规则的组合
    """
    
    def __init__(self, model: Type[T]):
        """
        初始化校验器
        
        Args:
            model: Pydantic 模型类（支持泛型类型），定义数据结构和约束
        """
        
    def validate(self, data: Dict[str, Any]) -> ValidationResult:
        """
        验证单个数据对象
        
        Args:
            data: 待验证的数据字典
            
        Returns:
            ValidationResult: 验证结果，包含验证状态和错误信息
        """
        
    def is_valid(self, data: Dict[str, Any]) -> bool:
        """
        快速检查数据是否有效
        
        Args:
            data: 待验证的数据字典
            
        Returns:
            bool: 数据是否有效
        """
        
    def register_rule(self, field_name: str, rule: ValidationRule) -> None:
        """
        注册自定义验证规则
        
        Args:
            field_name: 字段名
            rule: 验证规则实例
        """
        
    def remove_rule(self, field_name: str) -> bool:
        """
        移除字段的验证规则
        
        Args:
            field_name: 字段名
            
        Returns:
            bool: 是否成功移除
        """
```

#### ValidationResult 类
```python
class ValidationResult:
    """
    验证结果封装类
    """
    
    def __init__(self, is_valid: bool, errors: List[ValidationError] = None):
        """
        初始化验证结果
        
        Args:
            is_valid: 验证是否通过
            errors: 验证错误列表
        """
        
    @property
    def is_valid(self) -> bool:
        """验证是否通过"""
        
    @property
    def errors(self) -> List[ValidationError]:
        """验证错误列表"""
        
    def get_error_messages(self) -> List[str]:
        """获取格式化的错误消息列表"""
        
    def get_error_summary(self) -> str:
        """获取错误摘要"""
```

#### ValidationRule 类
```python
class ValidationRule:
    """
    自定义验证规则封装
    
    支持扩展 Pydantic 内置验证能力
    """
    
    def __init__(self, name: str, validator_func: Callable[[Any, Dict[str, Any]], Union[bool, str]], description: str = ""):
        """
        初始化验证规则
        
        Args:
            name: 规则名称，用于错误标识
            validator_func: 验证函数，接受字段值和上下文，返回验证结果
            description: 规则描述
        """
        
    def validate(self, value: Any, context: Dict[str, Any]) -> Optional[str]:
        """
        执行验证规则
        
        Args:
            value: 字段值
            context: 验证上下文
            
        Returns:
            Optional[str]: 错误消息，None 表示验证通过
        """
```

#### ValidationError 类
```python
class ValidationError:
    """
    验证错误信息封装
    """
    
    def __init__(self, field: str, error_type: str, message: str, value: Any = None):
        """
        初始化验证错误
        
        Args:
            field: 错误字段名
            error_type: 错误类型
            message: 错误消息
            value: 导致错误的字段值
        """
        
    @property
    def field(self) -> str:
        """错误字段名"""
        
    @property
    def error_type(self) -> str:
        """错误类型"""
        
    @property
    def message(self) -> str:
        """错误消息"""
        
    @property
    def value(self) -> Any:
        """导致错误的字段值"""
        
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
```

### 2.2 模块导出
```python
# seal/validation/__init__.py
from .validator import Validator, ValidationResult, ValidationError, ValidationRule

__all__ = ['Validator', 'ValidationResult', 'ValidationError', 'ValidationRule']
```

## 3. 文件目录结构

```
seal/
├── codes/
│   ├── validation/
│   │   ├── __init__.py          # 模块导出
│   │   ├── validator.py         # Validator 核心实现
│   │   └── errors.py            # 错误类型定义
│   └── ...
└── tests/
    └── codes/
        └── validation/
            ├── __init__.py
            ├── test_validator.py
            └── test_errors.py
```

## 4. 核心实现细节

### 4.1 验证架构
Validator 采用双层验证架构：
1. **Pydantic 内置验证**: 处理类型、格式、约束等基础验证
2. **自定义规则验证**: 扩展业务规则和复杂逻辑验证

### 4.2 错误类型分类
- **Pydantic 原生错误**: 直接使用 Pydantic 的错误类型（如 `int_parsing`, `greater_than_equal`）
- **自定义规则错误**: 格式为 `CustomRule.{rule_name}`，便于识别自定义规则失败

### 4.3 验证流程
1. **Pydantic 验证**: 执行 Pydantic 模型的基础验证
2. **自定义规则验证**: 执行注册的自定义验证规则
3. **错误合并**: 合并 Pydantic 错误和自定义规则错误
4. **结果封装**: 生成结构化的验证结果

### 4.4 自定义规则设计
- **字段级规则**: 每个字段支持一个自定义验证规则
- **上下文传递**: 验证函数接收字段值和完整数据上下文
- **灵活返回值**: 支持布尔值和自定义错误消息返回

### 4.3 错误信息提取
- 从 Pydantic ValidationError 中提取详细的错误信息
- 标准化错误消息格式，便于后续处理
- 提供错误定位和修复建议

## 5. 使用示例

### 5.1 基础使用
```python
from seal.validation import Validator
from seal.schema import SealModel, Field
from typing import List

class UserProfile(SealModel):
    name: str = Field(..., min_length=1, max_length=50)
    age: int = Field(..., ge=0, le=150)
    email: str = Field(..., pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    tags: List[str] = Field(default_factory=list)

# 创建校验器
validator = Validator(UserProfile)

# 测试数据
test_data = {
    "name": "John Doe",
    "age": 25,
    "email": "john@example.com"
}

# 执行验证
result = validator.validate(test_data)

if result.is_valid:
    print("数据验证通过")
else:
    print("验证错误:")
    for error in result.errors:
        print(f"- {error.field}: {error.error_type} - {error.message}")
```

### 5.2 自定义验证规则使用
```python
from seal.validation import Validator, ValidationRule

# 创建自定义验证规则
def validate_name_no_numbers(value: str, context: dict) -> bool:
    """验证姓名不能包含数字"""
    return not any(char.isdigit() for char in value)

def validate_age_even(value: int, context: dict) -> str:
    """验证年龄必须是偶数，返回自定义错误消息"""
    if value % 2 == 0:
        return True
    return "年龄必须是偶数"

# 创建验证规则实例
name_rule = ValidationRule("no_numbers", validate_name_no_numbers, "姓名不能包含数字")
age_rule = ValidationRule("even_age", validate_age_even, "年龄必须是偶数")

# 注册自定义规则
validator.register_rule("name", name_rule)
validator.register_rule("age", age_rule)

# 测试自定义规则
custom_test_data = {
    "name": "John123",  # 包含数字，违反自定义规则
    "age": 31,          # 奇数，违反自定义规则
    "email": "john@example.com"
}

result = validator.validate(custom_test_data)
if not result.is_valid:
    for error in result.errors:
        print(f"- {error.field}: {error.error_type} - {error.message}")
        # 输出示例:
        # - name: CustomRule.no_numbers - Validation rule 'no_numbers' failed
        # - age: CustomRule.even_age - 年龄必须是偶数
```

## 6. 设计原则

### 6.1 单一职责原则
- Validator 只负责数据验证，不涉及数据解析或修正
- 错误信息封装独立，便于复用和扩展

### 6.2 开放封闭原则
- 支持自定义错误处理逻辑
- 便于扩展新的验证规则

### 6.3 依赖倒置原则
- 依赖抽象的 BaseModel 接口，不依赖具体实现
- 便于测试和替换

## 7. 测试策略

### 7.1 单元测试
- 验证各种错误场景
- 测试边界条件
- 验证错误信息准确性

### 7.2 集成测试
- 与 Parser 模块集成测试
- 验证完整的数据处理流程

## 8. 实现状态

### ✅ 已实现功能
- Pydantic 内置验证的完整支持
- 自定义验证规则的注册和管理
- 详细的错误信息报告
- 字段级自定义验证规则
- 验证规则的动态管理（注册/移除）

### 🔄 后续扩展可能性
- 支持验证规则的组合和优先级
- 提供验证性能监控和统计
- 支持异步验证操作
- 增强的上下文信息传递
- 验证规则的序列化和持久化