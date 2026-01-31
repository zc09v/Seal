# Corrector 模块设计文档

## 1. 功能描述

Corrector 模块是 Seal 库的核心组件之一，负责在数据验证失败时提供修正策略。该模块定义了修正策略的抽象接口，并实现了基于重试的修正策略（FixPromptStrategy），能够根据验证错误生成修正建议的 Prompt，供用户再次调用 LLM 进行修正。

### 核心功能
1. **修正策略抽象接口**：定义统一的修正策略接口，支持多种修正方式
2. **重试策略实现**：基于验证错误生成修正建议 Prompt
3. **默认值策略实现**：使用默认值填充缺失字段，自动修正数据
4. **错误信息提取**：从 ValidationError 中提取关键信息用于修正
5. **修正建议生成**：生成清晰、具体的修正指导

## 2. 架构设计

### 2.1 模块关系
```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Validator   │ ──►│  Corrector   │ ──►│   LLM/User   │
│             │    │             │    │             │
│ Validation  │    │ Correction  │    │ Re-prompt   │
│   Errors    │    │  Strategy   │    │   Input     │
└─────────────┘    └─────────────┘    └─────────────┘
```

### 2.2 核心组件

#### CorrectionStrategy (抽象基类)
- 定义所有修正策略的通用接口
- 提供修正建议的生成方法
- 支持扩展多种修正策略（重试、启发式修正、默认值等）

#### PromptCorrectionStrategy (提示修正策略基类)
- 继承自 CorrectionStrategy
- 专门为 CORRECTION_PROMPT 类型策略设计
- 包含 max_retries 参数用于控制重试次数
- 自动设置 correction_type = CORRECTION_PROMPT

#### DataCorrectionStrategy (数据修正策略基类)
- 继承自 CorrectionStrategy
- 专门为 CORRECTED_DATA 类型策略设计
- 自动设置 correction_type = CORRECTED_DATA

#### FixPromptStrategy (修正提示策略)
- 继承自 PromptCorrectionStrategy
- 根据 ValidationError 生成修正建议 Prompt
- 支持错误类型分类处理
- 提供详细的修正指导

#### DefaultValueStrategy (默认值策略)
- 继承自 DataCorrectionStrategy
- 专门处理缺失字段错误
- 使用默认值填充缺失的必需字段
- 支持多种默认值来源：用户提供、模型schema、类型默认值
- 产生可直接使用的修正数据

#### TypeConversionStrategy (类型转换策略)
- 继承自 DataCorrectionStrategy
- 专门处理类型转换错误
- 自动将字段值转换为正确的类型
- 支持常见类型转换：字符串到数字、数字到字符串、布尔值转换等
- 产生可直接使用的修正数据

#### CorrectionResult
- 封装修正操作的结果
- 包含修正结果和修正类型信息
- 修正类型由策略在创建结果时确定
- 提供类型安全的枚举值表示结果类型

#### CorrectionType (修正类型枚举)
- 定义修正结果的类型：CORRECTED_DATA 和 CORRECTION_PROMPT
- 提供类型安全的枚举值
- 支持从字符串值创建枚举实例

## 3. 接口设计

### 3.1 CorrectionStrategy 接口（泛型实现）

```python
class CorrectionStrategy(Generic[T], ABC):
    """Abstract base class for correction strategies."""
    
    @property
    @abstractmethod
    def correction_type(self) -> CorrectionType:
        """Get the type of correction result this strategy produces."""
        pass
    
    @abstractmethod
    def correct(self, 
                data: Dict[str, Any], 
                errors: List[ValidationError],
                model: Type[T]) -> CorrectionResult:
        """
        Apply correction strategy to fix validation errors.
        
        Args:
            data: The original data that failed validation
            errors: List of validation errors
            model: The target SealModel for validation
            
        Returns:
            CorrectionResult containing the correction outcome
        """
        pass
    
    @abstractmethod
    def get_strategy_name(self) -> str:
        """Get the name of the correction strategy."""
        pass
```

### 3.2 PromptCorrectionStrategy 接口

