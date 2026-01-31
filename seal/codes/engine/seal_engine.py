"""SealEngine implementation for orchestrating structured output guarantee process."""

import time
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from seal.codes.corrector import CorrectionStrategy
from seal.codes.corrector.types import CorrectionType
from seal.codes.llm.base import LLMAdapter
from seal.codes.parser import JsonParser
from seal.codes.prompt import PromptBuilder
from seal.codes.schema import SealModel
from seal.codes.validation import Validator, ValidationResult

from .errors import EngineError, LLMCallError, MaxRetriesExceededError
from .results import EngineResult, ExecutionStep


T = TypeVar('T', bound=SealModel)


class SealEngine(Generic[T]):
    """SealEngine orchestrates the entire structured output guarantee process."""
    
    def __init__(self, 
                 model: Type[T],
                 llm_adapter: LLMAdapter,
                 prompt_builder: PromptBuilder[T],
                 parser: JsonParser,
                 validator: Validator[T],
                 correctors: List[CorrectionStrategy[T]]):
        """
        Initialize SealEngine with type-safe components.
        
        Args:
            model: The target SealModel type that all components should work with
            llm_adapter: LLM adapter for making API calls
            prompt_builder: PromptBuilder instance bound to the model type
            parser: JSON parser instance
            validator: Validator instance bound to the model type
            correctors: List of correction strategies bound to the model type
            config: Engine configuration (optional)
            
        Raises:
            ValueError: If any required component is invalid
        """
        # Validate inputs
        if not model:
            raise ValueError("Model is required")
        if not llm_adapter:
            raise ValueError("LLM adapter is required")
        if not prompt_builder:
            raise ValueError("PromptBuilder is required")
        if not parser:
            raise ValueError("Parser is required")
        if not validator:
            raise ValueError("Validator is required")
        if not correctors:
            raise ValueError("Correctors list cannot be empty")
        
        # Store components with type consistency
        self.model = model
        self.llm_adapter = llm_adapter
        self.prompt_builder = prompt_builder
        self.parser = parser
        self.validator = validator
        self.correctors = correctors
        
        # Initialize execution state
        self._execution_id: Optional[str] = None
    
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
    
    def _create_execution_step(self, 
                             step_type: str, 
                             input_data: Optional[Any] = None,
                             success: bool = True,
                             error: Optional[Exception] = None) -> ExecutionStep:
        """
        Create an execution step for logging.
        
        Args:
            step_type: Type of execution step
            input_data: Input data for the step
            success: Whether the step was successful
            error: Error if the step failed
            
        Returns:
            ExecutionStep instance
        """
        return ExecutionStep(
            step_type=step_type,
            input_data=input_data,
            success=success,
            error=error,
            timestamp=time.time()
        )
    
    def _build_prompt_with_instructions(self, user_prompt: str) -> str:
        """
        Build the final prompt by combining user prompt with format instructions.
        
        Args:
            user_prompt: Original user prompt
            
        Returns:
            Combined prompt with format instructions
        """
        format_instructions = self.prompt_builder.format_instructions
        
        # Combine user prompt with format instructions
        combined_prompt = f"""{user_prompt}

Please provide your response in the following JSON format:

{format_instructions}

Ensure your response is valid JSON that matches the schema above."""
        
        return combined_prompt
    
    def _call_llm(self, prompt: str, **kwargs) -> str:
        """
        Call LLM with the given prompt.
        
        Args:
            prompt: Prompt to send to LLM
            **kwargs: Additional parameters for LLM call
            
        Returns:
            LLM response content
            
        Raises:
            LLMCallError: If LLM call fails
        """
        try:
            # Use synchronous call for now (async will be implemented separately)
            response = self.llm_adapter.chat_completion_sync(prompt, **kwargs)
            return response.content
        except Exception as e:
            raise LLMCallError(e, prompt)
    
    async def _call_llm_async(self, prompt: str, **kwargs) -> str:
        """
        Call LLM asynchronously with the given prompt.
        
        Args:
            prompt: Prompt to send to LLM
            **kwargs: Additional parameters for LLM call
            
        Returns:
            LLM response content
            
        Raises:
            LLMCallError: If LLM call fails
        """
        try:
            response = await self.llm_adapter.chat_completion(prompt, **kwargs)
            return response.content
        except Exception as e:
            raise LLMCallError(e, prompt)
    
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """
        Parse LLM response to extract structured data.
        
        Args:
            response: LLM response text
            
        Returns:
            Parsed dictionary data
            
        Raises:
            JsonParseError: If parsing fails
        """
        return self.parser.parse(response)
    
    def _validate_data(self, data: Dict[str, Any]) -> ValidationResult:
        """
        Validate parsed data against the schema.
        
        Args:
            data: Data to validate
            
        Returns:
            ValidationResult object containing validation status and errors
        """
        return self.validator.validate(data)
    
    def _create_model_instance(self, data: Dict[str, Any]) -> T:
        """
        Create SealModel instance from validated data.
        
        Args:
            data: Validated data dictionary
            
        Returns:
            SealModel instance
            
        Raises:
            ValidationError: If data cannot be converted to model
        """
        return self.model(**data)
    
    def _generate_execution_id(self) -> str:
        """Generate a unique execution ID for logging."""
        return f"exec_{int(time.time() * 1000)}"
    
    def _run_execution_loop(self, 
                          result: EngineResult[T],
                          current_prompt: str,
                          llm_call_func,
                          **kwargs) -> tuple[EngineResult[T], str, int]:
        """
        Execute the main execution loop with the given LLM call function.
        
        Args:
            result: EngineResult instance to populate
            current_prompt: Current prompt to use
            llm_call_func: Function to call LLM (sync or async)
            **kwargs: Additional parameters for LLM call
            
        Returns:
            Tuple of (result, current_prompt, retry_count)
            
        Raises:
            EngineError: If execution fails
        """
        return self._execute_loop_template_sync(
            result, current_prompt,
            llm_step_name='llm_call',
            llm_call_func=llm_call_func,
            **kwargs
        )
    
    def run_sync(self, prompt: str, **kwargs) -> EngineResult[T]:
        """
        Run the engine synchronously.
        
        Args:
            prompt: User prompt to send to LLM
            **kwargs: Additional parameters for LLM call
            
        Returns:
            EngineResult containing the execution outcome
            
        Raises:
            EngineError: If engine execution fails
            MaxRetriesExceededError: If maximum retry attempts are exceeded
        """
        # Initialize execution
        self._execution_id = self._generate_execution_id()
        result = EngineResult[T](success=False)
        
        # Build the initial prompt with format instructions
        current_prompt = self._build_prompt_with_instructions(prompt)
        
        # Execute the main loop with synchronous LLM call
        result, _, _ = self._run_execution_loop(
            result, current_prompt, self._call_llm, **kwargs
        )
        
        return result
    
    async def _run_execution_loop_async(self, 
                                     result: EngineResult[T],
                                     current_prompt: str,
                                     **kwargs) -> tuple[EngineResult[T], str, int]:
        """
        Execute the main execution loop asynchronously.
        
        Args:
            result: EngineResult instance to populate
            current_prompt: Current prompt to use
            **kwargs: Additional parameters for LLM call
            
        Returns:
            Tuple of (result, current_prompt, retry_count)
            
        Raises:
            EngineError: If execution fails
        """
        return await self._execute_loop_template(
            result, current_prompt,
            llm_step_name='llm_call_async',
            llm_call_func=self._call_llm_async,
            **kwargs
        )
    
    async def run_async(self, prompt: str, **kwargs) -> EngineResult[T]:
        """
        Run the engine asynchronously.
        
        Args:
            prompt: User prompt to send to LLM
            **kwargs: Additional parameters for LLM call
            
        Returns:
            EngineResult containing the execution outcome
            
        Raises:
            EngineError: If engine execution fails
            MaxRetriesExceededError: If maximum retry attempts are exceeded
        """
        # Initialize execution
        self._execution_id = self._generate_execution_id()
        result = EngineResult[T](success=False)
        
        # Build the initial prompt with format instructions
        current_prompt = self._build_prompt_with_instructions(prompt)
        
        # Execute the main loop asynchronously
        result, _, _ = await self._run_execution_loop_async(
            result, current_prompt, **kwargs
        )
        
        return result
    


    def _execute_llm_step_sync(self, 
                         result: EngineResult[T],
                         current_prompt: str,
                         llm_step_name: str,
                         llm_call_func,
                         **kwargs) -> str:
        """Execute LLM call step synchronously.
        
        Args:
            result: EngineResult instance to populate
            current_prompt: Current prompt to send to LLM
            llm_step_name: Name for the execution step
            llm_call_func: Function to call LLM (sync)
            **kwargs: Additional parameters for LLM call
            
        Returns:
            LLM response content
            
        Raises:
            Exception: If LLM call fails
        """
        llm_step = self._create_execution_step(llm_step_name, current_prompt)
        try:
            response = llm_call_func(current_prompt, **kwargs)
            llm_step.output_data = response[:500] + "..." if len(response) > 500 else response
            llm_step.success = True
        except Exception as e:
            llm_step.success = False
            llm_step.error = e
            result.add_execution_step(llm_step)
            raise
        result.add_execution_step(llm_step)
        return response

    async def _execute_llm_step_async(self, 
                         result: EngineResult[T],
                         current_prompt: str,
                         llm_step_name: str,
                         llm_call_func,
                         **kwargs) -> str:
        """Execute LLM call step asynchronously.
        
        Args:
            result: EngineResult instance to populate
            current_prompt: Current prompt to send to LLM
            llm_step_name: Name for the execution step
            llm_call_func: Function to call LLM (async)
            **kwargs: Additional parameters for LLM call
            
        Returns:
            LLM response content
            
        Raises:
            Exception: If LLM call fails
        """
        llm_step = self._create_execution_step(llm_step_name, current_prompt)
        try:
            response = await llm_call_func(current_prompt, **kwargs)
            llm_step.output_data = response[:500] + "..." if len(response) > 500 else response
            llm_step.success = True
        except Exception as e:
            llm_step.success = False
            llm_step.error = e
            result.add_execution_step(llm_step)
            raise
        result.add_execution_step(llm_step)
        return response

    def _execute_parse_step(self, result: EngineResult[T], response: str) -> Dict[str, Any]:
        """Execute parse response step.
        
        Args:
            result: EngineResult instance to populate
            response: LLM response text
            
        Returns:
            Parsed dictionary data
            
        Raises:
            Exception: If parsing fails
        """
        parse_step = self._create_execution_step('parse', response)
        try:
            parsed_data = self._parse_response(response)
            parse_step.output_data = parsed_data
            parse_step.success = True
        except Exception as e:
            parse_step.success = False
            parse_step.error = e
            result.add_execution_step(parse_step)
            raise
        result.add_execution_step(parse_step)
        return parsed_data

    def _execute_validate_step(self, result: EngineResult[T], parsed_data: Dict[str, Any]) -> ValidationResult:
        """Execute validation step.
        
        Args:
            result: EngineResult instance to populate
            parsed_data: Data to validate
            
        Returns:
            ValidationResult object containing validation status and errors
            
        Raises:
            Exception: If validation fails
        """
        validate_step = self._create_execution_step('validate', parsed_data)
        try:
            validation_result = self._validate_data(parsed_data)
            validate_step.output_data = {"is_valid": validation_result.is_valid, "errors": validation_result.errors}
            validate_step.success = validation_result.is_valid
            
            if not validation_result.is_valid:
                result.errors = validation_result.errors
                validate_step.error = validation_result.errors[0] if validation_result.errors else None
        except Exception as e:
            validate_step.success = False
            validate_step.error = e
            result.add_execution_step(validate_step)
            raise
        result.add_execution_step(validate_step)
        return validation_result

    def _execute_model_step(self, result: EngineResult[T], parsed_data: Dict[str, Any]) -> T:
        """Execute model creation step.
        
        Args:
            result: EngineResult instance to populate
            parsed_data: Validated data dictionary
            
        Returns:
            SealModel instance
            
        Raises:
            Exception: If model creation fails
        """
        model_step = self._create_execution_step('create_model', parsed_data)
        try:
            model_instance = self._create_model_instance(parsed_data)
            model_step.output_data = model_instance
            model_step.success = True
            result.add_execution_step(model_step)
            return model_instance
        except Exception as e:
            model_step.success = False
            model_step.error = e
            result.add_execution_step(model_step)
            raise

    def _handle_success(self, 
                       result: EngineResult,
                       model_instance: SealModel,
                       current_prompt: str) -> tuple[EngineResult, str, int]:
        """Handle successful execution.
        
        Args:
            result: EngineResult instance to populate
            model_instance: Created model instance
            current_prompt: Current prompt used
            
        Returns:
            Tuple of (result, current_prompt, retry_count)
        """
        result.success = True
        result.data = model_instance
        result.retry_count = 0
        result.final_prompt = current_prompt
        return result, current_prompt, 0

    def _is_corrected_data_valid(self, data: Dict[str, Any]) -> bool:
        """验证修正后的数据是否有效"""
        try:
            validation_result = self._validate_data(data)
            return validation_result.is_valid
        except Exception:
            return False

    def _execute_corrector_chain_with_retry(self,
                                          result: EngineResult,
                                          parsed_data: Dict[str, Any],
                                          current_prompt: str,
                                          llm_call_func,
                                          **kwargs) -> tuple[EngineResult, str, int]:
        """Execute corrector chain with retry mechanism.

        When a corrector returns CORRECTION_PROMPT type, it will re-call LLM
        with the corrected prompt and go through the full flow (LLM -> Parse -> Validate).

        Args:
            result: EngineResult instance to populate
            parsed_data: Parsed data from initial LLM response
            current_prompt: Current prompt used
            llm_call_func: Function to call LLM (sync)
            **kwargs: Additional parameters for LLM call

        Returns:
            Tuple of (result, current_prompt, retry_count)

        Raises:
            EngineError: If all correctors fail to produce valid data
        """

        correction_state = self.CorrectionExecutionState(self.correctors)
        current_data = parsed_data
        current_errors = result.errors

        while correction_state.has_more_correctors():
            corrector = correction_state.get_current_corrector()
            if corrector is None:
                break

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

                # Handle correction result
                if correction_result.correction_type == CorrectionType.CORRECTED_DATA:
                    # Validate corrected data
                    if self._is_corrected_data_valid(correction_result.result):
                        result.add_execution_step(correction_step)
                        model_instance = self._create_model_instance(correction_result.result)
                        return self._handle_success(result, model_instance, current_prompt)
                    else:
                        # Data correction failed validation, move to next corrector
                        current_data = correction_result.result
                        validation_result = self._validate_data(current_data)
                        current_errors = validation_result.errors if not validation_result.is_valid else []
                        correction_state.move_to_next_corrector()

                elif correction_result.correction_type == CorrectionType.CORRECTION_PROMPT:
                    # Prompt correction, check if can retry
                    if correction_state.can_retry_current_corrector():
                        # Can retry, update prompt and re-call LLM
                        correction_state.increment_retry_count()
                        current_prompt = self._build_prompt_with_instructions(correction_result.result)

                        # Re-call LLM with corrected prompt
                        try:
                            response = self._execute_llm_step_sync(
                                result, current_prompt, 'llm_call_retry', llm_call_func, **kwargs
                            )
                            current_data = self._execute_parse_step(result, response)
                            validation_result = self._execute_validate_step(result, current_data)

                            if validation_result.is_valid:
                                # Success after retry
                                result.add_execution_step(correction_step)
                                model_instance = self._create_model_instance(current_data)
                                return self._handle_success(result, model_instance, current_prompt)
                            else:
                                # Still invalid after retry, update errors
                                current_errors = validation_result.errors
                                # Check if can retry again, if not, move to next corrector
                                if not correction_state.can_retry_current_corrector():
                                    correction_state.move_to_next_corrector()
                                # If can still retry, continue loop with same corrector
                        except Exception as e:
                            # LLM call failed during retry, move to next corrector
                            correction_state.move_to_next_corrector()
                    else:
                        # Cannot retry, move to next corrector
                        correction_state.move_to_next_corrector()

                result.add_execution_step(correction_step)

            except Exception as e:
                correction_step.success = False
                correction_step.error = e
                result.add_execution_step(correction_step)

                # Error handling: move to next corrector
                correction_state.move_to_next_corrector()

        # All correctors executed but none succeeded
        raise EngineError("All correctors failed to produce valid data")

    async def _execute_corrector_chain_with_retry_async(self,
                                                       result: EngineResult,
                                                       parsed_data: Dict[str, Any],
                                                       current_prompt: str,
                                                       llm_call_func,
                                                       **kwargs) -> tuple[EngineResult, str, int]:
        """Execute corrector chain with retry mechanism (async version).

        When a corrector returns CORRECTION_PROMPT type, it will re-call LLM
        with the corrected prompt and go through the full flow (LLM -> Parse -> Validate).

        Args:
            result: EngineResult instance to populate
            parsed_data: Parsed data from initial LLM response
            current_prompt: Current prompt used
            llm_call_func: Function to call LLM (async)
            **kwargs: Additional parameters for LLM call

        Returns:
            Tuple of (result, current_prompt, retry_count)

        Raises:
            EngineError: If all correctors fail to produce valid data
        """

        correction_state = self.CorrectionExecutionState(self.correctors)
        current_data = parsed_data
        current_errors = result.errors

        while correction_state.has_more_correctors():
            corrector = correction_state.get_current_corrector()
            if corrector is None:
                break

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

                # Handle correction result
                if correction_result.correction_type == CorrectionType.CORRECTED_DATA:
                    # Validate corrected data
                    if self._is_corrected_data_valid(correction_result.result):
                        result.add_execution_step(correction_step)
                        model_instance = self._create_model_instance(correction_result.result)
                        return self._handle_success(result, model_instance, current_prompt)
                    else:
                        # Data correction failed validation, move to next corrector
                        current_data = correction_result.result
                        validation_result = self._validate_data(current_data)
                        current_errors = validation_result.errors if not validation_result.is_valid else []
                        correction_state.move_to_next_corrector()

                elif correction_result.correction_type == CorrectionType.CORRECTION_PROMPT:
                    # Prompt correction, check if can retry
                    if correction_state.can_retry_current_corrector():
                        # Can retry, update prompt and re-call LLM
                        correction_state.increment_retry_count()
                        current_prompt = self._build_prompt_with_instructions(correction_result.result)

                        # Re-call LLM with corrected prompt
                        try:
                            response = await self._execute_llm_step_async(
                                result, current_prompt, 'llm_call_retry', llm_call_func, **kwargs
                            )
                            current_data = self._execute_parse_step(result, response)
                            validation_result = self._execute_validate_step(result, current_data)

                            if validation_result.is_valid:
                                # Success after retry
                                result.add_execution_step(correction_step)
                                model_instance = self._create_model_instance(current_data)
                                return self._handle_success(result, model_instance, current_prompt)
                            else:
                                # Still invalid after retry, update errors
                                current_errors = validation_result.errors
                                # Check if can retry again, if not, move to next corrector
                                if not correction_state.can_retry_current_corrector():
                                    correction_state.move_to_next_corrector()
                                # If can still retry, continue loop with same corrector
                        except Exception as e:
                            # LLM call failed during retry, move to next corrector
                            correction_state.move_to_next_corrector()
                    else:
                        # Cannot retry, move to next corrector
                        correction_state.move_to_next_corrector()

                result.add_execution_step(correction_step)

            except Exception as e:
                correction_step.success = False
                correction_step.error = e
                result.add_execution_step(correction_step)

                # Error handling: move to next corrector
                correction_state.move_to_next_corrector()

        # All correctors executed but none succeeded
        raise EngineError("All correctors failed to produce valid data")

    def _execute_loop_template_sync(self, 
                                   result: EngineResult[T],
                                   current_prompt: str,
                                   llm_step_name: str,
                                   llm_call_func,
                                   **kwargs) -> tuple[EngineResult[T], str, int]:
        """Unified execution loop template for synchronous operations.
    
        Args:
            result: EngineResult instance to populate
            current_prompt: Current prompt to use
            llm_step_name: Name for the LLM execution step
            llm_call_func: Function to call LLM (sync)
            **kwargs: Additional parameters for LLM call
    
        Returns:
            Tuple of (result, current_prompt, retry_count)
    
        Raises:
            EngineError: If execution fails
        """
        try:
            # Step 1: Call LLM
            response = self._execute_llm_step_sync(
                result, current_prompt, llm_step_name, llm_call_func, **kwargs
            )

            # Step 2: Parse response
            parsed_data = self._execute_parse_step(result, response)

            # Step 3: Validate data
            validation_result = self._execute_validate_step(result, parsed_data)

            if validation_result.is_valid:
                # Step 4: Create model instance (success path)
                model_instance = self._execute_model_step(result, parsed_data)
                return self._handle_success(result, model_instance, current_prompt)
            else:
                # Validation failed, execute corrector chain with retry
                return self._execute_corrector_chain_with_retry(
                    result, parsed_data, current_prompt, llm_call_func, **kwargs
                )

        except Exception as e:
            # Update result with current state
            result.retry_count = 0  # Retry count managed at corrector level
            result.final_prompt = current_prompt

            # Re-raise exception, retry managed at corrector level
            raise EngineError(f"Engine execution failed: {e}")

    async def _execute_loop_template(self,
                                   result: EngineResult[T],
                                   current_prompt: str,
                                   llm_step_name: str,
                                   llm_call_func,
                                   **kwargs) -> tuple[EngineResult[T], str, int]:
        """Unified execution loop template for asynchronous operations.
    
        Args:
            result: EngineResult instance to populate
            current_prompt: Current prompt to use
            llm_step_name: Name for the LLM execution step
            llm_call_func: Function to call LLM (async)
            **kwargs: Additional parameters for LLM call
    
        Returns:
            Tuple of (result, current_prompt, retry_count)
    
        Raises:
            EngineError: If execution fails
        """
        try:
            # Step 1: Call LLM
            response = await self._execute_llm_step_async(
                result, current_prompt, llm_step_name, llm_call_func, **kwargs
            )
    
            # Step 2: Parse response
            parsed_data = self._execute_parse_step(result, response)
    
            # Step 3: Validate data
            validation_result = self._execute_validate_step(result, parsed_data)

            if validation_result.is_valid:
                # Step 4: Create model instance (success path)
                model_instance = self._execute_model_step(result, parsed_data)
                return self._handle_success(result, model_instance, current_prompt)
            else:
                # Validation failed, execute corrector chain with retry
                return await self._execute_corrector_chain_with_retry_async(
                    result, parsed_data, current_prompt, llm_call_func, **kwargs
                )

        except Exception as e:
            # Update result with current state
            result.retry_count = 0  # Retry count managed at corrector level
            result.final_prompt = current_prompt

            # Re-raise exception, retry managed at corrector level
            raise EngineError(f"Engine execution failed: {e}")
