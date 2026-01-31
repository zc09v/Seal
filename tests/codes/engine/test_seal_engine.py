"""Unit tests for SealEngine."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List

from seal.codes.engine import SealEngine, EngineResult
from seal.codes.engine.errors import EngineError, MaxRetriesExceededError, LLMCallError
from seal.codes.schema import SealModel
from seal.codes.llm.base import LLMAdapter
from seal.codes.parser import JsonParser
from seal.codes.prompt import PromptBuilder
from seal.codes.validation import Validator
from seal.codes.corrector import CorrectionStrategy
from seal.codes.corrector.types import CorrectionType


class TestSealEngine:
    """Test cases for SealEngine class."""
    
    @pytest.fixture
    def simple_model(self):
        """Fixture for a simple SealModel."""
        
        class SimpleModel(SealModel):
            name: str
            age: int
            
        return SimpleModel
    
    @pytest.fixture
    def mock_components(self, simple_model):
        """Fixture for mocked components."""
        
        # Mock LLM adapter
        mock_llm_adapter = Mock(spec=LLMAdapter)
        mock_llm_adapter.chat_completion_sync.return_value.content = '{"name": "John", "age": 30}'
        mock_llm_adapter.chat_completion = AsyncMock(return_value=Mock(content='{"name": "John", "age": 30}'))
        
        # Mock parser
        mock_parser = Mock(spec=JsonParser)
        mock_parser.parse.return_value = {"name": "John", "age": 30}
        
        # Mock validator
        mock_validator = Mock(spec=Validator)
        mock_validation_result = Mock()
        mock_validation_result.is_valid = True
        mock_validation_result.errors = []
        mock_validator.validate.return_value = mock_validation_result
        
        # Mock corrector
        mock_corrector = Mock(spec=CorrectionStrategy)
        mock_corrector.max_retries = 3
        mock_corrector.correction_type = CorrectionType.CORRECTION_PROMPT
        mock_corrector.get_strategy_name.return_value = "MockCorrector"
        
        # Mock prompt builder
        mock_prompt_builder = Mock(spec=PromptBuilder)
        mock_prompt_builder.model = simple_model
        
        return {
            'llm_adapter': mock_llm_adapter,
            'prompt_builder': mock_prompt_builder,
            'parser': mock_parser,
            'validator': mock_validator,
            'correctors': [mock_corrector]
        }
    
    def test_seal_engine_initialization(self, simple_model, mock_components):
        """Test that SealEngine can be initialized with all required components."""
        
        engine = SealEngine[simple_model](
            model=simple_model,
            llm_adapter=mock_components['llm_adapter'],
            prompt_builder=mock_components['prompt_builder'],
            parser=mock_components['parser'],
            validator=mock_components['validator'],
            correctors=mock_components['correctors']
        )
        
        assert engine.model == simple_model
        assert engine.llm_adapter == mock_components['llm_adapter']
        assert engine.prompt_builder == mock_components['prompt_builder']
        assert engine.parser == mock_components['parser']
        assert engine.validator == mock_components['validator']
        assert engine.correctors == mock_components['correctors']
    
    def test_seal_engine_initialization_missing_components(self, simple_model, mock_components):
        """Test that SealEngine raises ValueError when components are missing."""
        
        # Test missing model
        with pytest.raises(ValueError, match="Model is required"):
            SealEngine[simple_model](
                model=None,
                llm_adapter=mock_components['llm_adapter'],
                prompt_builder=mock_components['prompt_builder'],
                parser=mock_components['parser'],
                validator=mock_components['validator'],
                correctors=mock_components['correctors']
            )
        
        # Test missing LLM adapter
        with pytest.raises(ValueError, match="LLM adapter is required"):
            SealEngine[simple_model](
                model=simple_model,
                llm_adapter=None,
                prompt_builder=mock_components['prompt_builder'],
                parser=mock_components['parser'],
                validator=mock_components['validator'],
                correctors=mock_components['correctors']
            )
        
        # Test missing prompt_builder
        with pytest.raises(ValueError, match="PromptBuilder is required"):
            SealEngine[simple_model](
                model=simple_model,
                llm_adapter=mock_components['llm_adapter'],
                prompt_builder=None,
                parser=mock_components['parser'],
                validator=mock_components['validator'],
                correctors=mock_components['correctors']
            )
        
        # Test missing parser
        with pytest.raises(ValueError, match="Parser is required"):
            SealEngine[simple_model](
                model=simple_model,
                llm_adapter=mock_components['llm_adapter'],
                prompt_builder=mock_components['prompt_builder'],
                parser=None,
                validator=mock_components['validator'],
                correctors=mock_components['correctors']
            )
    
    def test_run_sync_success(self, simple_model, mock_components):
        """Test successful synchronous execution."""
        
        engine = SealEngine[simple_model](
            model=simple_model,
            llm_adapter=mock_components['llm_adapter'],
            prompt_builder=mock_components['prompt_builder'],
            parser=mock_components['parser'],
            validator=mock_components['validator'],
            correctors=mock_components['correctors']
        )
        
        result = engine.run_sync("Test prompt")
        
        assert result.success is True
        assert result.data is not None
        assert result.data.name == "John"
        assert result.data.age == 30
        assert result.retry_count == 0
        assert len(result.errors) == 0
        
        # Verify component interactions
        mock_components['llm_adapter'].chat_completion_sync.assert_called_once()
        mock_components['parser'].parse.assert_called_once()
        mock_components['validator'].validate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_run_async_success(self, simple_model, mock_components):
        """Test successful asynchronous execution."""
        
        engine = SealEngine[simple_model](
            model=simple_model,
            llm_adapter=mock_components['llm_adapter'],
            prompt_builder=mock_components['prompt_builder'],
            parser=mock_components['parser'],
            validator=mock_components['validator'],
            correctors=mock_components['correctors']
        )
        
        result = await engine.run_async("Test prompt")
        
        assert result.success is True
        assert result.data is not None
        assert result.data.name == "John"
        assert result.data.age == 30
        assert result.retry_count == 0
        assert len(result.errors) == 0
        
        # Verify component interactions
        mock_components['llm_adapter'].chat_completion.assert_called_once()
        mock_components['parser'].parse.assert_called_once()
        mock_components['validator'].validate.assert_called_once()
    
    def test_correction_execution_state_initialization(self, simple_model, mock_components):
        """Test CorrectionExecutionState initialization and methods."""
        
        engine = SealEngine[simple_model](
            model=simple_model,
            llm_adapter=mock_components['llm_adapter'],
            prompt_builder=mock_components['prompt_builder'],
            parser=mock_components['parser'],
            validator=mock_components['validator'],
            correctors=mock_components['correctors']
        )
        
        # Test internal CorrectionExecutionState class
        state = engine.CorrectionExecutionState(mock_components['correctors'])
        
        assert state.current_corrector_index == 0
        assert len(state.corrector_states) == 1
        assert state.has_more_correctors() is True
        assert state.get_current_corrector() == mock_components['correctors'][0]
    
    def test_correction_execution_state_retry_logic(self, simple_model, mock_components):
        """Test CorrectionExecutionState retry logic."""
        
        engine = SealEngine[simple_model](
            model=simple_model,
            llm_adapter=mock_components['llm_adapter'],
            prompt_builder=mock_components['prompt_builder'],
            parser=mock_components['parser'],
            validator=mock_components['validator'],
            correctors=mock_components['correctors']
        )
        
        state = engine.CorrectionExecutionState(mock_components['correctors'])
        
        # Test initial state
        assert state.can_retry_current_corrector() is True
        
        # Test incrementing retry count
        state.increment_retry_count()
        assert state.corrector_states[0]['retry_count'] == 1
        
        # Test moving to next corrector
        state.move_to_next_corrector()
        assert state.current_corrector_index == 1
        assert state.has_more_correctors() is False
        assert state.get_current_corrector() is None
        assert state.can_retry_current_corrector() is False
    
    def test_llm_call_error_handling(self, simple_model, mock_components):
        """Test LLM call error handling."""
        
        # Mock LLM adapter to raise exception
        mock_components['llm_adapter'].chat_completion_sync.side_effect = Exception("LLM call failed")
        
        engine = SealEngine[simple_model](
            model=simple_model,
            llm_adapter=mock_components['llm_adapter'],
            prompt_builder=mock_components['prompt_builder'],
            parser=mock_components['parser'],
            validator=mock_components['validator'],
            correctors=mock_components['correctors']
        )
        
        with pytest.raises(EngineError):
            engine.run_sync("Test prompt")
    
    def test_parse_error_handling(self, simple_model, mock_components):
        """Test JSON parse error handling."""
        
        # Mock parser to raise exception
        mock_components['parser'].parse.side_effect = Exception("Parse failed")
        
        engine = SealEngine[simple_model](
            model=simple_model,
            llm_adapter=mock_components['llm_adapter'],
            prompt_builder=mock_components['prompt_builder'],
            parser=mock_components['parser'],
            validator=mock_components['validator'],
            correctors=mock_components['correctors']
        )
        
        with pytest.raises(EngineError):
            engine.run_sync("Test prompt")
    
    def test_validation_error_with_all_correctors_failing(self, simple_model, mock_components):
        """Test validation error when all correctors fail."""
        
        # Mock validator to always fail
        mock_validator = Mock(spec=Validator)
        mock_fail_result = Mock()
        mock_fail_result.is_valid = False
        mock_fail_result.errors = ["Validation error"]
        mock_validator.validate.return_value = mock_fail_result
        
        # Mock corrector to fail
        mock_corrector = Mock(spec=CorrectionStrategy)
        mock_corrector.max_retries = 0
        mock_corrector.correction_type = CorrectionType.CORRECTED_DATA
        mock_corrector.get_strategy_name.return_value = "FailingCorrector"
        
        # Create mock correction result indicating failure
        correction_result = Mock()
        correction_result.correction_type = CorrectionType.CORRECTED_DATA
        correction_result.result = {"name": "John", "age": "invalid"}  # Still invalid
        
        mock_corrector.correct.return_value = correction_result
        
        engine = SealEngine[simple_model](
            model=simple_model,
            llm_adapter=mock_components['llm_adapter'],
            prompt_builder=mock_components['prompt_builder'],
            parser=mock_components['parser'],
            validator=mock_validator,
            correctors=[mock_corrector]
        )
        
        with pytest.raises(EngineError, match="All correctors failed to produce valid data"):
            engine.run_sync("Test prompt")
    
    def test_run_sync_validation_failure_with_corrector(self, simple_model, mock_components):
        """Test synchronous execution with validation failure and corrector handling."""
        
        # Mock validator to fail first time, succeed after corrector
        mock_validator = Mock(spec=Validator)
        mock_fail_result = Mock()
        mock_fail_result.is_valid = False
        mock_fail_result.errors = ["Validation error"]
        
        mock_success_result = Mock()
        mock_success_result.is_valid = True
        mock_success_result.errors = []
        
        mock_validator.validate.side_effect = [
            mock_fail_result,  # First validation fails
            mock_success_result  # Second validation succeeds after correction
        ]
        
        # Mock corrector to provide corrected data
        mock_corrector = Mock(spec=CorrectionStrategy)
        mock_corrector.max_retries = 3
        mock_corrector.correction_type = CorrectionType.CORRECTED_DATA
        mock_corrector.get_strategy_name.return_value = "TestCorrector"
        
        # Create mock correction result with proper attributes
        correction_result = Mock()
        correction_result.correction_type = CorrectionType.CORRECTED_DATA
        correction_result.result = {"name": "John", "age": 30}
        
        mock_corrector.correct.return_value = correction_result
        
        engine = SealEngine[simple_model](
            model=simple_model,
            llm_adapter=mock_components['llm_adapter'],
            prompt_builder=mock_components['prompt_builder'],
            parser=mock_components['parser'],
            validator=mock_validator,
            correctors=[mock_corrector]
        )
        
        result = engine.run_sync("Test prompt")
        
        assert result.success is True
        assert result.retry_count == 0  # 重试计数由corrector维度管理
        
        # Verify component interactions
        assert mock_components['llm_adapter'].chat_completion_sync.call_count == 1
        assert mock_validator.validate.call_count == 2  # 初始验证 + 修正后验证
        mock_corrector.correct.assert_called_once()
    
    def test_run_sync_all_correctors_failed(self, simple_model, mock_components):
        """Test synchronous execution when all correctors fail to produce valid data."""
        
        # Mock validator to always fail
        mock_validator = Mock(spec=Validator)
        mock_validation_result = Mock()
        mock_validation_result.is_valid = False
        mock_validation_result.errors = ["Validation error"]
        mock_validator.validate.return_value = mock_validation_result
        
        # Mock corrector to provide invalid corrected data
        mock_corrector = Mock(spec=CorrectionStrategy)
        mock_corrector.max_retries = 1
        mock_corrector.correction_type = CorrectionType.CORRECTED_DATA
        mock_corrector.get_strategy_name.return_value = "TestCorrector"
        
        # Create mock correction result with invalid data
        correction_result = Mock()
        correction_result.correction_type = CorrectionType.CORRECTED_DATA
        correction_result.result = {"name": "John", "age": "invalid"}  # Invalid data
        
        mock_corrector.correct.return_value = correction_result
        
        engine = SealEngine[simple_model](
            model=simple_model,
            llm_adapter=mock_components['llm_adapter'],
            prompt_builder=mock_components['prompt_builder'],
            parser=mock_components['parser'],
            validator=mock_validator,
            correctors=[mock_corrector]
        )
        
        with pytest.raises(EngineError, match="All correctors failed to produce valid data"):
            engine.run_sync("Test prompt")
        
        # Verify component interactions
        # In multi-corrector architecture, LLM is called only once
        assert mock_components['llm_adapter'].chat_completion_sync.call_count == 1
        assert mock_validator.validate.call_count == 3  # Initial + correction validation + validation after correction
        # Corrector is called once when validation fails
        assert mock_corrector.correct.call_count == 1
    
    def test_run_sync_llm_call_failure(self, simple_model, mock_components):
        """Test synchronous execution when LLM call fails."""
        
        # Mock LLM adapter to raise exception
        mock_llm_adapter = Mock(spec=LLMAdapter)
        mock_llm_adapter.chat_completion_sync.side_effect = Exception("LLM API error")
        
        engine = SealEngine[simple_model](
            model=simple_model,
            llm_adapter=mock_llm_adapter,
            prompt_builder=mock_components['prompt_builder'],
            parser=mock_components['parser'],
            validator=mock_components['validator'],
            correctors=mock_components['correctors']
        )
        
        with pytest.raises(EngineError):
            engine.run_sync("Test prompt")
    
    @pytest.mark.asyncio
    async def test_run_async_success(self, simple_model, mock_components):
        """Test successful asynchronous execution."""
        
        engine = SealEngine[simple_model](
            model=simple_model,
            llm_adapter=mock_components['llm_adapter'],
            prompt_builder=mock_components['prompt_builder'],
            parser=mock_components['parser'],
            validator=mock_components['validator'],
            correctors=mock_components['correctors']
        )
        
        result = await engine.run_async("Test prompt")
        
        assert result.success is True
        assert result.data is not None
        assert result.data.name == "John"
        assert result.data.age == 30
        assert result.retry_count == 0
        assert len(result.errors) == 0
        
        # Verify component interactions
        mock_components['llm_adapter'].chat_completion.assert_called_once()
        mock_components['parser'].parse.assert_called_once()
        mock_components['validator'].validate.assert_called_once()
    
    def test_build_prompt_with_instructions(self, simple_model, mock_components):
        """Test prompt building with format instructions."""
        
        engine = SealEngine[simple_model](
            model=simple_model,
            llm_adapter=mock_components['llm_adapter'],
            prompt_builder=mock_components['prompt_builder'],
            parser=mock_components['parser'],
            validator=mock_components['validator'],
            correctors=mock_components['correctors']
        )
        
        user_prompt = "Tell me about a person"
        combined_prompt = engine._build_prompt_with_instructions(user_prompt)
        
        assert user_prompt in combined_prompt
        assert "JSON format" in combined_prompt
        assert "schema" in combined_prompt
    
    def test_execution_step_creation(self, simple_model, mock_components):
        """Test execution step creation."""
        
        engine = SealEngine[simple_model](
            model=simple_model,
            llm_adapter=mock_components['llm_adapter'],
            prompt_builder=mock_components['prompt_builder'],
            parser=mock_components['parser'],
            validator=mock_components['validator'],
            correctors=mock_components['correctors']
        )
        
        step = engine._create_execution_step("test_step", "input_data")

        assert step.step_type == "test_step"
        assert step.input_data == "input_data"
        assert step.success is True
        assert step.error is None
        assert step.timestamp is not None

    def test_correction_prompt_retry_calls_llm_again(self, simple_model, mock_components):
        """Test that CORRECTION_PROMPT type triggers LLM re-call with corrected prompt."""

        from seal.codes.corrector.results import CorrectionResult

        # Mock validator to fail first time, succeed after retry
        mock_validator = Mock(spec=Validator)
        mock_fail_result = Mock()
        mock_fail_result.is_valid = False
        mock_fail_result.errors = ["Validation error"]

        mock_success_result = Mock()
        mock_success_result.is_valid = True
        mock_success_result.errors = []

        mock_validator.validate.side_effect = [
            mock_fail_result,  # First validation fails
            mock_success_result  # Second validation succeeds after LLM retry
        ]

        # Mock corrector to return CORRECTION_PROMPT type
        mock_corrector = Mock(spec=CorrectionStrategy)
        mock_corrector.max_retries = 3
        mock_corrector.correction_type = CorrectionType.CORRECTION_PROMPT
        mock_corrector.get_strategy_name.return_value = "PromptFixCorrector"

        # Create correction result with CORRECTION_PROMPT type
        correction_result = CorrectionResult(
            correction_type=CorrectionType.CORRECTION_PROMPT,
            result="Corrected user prompt with instructions"
        )
        mock_corrector.correct.return_value = correction_result

        # Mock LLM adapter to return different responses
        mock_llm_responses = [
            Mock(content='{"name": "invalid", "age": "not_a_number"}'),  # First call - invalid
            Mock(content='{"name": "John", "age": 30}')  # Second call - valid after retry
        ]
        mock_components['llm_adapter'].chat_completion_sync.side_effect = mock_llm_responses

        # Mock parser to parse both responses
        mock_components['parser'].parse.side_effect = [
            {"name": "invalid", "age": "not_a_number"},  # First parse - invalid
            {"name": "John", "age": 30}  # Second parse - valid
        ]

        engine = SealEngine[simple_model](
            model=simple_model,
            llm_adapter=mock_components['llm_adapter'],
            prompt_builder=mock_components['prompt_builder'],
            parser=mock_components['parser'],
            validator=mock_validator,
            correctors=[mock_corrector]
        )

        result = engine.run_sync("Test prompt")

        # Verify success
        assert result.success is True
        assert result.data is not None
        assert result.data.name == "John"
        assert result.data.age == 30

        # Verify LLM was called twice (initial + retry)
        assert mock_components['llm_adapter'].chat_completion_sync.call_count == 2

        # Verify corrector was called once
        mock_corrector.correct.assert_called_once()

        # Verify parser was called twice
        assert mock_components['parser'].parse.call_count == 2

        # Verify validator was called twice (initial + after retry)
        assert mock_validator.validate.call_count == 2

    def test_correction_prompt_retry_exhausted_moves_to_next_corrector(self, simple_model):
        """Test that when CORRECTION_PROMPT retry is exhausted, it moves to next corrector."""

        from seal.codes.corrector.results import CorrectionResult

        # Mock validator to always fail initially
        mock_validator = Mock(spec=Validator)
        mock_fail_result = Mock()
        mock_fail_result.is_valid = False
        mock_fail_result.errors = ["Validation error"]

        mock_success_result = Mock()
        mock_success_result.is_valid = True
        mock_success_result.errors = []

        # First corrector: CORRECTION_PROMPT with max_retries=1, fails after retry
        # Second corrector: CORRECTED_DATA, succeeds
        mock_validator.validate.side_effect = [
            mock_fail_result,  # Initial validation
            mock_fail_result,  # After first corrector's retry - still fails
            mock_success_result  # After second corrector's data correction - succeeds
        ]

        # First corrector: returns CORRECTION_PROMPT, exhausts retry
        mock_corrector1 = Mock(spec=CorrectionStrategy)
        mock_corrector1.max_retries = 1
        mock_corrector1.correction_type = CorrectionType.CORRECTION_PROMPT
        mock_corrector1.get_strategy_name.return_value = "PromptFixCorrector"

        correction_result1 = CorrectionResult(
            correction_type=CorrectionType.CORRECTION_PROMPT,
            result="Corrected prompt"
        )
        mock_corrector1.correct.return_value = correction_result1

        # Second corrector: returns CORRECTED_DATA, succeeds
        mock_corrector2 = Mock(spec=CorrectionStrategy)
        mock_corrector2.max_retries = 0
        mock_corrector2.correction_type = CorrectionType.CORRECTED_DATA
        mock_corrector2.get_strategy_name.return_value = "DataFixCorrector"

        correction_result2 = CorrectionResult(
            correction_type=CorrectionType.CORRECTED_DATA,
            result={"name": "John", "age": 30}
        )
        mock_corrector2.correct.return_value = correction_result2

        # Mock LLM adapter
        mock_llm_adapter = Mock(spec=LLMAdapter)
        mock_llm_adapter.chat_completion_sync.side_effect = [
            Mock(content='{"name": "invalid", "age": "not_a_number"}'),  # Initial
            Mock(content='{"name": "still_invalid", "age": "not_a_number"}')  # After retry
        ]

        # Mock parser
        mock_parser = Mock(spec=JsonParser)
        mock_parser.parse.side_effect = [
            {"name": "invalid", "age": "not_a_number"},
            {"name": "still_invalid", "age": "not_a_number"}
        ]

        # Mock prompt builder
        mock_prompt_builder = Mock(spec=PromptBuilder)
        mock_prompt_builder.model = simple_model

        engine = SealEngine[simple_model](
            model=simple_model,
            llm_adapter=mock_llm_adapter,
            prompt_builder=mock_prompt_builder,
            parser=mock_parser,
            validator=mock_validator,
            correctors=[mock_corrector1, mock_corrector2]
        )

        result = engine.run_sync("Test prompt")

        # Verify success via second corrector
        assert result.success is True
        assert result.data.name == "John"
        assert result.data.age == 30

        # Verify LLM was called twice (initial + one retry from first corrector)
        assert mock_llm_adapter.chat_completion_sync.call_count == 2

        # Verify first corrector was called once
        mock_corrector1.correct.assert_called_once()

        # Verify second corrector was called once
        mock_corrector2.correct.assert_called_once()

    @pytest.mark.asyncio
    async def test_correction_prompt_retry_async_calls_llm_again(self, simple_model, mock_components):
        """Test that CORRECTION_PROMPT type triggers async LLM re-call with corrected prompt."""

        from seal.codes.corrector.results import CorrectionResult

        # Mock validator to fail first time, succeed after retry
        mock_validator = Mock(spec=Validator)
        mock_fail_result = Mock()
        mock_fail_result.is_valid = False
        mock_fail_result.errors = ["Validation error"]

        mock_success_result = Mock()
        mock_success_result.is_valid = True
        mock_success_result.errors = []

        mock_validator.validate.side_effect = [
            mock_fail_result,  # First validation fails
            mock_success_result  # Second validation succeeds after LLM retry
        ]

        # Mock corrector to return CORRECTION_PROMPT type
        mock_corrector = Mock(spec=CorrectionStrategy)
        mock_corrector.max_retries = 3
        mock_corrector.correction_type = CorrectionType.CORRECTION_PROMPT
        mock_corrector.get_strategy_name.return_value = "PromptFixCorrector"

        # Create correction result with CORRECTION_PROMPT type
        correction_result = CorrectionResult(
            correction_type=CorrectionType.CORRECTION_PROMPT,
            result="Corrected user prompt with instructions"
        )
        mock_corrector.correct.return_value = correction_result

        # Mock LLM adapter to return different responses
        mock_llm_responses = [
            Mock(content='{"name": "invalid", "age": "not_a_number"}'),  # First call - invalid
            Mock(content='{"name": "John", "age": 30}')  # Second call - valid after retry
        ]
        mock_components['llm_adapter'].chat_completion = AsyncMock(side_effect=mock_llm_responses)

        # Mock parser to parse both responses
        mock_components['parser'].parse.side_effect = [
            {"name": "invalid", "age": "not_a_number"},  # First parse - invalid
            {"name": "John", "age": 30}  # Second parse - valid
        ]

        engine = SealEngine[simple_model](
            model=simple_model,
            llm_adapter=mock_components['llm_adapter'],
            prompt_builder=mock_components['prompt_builder'],
            parser=mock_components['parser'],
            validator=mock_validator,
            correctors=[mock_corrector]
        )

        result = await engine.run_async("Test prompt")

        # Verify success
        assert result.success is True
        assert result.data is not None
        assert result.data.name == "John"
        assert result.data.age == 30

        # Verify LLM was called twice (initial + retry)
        assert mock_components['llm_adapter'].chat_completion.call_count == 2

        # Verify corrector was called once
        mock_corrector.correct.assert_called_once()

        # Verify parser was called twice
        assert mock_components['parser'].parse.call_count == 2

        # Verify validator was called twice
        assert mock_validator.validate.call_count == 2


class TestEngineResult:
    """Test cases for EngineResult class."""
    
    def test_engine_result_initialization(self):
        """Test EngineResult initialization."""
        
        result = EngineResult(success=True)
        
        assert result.success is True
        assert result.data is None
        assert result.errors == []
        assert result.retry_count == 0
        assert result.execution_log == []
        assert result.final_prompt is None
    
    def test_engine_result_methods(self):
        """Test EngineResult methods."""
        
        result = EngineResult(success=True)
        
        assert result.is_successful() is True
        assert result.get_data() is None
        assert result.get_errors() == []
        assert result.get_retry_count() == 0
        assert result.get_execution_log() == []
    
    def test_engine_result_to_dict(self):
        """Test EngineResult serialization to dictionary."""
        
        result = EngineResult(success=True)
        result_dict = result.to_dict()
        
        assert result_dict["success"] is True
        assert result_dict["data"] is None
        assert result_dict["errors"] == []
        assert result_dict["retry_count"] == 0
        assert result_dict["execution_steps"] == 0
        assert result_dict["final_prompt"] is None


