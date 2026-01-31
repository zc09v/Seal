# Seal 架构设计文档

## 1. 概述
Seal 是一个轻量级的 Python 库，旨在解决 LLM 应用开发中结构化输出的保证问题。它不仅仅关注 JSON 格式的合法性，更致力于保障数据的语义正确性、业务规则约束以及类型安全。Seal 既提供全流程托管的 Engine，也提供高度解耦的工具箱（Toolbox），允许用户按需使用 Prompt 生成、解析、校验和修正等原子能力。

## 2. 核心目标
1.  **结构化保障**: 确保 LLM 输出符合预定义的 Schema（基于 Pydantic）。
2.  **语义校验**: 支持复杂的字段约束（如 `age > 0`）和跨字段验证（如 `start_date <= end_date`）。
3.  **自动修正与重试**: 提供运行时修正机制（Re-prompting, Heuristic Fix, Default Fallback）。
4.  **高度解耦与灵活性**: 
    - 不强绑定特定 LLM 或 Adapter，支持用户自带 LLM 响应进行处理。
    - 提供 Prompt 片段生成能力，支持用户自定义 Prompt 组装。
    - 各核心组件（Parser, Validator, Corrector）可独立使用。
5.  **可观测性**: 提供详细的审计日志、违规率和修复成功率指标。
6.  **轻量级**: 核心库零依赖（除 Pydantic 外），易于集成。

## 3. 核心概念 (Core Concepts)

### 3.1 Schema (契约)
定义数据结构和约束。使用 Python 标准的 `Pydantic` 模型作为 Schema 的载体。
- 支持字段类型定义 (str, int, enum, etc.)
- 支持 Field 级别的 Validator
- 支持 Model 级别的 Validator (root_validator)

### 3.2 PromptBuilder (提示构建器)
负责将 Schema 转换为 LLM 可理解的格式说明（Format Instructions）。
- 提供 `.format_instructions` 属性或方法，生成 Prompt 片段。
- 支持不同风格的格式说明（JSON Schema, TypeScript Interface 等）。

### 3.3 Parser (解析器)
负责从 LLM 的非结构化输出（String）中提取结构化数据。
- **Raw Parsing**: 提取 JSON/XML 代码块。
- **Fault Tolerance**: 处理常见的格式错误（如末尾逗号、Markdown 代码块包裹）。

### 3.4 Validator (校验器)
负责验证数据是否符合 Schema。
- **Syntactic Validation**: 格式验证 (Type Check).
- **Semantic Validation**: 业务规则验证 (Constraints, Business Logic).

### 3.5 Corrector (修正器)
当校验失败时，决定如何处理。
- **FixPromptStrategy**: 生成错误反馈 Prompt，供用户再次调用 LLM。
- **RuleCorrector**: 基于预定义规则进行修正（如自动去除多余空格，转换大小写）。
- **DefaultCorrector**: 使用默认值填充。
- **HumanCorrector**: (可选) 接入人工审核/修正流程。

### 3.6 Engine (引擎)
协调整个流程的核心组件，分为两种模式：
- **Active Engine (全托管)**: 托管 Prompt -> LLM -> Parse -> Validate -> Correct 循环。
- **Manual Toolbox (手动/解耦)**: 用户自行调用 LLM，仅使用 Seal 进行 Prompt 生成、解析和校验修正。

### 3.7 Adapter (适配器)
用于对接不同的 LLM 后端（DeepSeek, OpenAI, Anthropic, Local Models）。
- 仅在 Active Engine 模式下需要。
- 提供统一的 `chat` 或 `completion` 接口。

## 4. 架构分层 (Layering)

```mermaid
graph TD

    subgraph Seal Library
        SealAPI --> ActiveEngine[Active Engine]
        SealAPI --> Toolbox[Manual Toolbox]
        
        Toolbox --> PromptBuilder[Prompt Builder]
        Toolbox --> Parser[Parser]
        Toolbox --> Validator[Validator]
        Toolbox --> Corrector[Corrector]
        
        ActiveEngine --> LLMAdapter[LLM Adapter]
        ActiveEngine --> Toolbox
        
        SchemaLayer[Schema Layer (Pydantic)] -.-> Toolbox
    end
    
    LLMAdapter --> ExternalLLM[External LLM]
    UserCode -.-> ExternalLLM
```

- **Toolbox Layer**: 提供原子能力 (`parse`, `validate`, `build_prompt`)，完全解耦 LLM 调用。
- **Engine Layer**: 组装 Toolbox 和 Adapter，提供全托管服务。
- **Integration Layer**: `LLMAdapter`。

## 5. 模块设计

### 5.1 seal.schema
封装 Pydantic。

### 5.2 seal.prompt
- `PromptBuilder`: 根据 Schema 生成 format instructions。

### 5.3 seal.parser
- `JsonParser`: 健壮的 JSON 解析器。

### 5.4 seal.validation
- `Validator`: 执行 Pydantic 校验。

### 5.5 seal.correction
- `CorrectionStrategy`: 修正策略接口。
- `RetryStrategy`: 生成重试 Prompt。

### 5.6 seal.engine
- `SealEngine`: 全托管入口。

## 6. 数据流 (Data Flow)

### 6.1 Active Mode (全托管)
1.  **Input**: Prompt + Schema.
2.  **Engine**: Build Prompt (with instructions) -> Call LLM -> Parse -> Validate -> (Correct/Retry) -> Result.

### 6.2 Manual Mode (手动/解耦)
1.  **Prompting**: 用户调用 `seal.build_instructions(schema)` 获取提示词片段，拼接到自己的 Prompt。
2.  **LLM Call**: 用户自行调用 LLM (DeepSeek, OpenAI, HTTP, etc.)，获取 `raw_response`。
3.  **Parsing & Validation**: 用户调用 `seal.parse_and_validate(raw_response, schema)`。
    - 成功：返回 Object。
    - 失败：返回 `Result` 对象，包含 `errors` 和 `retry_prompt`（如果配置了 Retry 策略）。
4.  **Retry (Optional)**: 用户如果决定重试，可以将 `retry_prompt` 发回给 LLM。

## 7. 开发计划 (Development Plan)
详见 [Development Plan](../development_plan.md)

