# Seal 开发计划 (Development Plan)

## Phase 1: 核心工具箱 (Manual Mode Toolbox)
目标：实现 Manual Mode 流程，使用户可以独立使用各组件。

- [x] **Task 1.1: 基础 Schema 与 PromptBuilder** ✅
    - 定义 `seal.schema` (基于 Pydantic，创建了增强的 `SealModel` 基类)
    - 实现 `PromptBuilder`，将 `SealModel` 转换为 JSON Schema 描述的 Prompt 文本
    - 完整的单元测试覆盖（13个测试用例全部通过）
    - 创建了演示示例文件

- [x] **Task 1.2: Parser 实现** ✅
    - 实现 `JsonParser`。
    - 支持从 Markdown (` ```json ... ``` `) 中提取内容。
    - 支持部分容错（如 `dirty-json` 库的一些能力，或正则修复）。

- [x] **Task 1.3: Validator 实现** ✅
    - 实现 `Validator`，输入 JSON Dict，验证是否符合 Pydantic Model。
    - 返回结构化的错误报告 (`ValidationError` 列表)。

- [x] **Task 1.4: Corrector 接口与 Retry 策略** ✅
    - 定义 `CorrectionStrategy` 接口。
    - 实现 `RetryStrategy`: 根据 `ValidationError` 生成 "修正建议 Prompt"。

## Phase 2: 全托管引擎 (Active Engine)
目标：基于 Toolbox 实现全自动的 Engine。

- [x] **Task 2.1: LLM Adapter 抽象** ✅
    - 定义 `LLMAdapter` 抽象基类。
    - 实现 `DeepSeekAIAdapter` (调用 `deepseek` 库)。

- [x] **Task 2.2: SealEngine 实现** ✅
    - 编排 Prompt -> Call -> Parse -> Validate -> Retry 循环。
    - 实现最大重试次数控制。

- [x] **Task 2.3: 完整流程测试** ✅
    - 使用 `DeepSeekAIAdapter` 测试 Engine 的完整流程是否正确。

## Phase 3: 高级特性与优化 (Future)
P0: 
- [x] engine多corrector的支持
- [x] 测试覆盖率目标100%，测试用例完善
- [ ] 更多的后端引擎支持
P1:
- [x] 更多corrector的支持
- [ ] 英文文档
- [ ] api文档
- [ ] 支持切片
- [ ] 日志
- [ ] parser支持 XML格式
- [ ] engine多parse支持
P2:
- [ ] parser更强的支持，比如json one of的支持