```python
class PromptCorrectionStrategy(CorrectionStrategy):
    """Abstract base class for prompt-based correction strategies."""
    
    def __init__(self, max_retries: int = 3):
        """
        Initialize prompt correction strategy.
        
        Args:
            max_retries: Maximum number of retry attempts
        """
        self.max_retries = max_retries
    
    @property
    def correction_type(self) -> CorrectionType:
        """Get the type of correction result."""
        return CorrectionType.CORRECTION_PROMPT
```

### 3.3 DataCorrectionStrategy 接口

```python
class DataCorrectionStrategy(CorrectionStrategy):
    """Abstract base class for data correction strategies."""
    
    @property
    def correction_type(self) -> CorrectionType:
        """Get the type of correction result."""
        return CorrectionType.CORRECTED_DATA
```

### 3.4 FixPromptStrategy 实现

```python
class FixPromptStrategy(PromptCorrectionStrategy):
    """Fix prompt strategy that generates correction prompts for LLM re-prompting."""
    
    def __init__(self, max_retries: int = 3):
        """
        Initialize fix prompt strategy.
        
        Args:
            max_retries: Maximum number of retry attempts
        """
        super().__init__(max_retries)
    
    def correct(self, 
                data: Dict[str, Any], 
                errors: List[ValidationError],
                model: Type[SealModel]) -> CorrectionResult:
        """
        Generate correction prompt based on validation errors.
        
        Args:
            data: The original data that failed validation
            errors: List of validation errors
            model: The target SealModel for validation
            
        Returns:
            CorrectionResult with correction prompt
        """
```

### 3.3 CorrectionResult 类

```python
@dataclass
class CorrectionResult:
    """Result of correction operation using Union types for oneof pattern."""
    
    result: Union[Dict[str, Any], str, None]
    """The result of the correction operation using Union types.
    
    This field uses Union types to represent the oneof pattern:
    - Dict[str, Any]: Corrected data (successful correction)
    - str: Correction prompt (re-prompting needed)
    - None: Empty result
    """
    
    strategy_name: Optional[str] = None
    """Name of the correction strategy that produced this result."""
    
    error_summary: Optional[str] = None
    """Summary of validation errors that triggered the correction."""
    
    @property
    def result_type(self) -> str:
        """Get the type of result based on the Union type."""
        if isinstance(self.result, dict):
            return 'corrected_data'
        elif isinstance(self.result, str):
            return 'correction_prompt'
        else:
            return 'empty'
    
    @property
    def success(self) -> bool:
        """Whether the correction operation was successful."""
        return isinstance(self.result, dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'result_type': self.result_type,
            'success': self.success,
            'result': self.result,
            'strategy_name': self.strategy_name,
            'error_summary': self.error_summary
        }
```

## 4. 实现细节

### 4.1 错误分类处理

#### FixPromptStrategy 错误分类
FixPromptStrategy 将错误分为以下几类进行处理：

1. **类型错误**：字段类型不匹配（如字符串应为数字）
2. **必填字段缺失**：缺少必需字段
3. **约束验证失败**：字段值不符合约束条件（如范围、格式等）
4. **枚举值错误**：字段值不在允许的枚举值范围内
5. **自定义规则错误**：自定义验证规则失败

#### DefaultValueStrategy 错误处理
DefaultValueStrategy 专门处理缺失字段错误，具有以下特点：

1. **错误识别**：通过错误类型和消息识别缺失字段错误
   - 错误类型包含 "missing" 或 "required"
   - 错误消息包含 "missing" 或 "required"

2. **优先级处理**：仅处理缺失字段错误，其他错误类型保持不变
3. **智能修正**：对可修正的缺失字段进行默认值填充，保留其他错误

### 4.4 默认值获取策略

DefaultValueStrategy 采用多级优先级获取默认值：

1. **用户自定义默认值**：通过构造函数传入的 default_values 字典
2. **模型Schema默认值**：从 SealModel 的 schema 中提取的 default 值
3. **类型默认值**：基于字段类型的默认值
   - 数值类型（int, float）：0
   - 字符串类型：空字符串 ""
   - 布尔类型：False
   - 列表/元组类型：空列表 []
   - 字典类型：空字典 {}
   - Optional类型：提取内部类型的默认值

### 4.5 修正结果生成

