# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-01-31

### Added
- Initial release of Seal library
- **Schema Module**: Pydantic-based `SealModel` with extended features
  - Support for field constraints (min/max length, ranges, patterns)
  - Example data generation from schema definitions
  - JSON Schema export capability
- **Validation Module**: Comprehensive validation system
  - `Validator` class for schema validation
  - `ValidationResult` with detailed error reporting
  - Support for custom validation rules
- **Prompt Module**: LLM format instruction generation
  - `PromptBuilder` for creating LLM-friendly format instructions
  - `build_format_instructions()` helper function
- **Parser Module**: JSON parsing with error handling
  - `JsonParser` with robust error recovery
  - Support for markdown code block extraction
- **Corrector Module**: Multiple correction strategies
  - `FixPromptStrategy`: Generate correction prompts for LLM re-prompting
  - `TypeConversionStrategy`: Automatic type coercion
  - `DefaultValueStrategy`: Fill missing values with defaults
  - Extensible base classes for custom strategies
- **LLM Adapter Module**: DeepSeek AI integration
  - `DeepSeekAIAdapter` for DeepSeek AI API
  - `DeepSeekConfig` for configuration management
  - Comprehensive error handling (connection, auth, rate limit, timeout)
- **Engine Module**: Orchestration layer
  - `SealEngine` for end-to-end validation pipeline
  - Support for sync and async operations
  - Configurable retry logic with multiple correctors
  - `EngineResult` with execution logging
- **Type Safety**: Full type hints and generic support throughout
- **Test Suite**: Comprehensive test coverage (88%)
  - Unit tests for all modules
  - Integration tests for end-to-end workflows

### Technical Details
- Python 3.8+ support
- Pydantic v2 compatibility
- Minimal dependencies (only pydantic>=2.0 required)
- Optional dependencies for LLM providers
