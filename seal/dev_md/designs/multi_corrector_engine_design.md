# Engine多Corrector支持设计方案

## 1. 功能描述

增强SealEngine的能力，支持传入一组corrector进行串联执行。当验证失败时，engine将按顺序调用每个corrector来处理错误，提高修正成功率。

### 核心功能
1. **多corrector串联执行**：支持传入corrector列表，按顺序执行修正策略
2. **智能短路逻辑**：当某个corrector成功修正数据时，可提前终止链式执行
3. **重试逻辑优化**：根据corrector类型智能控制重试行为

## 2. 架构设计

### 2.1 模块关系
```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Validator   │ ──►│ Corrector   │ ──►│   LLM/User   │
│             │    │   Chain     │    │             │
│ Validation  │    │             │    │ Re-prompt   │
│   Errors    │    │ Strategy 1  │    │   Input     │
└─────────────┘    │ Strategy 2  │    └─────────────┘
                   │ Strategy 3  │
                   └─────────────┘
```

### 2.2 核心组件变更

#### SealEngine (增强版)
- 新增`corrector_chain`属性存储corrector列表
- 修改`__init__`方法支持corrector列表
- 新增`_execute_corrector_chain`方法实现corrector串联执行

#### CorrectionChain (可选，未来扩展)
- 专门管理corrector执行顺序和逻辑
- 提供corrector优先级和依赖关系管理

## 3. 接口设计

### 3.1 SealEngine.__init__ 方法增强

```python
def __init__(self, 
             model: Type[T],
             llm_adapter: LLMAdapter,
             prompt_builder: PromptBuilder[T],
             parser: JsonParser,
             validator: Validator[T],
             correctors: List[CorrectionStrategy[T]],
             config: Optional[Dict[str, Any]] = None):
    """
    Initialize SealEngine with type-safe components.
    
    Args:
        model: The target SealModel type
        llm_adapter: LLM adapter for API calls
        prompt_builder: PromptBuilder instance
        parser: JSON parser instance
        validator: Validator instance
        correctors: List of correction strategies
        config: Engine configuration (optional)
    
    Raises:
        ValueError: If any required component is invalid
    """
    # ... 现有验证逻辑 ...
    
    # 处理corrector参数
    if not correctors:
        raise ValueError("Correctors list cannot be empty")
    self.correctors = correctors
```

### 3.2 新增 _execute_corrector_chain_with_retry 方法

```python
def _execute_corrector_chain_with_retry(self, 
                                      result: EngineResult,
                                      parsed_data: Dict[str, Any],
                                      current_prompt: str) -> tuple[Any, str, int]:
    """带重试机制的corrector链执行"""
    
    correction_state = CorrectionExecutionState(self.correctors)
    current_data = parsed_data
    current_errors = result.errors
    
    while correction_state.has_more_correctors():
        corrector = correction_state.get_current_corrector()
        corrector_name = corrector.get_strategy_name()
        
        correction_step = self._create_execution_step(
            f'correct_{correction_state.current_corrector_index}',
            {
                "data": current_data,
                "errors": current_errors,
                "corrector": corrector_name,
                "retry_count": correction_state.corrector_states[correction_state.current_corrector_index]['retry_count']
            }
        )
        
        try:
            correction_result = corrector.correct(current_data, current_errors, self.model)
            correction_step.output_data = correction_result
            correction_step.success = True
            
            # 处理修正结果
            if correction_result.correction_type == CorrectionType.CORRECTED_DATA:
                # 验证修正后的数据
                if self._is_corrected_data_valid(correction_result.result):
                    result.add_execution_step(correction_step)
                    return correction_result.result, current_prompt, 0  # 数据修正成功
                else:
                    # 数据修正但验证失败，继续下一个corrector
                    current_data = correction_result.result
                    validation_result = self._validate_data(current_data)
                    current_errors = validation_result.errors if not validation_result.is_valid else []
                    correction_state.move_to_next_corrector()
                    
            elif correction_result.correction_type == CorrectionType.CORRECTION_PROMPT:
                # 提示修正，检查是否可以重试
                if correction_state.can_retry_current_corrector():
                    # 可以重试，更新提示并继续
                    correction_state.increment_retry_count()
                    current_prompt = self._build_prompt_with_instructions(correction_result.result)
                    # 继续使用当前corrector进行重试
                else:
                    # 不能重试，移动到下一个corrector
                    correction_state.move_to_next_corrector()
            
            result.add_execution_step(correction_step)
            
        except Exception as e:
            correction_step.success = False
            correction_step.error = e
            result.add_execution_step(correction_step)
            
            # 错误处理：移动到下一个corrector
            correction_state.move_to_next_corrector()
    
    # 所有corrector都执行完毕但未成功
    raise EngineError("All correctors failed to produce valid data")
```

### 3.3 新增 CorrectionExecutionState 类