DefaultValueStrategy 生成详细的修正摘要，包含：
- 成功修正的字段列表
- 无法修正的字段列表（无默认值可用）
- 剩余的错误数量统计
- 按错误类型分类的错误信息

### 4.2 修正提示生成

修正提示将包含以下信息：
- 错误摘要：简要说明验证失败的原因
- 具体错误：列出每个字段的具体错误信息
- 修正指导：提供具体的修正建议
- 示例数据：提供正确的数据示例

### 4.3 示例修正提示

#### FixPromptStrategy 修正提示示例
```
Validation failed for the following reasons:

1. Field 'age': Expected integer, but got string "25"
   - Correction: Convert the value to integer type

2. Field 'email': Invalid format, must be a valid email address
   - Correction: Provide a valid email format (e.g., user@example.com)

3. Field 'price': Value must be greater than 0
   - Correction: Ensure price is a positive number

Please correct the data and try again.
```

#### DefaultValueStrategy 修正结果示例
```python
# 原始数据（缺失字段）
original_data = {
    "name": "John",
    "email": "john@example.com"
    # age 字段缺失
}

# 修正后的数据
corrected_data = {
    "name": "John", 
    "email": "john@example.com",
    "age": 0  # 使用默认值填充
}

# 修正摘要
correction_summary = """
Successfully corrected fields:
- age = 0

No remaining errors.
"""
```

#### TypeConversionStrategy 修正结果示例
```python
# 原始数据（类型错误）
original_data = {
    "name": "John",
    "age": "30",  # 字符串，应为整数
    "price": "19.99",  # 字符串，应为浮点数
    "active": "true"  # 字符串，应为布尔值
}

# 修正后的数据
corrected_data = {
    "name": "John",
    "age": 30,  # 转换为整数
    "price": 19.99,  # 转换为浮点数
    "active": True  # 转换为布尔值
}

# 修正摘要
correction_summary = """
Type conversions applied:
- age: '30' -> 30
- price: '19.99' -> 19.99
- active: 'true' -> True

No remaining errors.
"""
```
seal/
├── codes/
│   ├── corrector/
│   │   ├── __init__.py          # 模块导出
│   │   ├── base.py              # CorrectionStrategy 基类
│   │   ├── fix_prompt_strategy.py    # FixPromptStrategy 实现
│   │   ├── strategies/          # 修正策略实现
│   │   │   ├── __init__.py      # 策略模块导出
│   │   │   └── default_value_strategy.py  # DefaultValueStrategy 实现
│   │   ├── results.py           # CorrectionResult 类
│   │   └── errors.py            # 修正相关错误类型
│   └── ...
└── ...
```

## 6. 测试策略

### 6.1 单元测试覆盖
- CorrectionStrategy 接口测试
- FixPromptStrategy 功能测试
- DefaultValueStrategy 功能测试
- 错误分类处理测试
- 修正提示生成测试
- 默认值获取逻辑测试

### 6.2 集成测试
- 与 Validator 模块的集成测试
- 端到端的修正流程测试
- 多种修正策略组合使用测试

## 7. 扩展性考虑

### 7.1 已实现策略
- **FixPromptStrategy**：基于重试的提示修正策略
- **DefaultValueStrategy**：使用默认值填充缺失字段

### 7.2 已实现策略扩展
- **FixPromptStrategy**：基于重试的提示修正策略
- **DefaultValueStrategy**：使用默认值填充缺失字段
- **TypeConversionStrategy**：自动类型转换策略

### 7.3 配置选项
- 修正策略选择
- 重试次数配置
- 错误处理粒度配置
- 默认值来源优先级配置

## 8. 设计原则

1. **单一职责原则**：每个修正策略只负责一种修正方式
2. **开闭原则**：支持通过继承扩展新的修正策略
3. **依赖倒置原则**：依赖抽象接口而非具体实现
4. **轻量级设计**：避免不必要的复杂性，保持代码简洁

## 9. 总结

Corrector 模块为 Seal 库提供了强大的修正能力，能够根据验证错误生成有针对性的修正建议。通过抽象的策略接口和具体的 RetryStrategy 实现，该模块既满足了当前的重试需求，也为未来的扩展奠定了基础。