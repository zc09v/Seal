# SealEngine 类型安全性重构方案设计

## 问题描述

当前 `SealEngine` 的构造函数中，`PromptBuilder`、`Validator`、`CorrectionStrategy` 都依赖 `SealModel` 类型，但它们是独立注入的，没有类型一致性保证。这可能导致运行时类型不一致的错误。

### 当前问题代码示例
```python
def __init__(self, 
             llm_adapter: LLMAdapter,
             prompt_builder: PromptBuilder,  # 依赖 SealModel
             parser: JsonParser,
             validator: Validator,           # 依赖 SealModel  
             corrector: CorrectionStrategy):  # 依赖 SealModel
```

## 设计目标

1. **类型安全**：在编译时就能发现类型不一致的问题
2. **一致性保证**：确保整个引擎流程中使用相同的 `SealModel` 类型
3. **向后兼容**：尽量不影响现有代码的使用方式
4. **轻量级**：符合项目"仅包含最基础和最必要的能力"的原则

## 方案选择

### 方案1：泛型类型绑定（推荐）

**优点**：
- 类型安全：编译时类型检查
- 灵活性：允许用户自定义组件
- 符合Python类型提示最佳实践

**缺点**：
- 需要修改现有接口，可能影响向后兼容性

### 方案2：工厂模式

**优点**：
- 使用简单，隐藏复杂性
- 保证组件一致性

**缺点**：
- 灵活性较差，用户无法自定义组件
- 运行时才能发现类型问题

### 方案3：配置类封装

**优点**：
- 清晰的配置管理
- 一定程度保证一致性

**缺点**：
- 增加了配置复杂性
- 仍然存在运行时类型问题的可能

## 推荐方案：泛型类型绑定

### 核心设计

```python
from typing import Generic, TypeVar

T = TypeVar('T', bound=SealModel)

class SealEngine(Generic[T]):
    """泛型化的 SealEngine，确保类型一致性。"""
    
    def __init__(self, 
                 model: Type[T],
                 llm_adapter: LLMAdapter,
                 prompt_builder: PromptBuilder[T],  # 泛型化的组件
                 parser: JsonParser,
                 validator: Validator[T],
                 corrector: CorrectionStrategy[T]):
        """
        Initialize SealEngine with type-safe components.
        
        Args:
            model: The target SealModel type that all components should work with
            llm_adapter: LLM adapter for making API calls
            prompt_builder: PromptBuilder instance bound to the model type
            parser: JSON parser instance
            validator: Validator instance bound to the model type
            corrector: Correction strategy bound to the model type
            config: Engine configuration (optional)
        """
        self.model = model
        self.llm_adapter = llm_adapter
        self.prompt_builder = prompt_builder
        self.parser = parser
        self.validator = validator
        self.corrector = corrector
        self.config = config or DEFAULT_CONFIG
```

### 组件接口修改

需要将相关组件改为泛型接口：

```python
# prompt/builder.py
class PromptBuilder(Generic[T]):
    def __init__(self, model: Type[T]):
        self.model = model

# validation/validator.py  
class Validator(Generic[T]):
    def __init__(self, model: Type[T]):
        self.model = model

# corrector/base.py
class CorrectionStrategy(Generic[T], ABC):
    @abstractmethod
    def correct(self, 
                data: Dict[str, Any], 
                errors: List[ValidationError],
                model: Type[T]) -> 'CorrectionResult':
        pass
```

### 使用示例

```python
# 类型安全的使用方式
from seal.codes.schema import UserModel

# 所有组件都绑定到 UserModel 类型
engine = SealEngine[UserModel](
    model=UserModel,
    llm_adapter=llm_adapter,
    prompt_builder=PromptBuilder(UserModel),
    parser=JsonParser(),
    validator=Validator(UserModel),
    corrector=FixPromptStrategy(UserModel)
)

# 类型检查器会捕获不一致的类型
# 以下代码会在类型检查时报错：
engine = SealEngine[UserModel](
    model=UserModel,
    prompt_builder=PromptBuilder(ProductModel),  # 类型不一致！
    # ...
)
```

## 向后兼容性处理

为了保持向后兼容性，可以提供非泛型版本的别名：

```python
# 向后兼容的别名
LegacySealEngine = SealEngine[SealModel]
```

## 文件目录结构变更

无需新增文件，主要修改现有文件：

- `seal/codes/engine/seal_engine.py` - 主要重构
- `seal/codes/prompt/builder.py` - 添加泛型支持
- `seal/codes/validation/validator.py` - 添加泛型支持  
- `seal/codes/corrector/base.py` - 添加泛型支持

## 测试策略

1. **类型检查测试**：使用 mypy 验证类型安全性
2. **运行时测试**：确保重构后功能正常
3. **向后兼容性测试**：验证现有代码仍能工作

## 风险评估

1. **类型检查器兼容性**：需要确保用户的类型检查器支持泛型
2. **学习曲线**：用户需要了解泛型类型的使用
3. **现有代码影响**：可能需要少量修改现有代码

## 实施计划

1. 修改组件接口支持泛型
2. 重构 SealEngine 为泛型类
3. 更新测试用例
4. 验证向后兼容性
5. 更新文档和示例

## 结论

泛型类型绑定方案提供了最佳的编译时类型安全性，同时保持了足够的灵活性。虽然需要修改现有接口，但这是保证类型一致性的最可靠方法，符合项目的质量要求。