```python
class CorrectionExecutionState:
    """修正执行状态，跟踪每个corrector的重试状态"""
    
    def __init__(self, correctors: List[CorrectionStrategy[T]]):
        self.corrector_states = {
            i: {
                'corrector': corrector,
                'retry_count': 0,
                'max_retries': self._get_corrector_max_retries(corrector)
            }
            for i, corrector in enumerate(correctors)
        }
        self.current_corrector_index = 0
    
    def _get_corrector_max_retries(self, corrector: CorrectionStrategy[T]) -> int:
        """获取单个corrector的最大重试次数"""
        if (hasattr(corrector, 'correction_type') and 
            corrector.correction_type == CorrectionType.CORRECTION_PROMPT):
            return getattr(corrector, 'max_retries', 0)
        return 0  # 数据修正corrector不支持重试
    
    def can_retry_current_corrector(self) -> bool:
        """检查当前corrector是否可以重试"""
        if self.current_corrector_index >= len(self.corrector_states):
            return False
        
        state = self.corrector_states[self.current_corrector_index]
        return (state['retry_count'] < state['max_retries'] and 
                state['max_retries'] > 0)  # 只有prompt-based corrector可以重试
    
    def increment_retry_count(self):
        """增加当前corrector的重试计数"""
        if self.current_corrector_index < len(self.corrector_states):
            state = self.corrector_states[self.current_corrector_index]
            state['retry_count'] += 1
    
    def move_to_next_corrector(self):
        """移动到下一个corrector"""
        self.current_corrector_index += 1
        # 重置当前corrector的重试计数（如果需要）
        if self.current_corrector_index < len(self.corrector_states):
            self.corrector_states[self.current_corrector_index]['retry_count'] = 0
    
    def get_current_corrector(self) -> Optional[CorrectionStrategy[T]]:
        """获取当前corrector"""
        if self.current_corrector_index < len(self.corrector_states):
            return self.corrector_states[self.current_corrector_index]['corrector']
        return None
    
    def has_more_correctors(self) -> bool:
        """是否还有更多corrector"""
        return self.current_corrector_index < len(self.corrector_states)
```

## 4. 执行流程

### 4.1 修正链执行流程

```
开始修正链执行
    ↓
遍历corrector_chain中的每个corrector
    ↓
执行当前corrector的correct方法
    ↓
检查修正结果类型
    ↓
如果是CORRECTED_DATA且数据有效 → 返回结果（短路）
    ↓
如果是CORRECTED_DATA但数据无效 → 更新数据并继续下一个corrector
    ↓
如果是CORRECTION_PROMPT → 继续下一个corrector
    ↓
所有corrector执行完毕 → 返回最后一个corrector的结果
```

### 4.2 典型使用场景

#### 场景1：数据修正优先
```python
# 先尝试自动数据修正，再尝试提示修正
corrector_chain = [
    DefaultValueStrategy(),  # 自动填充默认值
    TypeConversionStrategy(), # 自动类型转换
    FixPromptStrategy(max_retries=3)  # 最后尝试提示修正
]

engine = SealEngine(
    model=UserModel,
    llm_adapter=llm_adapter,
    prompt_builder=prompt_builder,
    parser=parser,
    validator=validator,
    corrector=corrector_chain
)
```



## 5. 错误处理设计

### 5.1 修正链错误处理

1. **单个corrector失败**：记录错误信息，继续执行下一个corrector
2. **所有corrector失败**：抛出EngineError，包含所有修正步骤的错误信息
3. **数据验证失败**：修正后的数据仍需重新验证，确保数据有效性

### 5.2 执行步骤记录

每个corrector的执行都会创建独立的执行步骤，便于调试和分析：
- `correct_0`: 第一个corrector的执行结果
- `correct_1`: 第二个corrector的执行结果
- ...

## 6. 性能考虑

### 6.1 短路优化
- 当数据修正成功时立即返回，避免不必要的corrector执行
- 减少LLM调用次数，提高执行效率

### 6.2 执行顺序优化
- 建议将轻量级的数据修正corrector放在前面
- 重量级的提示修正corrector放在后面

## 7. 测试策略

### 7.1 单元测试覆盖
- 单corrector向后兼容性测试
- 多corrector串联执行测试
- 短路逻辑测试
- 错误处理测试

### 7.2 集成测试
- 与现有engine功能的集成测试
- 端到端的多corrector流程测试

## 8. 向后兼容性

### 8.1 API兼容性
- 保持现有单corrector接口完全不变
- 新增corrector列表参数支持

### 8.2 行为兼容性
- 单corrector场景下行为完全一致
- 多corrector场景下提供增强功能

## 9. 总结

多corrector支持方案通过corrector链式执行机制，显著提升了engine的修正能力。该设计保持了向后兼容性，同时提供了灵活的corrector组合方式，能够适应不同的修正需求场景。