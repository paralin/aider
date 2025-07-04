#!/usr/bin/env python

"""
CORT (Chain of Recursive Thought) Coder Implementation

This module implements the CortCoder class and supporting managers that provide
Chain of Recursive Thought capabilities as a wrapper around any existing Aider coder.

Architecture Overview:
- CortCoder: Main class that inherits from BaseCoder and acts as a wrapper
- CortConversationManager: Handles CORT's thinking rounds and state management
- CortThreadingManager: Coordinates API calls and integrates with Aider's systems

Key Design Principles:
1. Wrapper Pattern: CortCoder enhances any edit format without changing it
2. Separation of Concerns: Clear boundaries between conversation, threading, and main logic
3. Compatibility: Full backwards compatibility with existing Aider functionality
4. Extensibility: Foundation for future phases of the refactoring
"""

import sys
import time
import traceback
from typing import Dict, List, Optional, Generator, Any

from .base_coder import Coder
from .cort_types import (
    CortState,
    CortMessage,
    CortThinkingRound,
    CortEvaluationResult,
    CortConfig,
    CortMessageType,
    CortRoundStatus,
    DEFAULT_CORT_CONFIG,
)


class CortConversationManager:
    """
    Manages CORT conversation state and thinking rounds.

    This class handles the core CORT logic of generating alternatives,
    evaluating responses, and tracking the iterative thinking process.
    Separated from the main CortCoder for clean architecture.
    """

    def __init__(self, coder: "Coder", config: CortConfig = None):
        self.coder = coder
        self.config = config or DEFAULT_CORT_CONFIG
        self.current_state: Optional[CortState] = None

    def start_thinking_session(self, user_input: str) -> CortState:
        """
        Initialize a new CORT thinking session.

        Args:
            user_input: The original user prompt to process

        Returns:
            CortState object tracking this session
        """
        thinking_rounds = self._determine_thinking_rounds(user_input)

        self.current_state = CortState(
            original_prompt=user_input, thinking_rounds_planned=thinking_rounds
        )

        # Add initial message to history
        initial_msg = CortMessage(
            role="user",
            content=user_input,
            round_number=0,
            message_type=CortMessageType.INITIAL,
        )
        self.current_state.add_message(initial_msg)

        return self.current_state

    def _determine_thinking_rounds(self, prompt: str) -> int:
        """
        Determine how many thinking rounds are needed for this prompt.

        Uses the LLM to intelligently determine optimal round count.

        Args:
            prompt: The user's input prompt

        Returns:
            Number of thinking rounds to perform (1-5)
        """
        meta_prompt = f"""Given this message: "{prompt}"

How many rounds of iterative thinking (1-5) would be optimal to generate the best response?
Consider the complexity and nuance required.
Respond with just a number between 1 and 5."""

        messages = [{"role": "user", "content": meta_prompt}]

        self.coder.io.tool_output("\n=== CORT: DETERMINING THINKING ROUNDS ===")

        try:
            # Use Aider's integrated send_completion method
            hash_obj, completion = self.coder.main_model.send_completion(
                messages, functions=None, stream=False, temperature=0.3
            )
            response = completion.choices[0].message.content.strip()

            # Display the response
            self.coder.io.assistant_output(response, pretty=self.coder.show_pretty())

        except Exception as e:
            self.coder.io.tool_error(f"Error determining thinking rounds: {e}")
            self.coder.io.tool_output("Defaulting to 3 rounds")
            return 3

        self.coder.io.tool_output("=" * 50 + "\n")

        try:
            rounds = int("".join(filter(str.isdigit, response)))
            return min(max(rounds, 1), 5)
        except:
            return 3

    def generate_initial_response(self, user_input: str) -> str:
        """
        Generate the initial response for CORT processing.

        Uses Aider's message formatting and send system to generate the response.

        Args:
            user_input: The original user prompt

        Returns:
            Initial response content
        """
        # Add user input to current messages temporarily for formatting
        original_cur_messages = list(self.coder.cur_messages)
        self.coder.cur_messages += [dict(role="user", content=user_input)]

        try:
            # Use Aider's message formatting system
            chunks = self.coder.format_messages()
            messages = chunks.all_messages()

            # Make the API call using Aider's integrated system
            hash_obj, completion = self.coder.main_model.send_completion(
                messages, functions=None, stream=False, temperature=0.7
            )

            response = completion.choices[0].message.content.strip()

            if self.current_state:
                self.current_state.update_best_response(response)

            return response

        except Exception as e:
            self.coder.io.tool_error(f"Error generating initial response: {e}")
            fallback = f"Error generating response to: {user_input}"
            if self.current_state:
                self.current_state.update_best_response(fallback)
            return fallback
        finally:
            # Restore original cur_messages
            self.coder.cur_messages = original_cur_messages

    def _generate_alternatives(
        self, current_best: str, original_prompt: str, round_num: int
    ) -> List[str]:
        """
        Generate alternative responses for evaluation.

        Creates alternative responses using the LLM with varied prompting.

        Args:
            current_best: The current best response
            original_prompt: The original user prompt
            round_num: Current thinking round number

        Returns:
            List of alternative responses
        """
        alternatives = []

        for i in range(self.config.num_alternatives_per_round):
            try:
                alt_prompt = f"""Original message: {original_prompt}

Current response being considered:
{current_best}

Generate an alternative response that might be better. Be creative and consider different approaches.
Alternative response:"""

                # Create a fresh conversation for alternatives
                messages = [{"role": "user", "content": alt_prompt}]

                # Use Aider's integrated send_completion
                hash_obj, completion = self.coder.main_model.send_completion(
                    messages,
                    functions=None,
                    stream=False,
                    temperature=0.7 + i * 0.1,  # Increase diversity
                )

                alternative = completion.choices[0].message.content.strip()
                alternatives.append(alternative)

            except Exception as e:
                self.coder.io.tool_error(f"Error generating alternative {i+1}: {e}")
                alternatives.append(f"[Error generating alternative {i+1}]")

        return alternatives

    def _evaluate_responses(
        self, original_prompt: str, current_best: str, alternatives: List[str]
    ) -> CortEvaluationResult:
        """
        Evaluate responses and select the best one.

        Uses the LLM to intelligently evaluate and select responses.

        Args:
            original_prompt: The original user prompt
            current_best: Current best response
            alternatives: Alternative responses to evaluate

        Returns:
            CortEvaluationResult with selection and reasoning
        """
        try:
            eval_prompt = f"""Original message: {original_prompt}

Evaluate these responses and choose the best one:

Current best: {current_best}

Alternatives:
{chr(10).join([f"{i+1}. {alt}" for i, alt in enumerate(alternatives)])}

Which response best addresses the original message? Consider accuracy, clarity, and completeness.
First, respond with ONLY 'current' or a number (1-{len(alternatives)}).
Then on a new line, explain your choice in one sentence."""

            messages = [{"role": "user", "content": eval_prompt}]

            # Use Aider's integrated send_completion with low temperature for consistency
            hash_obj, completion = self.coder.main_model.send_completion(
                messages, functions=None, stream=False, temperature=0.2
            )

            evaluation = completion.choices[0].message.content.strip()

        except Exception as e:
            self.coder.io.tool_error(f"Error evaluating responses: {e}")
            evaluation = "current\nError in evaluation, keeping current response."

        # Parse the evaluation
        lines = [line.strip() for line in evaluation.split("\n") if line.strip()]

        choice = "current"
        explanation = "No explanation provided"

        if lines:
            first_line = lines[0].lower()
            if "current" in first_line:
                choice = "current"
            else:
                for char in first_line:
                    if char.isdigit():
                        choice = char
                        break

            if len(lines) > 1:
                explanation = " ".join(lines[1:])

        if choice == "current":
            return CortEvaluationResult(
                selected_response=current_best,
                selected_index=-1,
                evaluation_reasoning=explanation,
                alternatives_considered=alternatives,
            )
        else:
            try:
                index = int(choice) - 1
                if 0 <= index < len(alternatives):
                    return CortEvaluationResult(
                        selected_response=alternatives[index],
                        selected_index=index,
                        evaluation_reasoning=explanation,
                        alternatives_considered=alternatives,
                    )
            except:
                pass

        # Fallback to current best
        return CortEvaluationResult(
            selected_response=current_best,
            selected_index=-1,
            evaluation_reasoning=explanation,
            alternatives_considered=alternatives,
        )

    def process_thinking_round(self, round_num: int) -> CortThinkingRound:
        """
        Process a single thinking round.

        Args:
            round_num: The round number to process

        Returns:
            CortThinkingRound object with results
        """
        if not self.current_state:
            raise ValueError("No active CORT session")

        round_obj = CortThinkingRound(round_number=round_num)
        round_obj.status = CortRoundStatus.GENERATING

        try:
            # Generate alternatives
            alternatives = self._generate_alternatives(
                self.current_state.current_best_response,
                self.current_state.original_prompt,
                round_num,
            )
            round_obj.alternatives = alternatives
            round_obj.status = CortRoundStatus.EVALUATING

            # Evaluate and select best
            evaluation = self._evaluate_responses(
                self.current_state.original_prompt,
                self.current_state.current_best_response,
                alternatives,
            )

            # Update state
            round_obj.mark_completed(
                evaluation.selected_response, evaluation.evaluation_reasoning
            )

            # Update session state
            self.current_state.update_best_response(evaluation.selected_response)
            self.current_state.add_round(round_obj)

        except Exception as e:
            round_obj.mark_failed(str(e))

        return round_obj


class CortThreadingManager:
    """
    Manages threading and integration with Aider's systems.

    This class coordinates CORT's API calls and ensures proper integration
    with Aider's threading, caching, and streaming systems.
    """

    def __init__(self, coder: "Coder"):
        self.coder = coder

    def ensure_aider_systems_ready(self):
        """
        Ensure Aider's threading and caching systems are ready.

        Integrates with Aider's cache warming and threading systems.
        """
        # Start cache warming if configured
        if hasattr(self.coder, "warm_cache") and self.coder.ok_to_warm_cache:
            try:
                chunks = self.coder.format_messages()
                self.coder.warm_cache(chunks)
            except Exception as e:
                self.coder.io.tool_warning(f"Cache warming failed: {e}")

    def _make_api_call(self, messages: List[Dict], **kwargs) -> str:
        """
        Coordinate API calls through Aider's systems.

        Uses Aider's send_completion method and threading systems properly.

        Args:
            messages: Messages to send to the LLM
            **kwargs: Additional arguments for the API call

        Returns:
            Response content from the LLM
        """
        try:
            # Use Aider's integrated model send_completion method
            temperature = kwargs.get("temperature", 0.7)
            stream = kwargs.get("stream", False)

            hash_obj, completion = self.coder.main_model.send_completion(
                messages, functions=None, stream=stream, temperature=temperature
            )

            if stream:
                # Handle streaming response
                full_response = ""
                for chunk in completion:
                    if (
                        chunk.choices
                        and chunk.choices[0].delta
                        and chunk.choices[0].delta.content
                    ):
                        content = chunk.choices[0].delta.content
                        full_response += content
                        # Display streaming content
                        if self.coder.show_pretty():
                            # Use pretty streaming if available
                            try:
                                sys.stdout.write(content)
                                sys.stdout.flush()
                            except UnicodeEncodeError:
                                safe_content = content.encode(
                                    sys.stdout.encoding, errors="backslashreplace"
                                ).decode(sys.stdout.encoding)
                                sys.stdout.write(safe_content)
                                sys.stdout.flush()
                        else:
                            # Simple stdout streaming
                            try:
                                sys.stdout.write(content)
                                sys.stdout.flush()
                            except UnicodeEncodeError:
                                safe_content = content.encode(
                                    sys.stdout.encoding, errors="backslashreplace"
                                ).decode(sys.stdout.encoding)
                                sys.stdout.write(safe_content)
                                sys.stdout.flush()
                return full_response
            else:
                # Handle non-streaming response
                response = completion.choices[0].message.content.strip()
                # Display the response using Aider's assistant_output
                self.coder.io.assistant_output(
                    response, pretty=self.coder.show_pretty()
                )
                return response

        except Exception as e:
            self.coder.io.tool_error(f"API call failed: {e}")
            return "Error: Could not get response from API"

    def _warm_cache(self, chunks) -> None:
        """
        Use existing Aider cache warming thread.

        Args:
            chunks: Message chunks to warm cache with
        """
        if hasattr(self.coder, "warm_cache") and self.coder.ok_to_warm_cache:
            try:
                self.coder.warm_cache(chunks)
            except Exception as e:
                self.coder.io.tool_warning(f"Cache warming failed: {e}")

    def _handle_streaming(self, content: str) -> Generator[str, None, None]:
        """
        Stream response content using Aider's streaming systems.

        Args:
            content: Content to stream

        Yields:
            Individual characters or chunks for streaming
        """
        if self.coder.stream:
            # Use Aider's streaming display system
            if self.coder.show_pretty():
                mdstream = self.coder.io.get_assistant_mdstream()
                mdstream.update(content, final=True)
            else:
                # Stream character by character for non-pretty output
                for char in content:
                    yield char
                    # Small delay to simulate realistic streaming
                    time.sleep(0.001)
        else:
            # Return all at once
            yield content


class CortCoder(Coder):
    """
    Main CORT Coder class that wraps any existing Aider coder with CORT capabilities.

    This class inherits from BaseCoder to maintain full compatibility with Aider's
    systems while adding Chain of Recursive Thought processing. It acts as a wrapper
    that can enhance any edit format with CORT thinking capabilities.

    Key Features:
    - Inherits from BaseCoder for full compatibility
    - Wraps any edit format (editblock, wholefile, architect, etc.)
    - Adds CORT thinking without changing underlying edit behavior
    - Maintains all existing Aider functionality

    Architecture:
    - Uses composition pattern with manager classes
    - Delegates CORT logic to specialized managers
    - Overrides send_message() to inject CORT processing
    - Falls back gracefully on errors
    """

    # Edit format is set to None - CortCoder wraps other formats
    edit_format = None

    def __init__(self, main_model, io, **kwargs):
        """
        Initialize CortCoder with CORT-specific components and proper attribute delegation.

        Args:
            main_model: The language model to use
            io: Input/output handler
            **kwargs: Additional arguments passed to BaseCoder
        """
        # Set up essential attributes BEFORE calling super().__init__
        # This prevents recursion issues in __getattr__ during base class initialization
        self._setup_essential_attributes()

        # Create a base coder instance to delegate to for essential attributes
        self._setup_base_coder(main_model, io, **kwargs)

        # Copy essential attributes from the base coder
        self._copy_base_coder_attributes()

        # Initialize base coder functionality
        super().__init__(main_model, io, **kwargs)

        # Initialize CORT-specific components
        self.cort_config = kwargs.get("cort_config", DEFAULT_CORT_CONFIG)
        self.conversation_manager = CortConversationManager(self, self.cort_config)
        self.threading_manager = CortThreadingManager(self)

        # CORT session tracking
        self.current_cort_session: Optional[CortState] = None
        self.cort_history: List[CortState] = []

        # Override cort_enabled to True since this IS the CORT coder
        self.cort_enabled = True

    def _setup_essential_attributes(self):
        """
        Set up essential attributes early to prevent recursion issues.
        """
        # Initialize base_coder to None to prevent recursion in __getattr__
        self.base_coder = None

        # Set up default gpt_prompts to prevent issues during base class initialization
        from .editblock_prompts import EditBlockPrompts

        self.gpt_prompts = EditBlockPrompts()

        # Set up default fence attributes
        from .base_coder import all_fences

        self.fences = all_fences
        self.fence = self.fences[0]

    def _setup_base_coder(self, main_model, io, **kwargs):
        """
        Create a base coder instance to delegate essential attributes to.

        This ensures CortCoder has access to all the attributes that base coders provide,
        particularly gpt_prompts which many methods expect to find.
        """
        # Import here to avoid circular imports
        from .editblock_coder import EditBlockCoder

        # Use EditBlockCoder as the default base coder since it's widely compatible
        # and provides the essential gpt_prompts attribute
        base_kwargs = dict(kwargs)
        base_kwargs.pop("cort", None)  # Remove cort flag to avoid recursion
        base_kwargs.pop("cort_config", None)  # Remove CORT-specific config

        try:
            self.base_coder = EditBlockCoder(main_model, io, **base_kwargs)
        except Exception as e:
            # Fallback: just create a minimal coder for attribute access
            from .base_coder import Coder

            self.base_coder = Coder(main_model, io, **base_kwargs)
            # If even that fails, we'll handle it in _copy_base_coder_attributes

    def _copy_base_coder_attributes(self):
        """
        Copy essential attributes from the base coder to ensure compatibility.

        This addresses the core issue where CORT methods expect certain attributes
        like gpt_prompts to be available.
        """
        if hasattr(self, "base_coder") and hasattr(self.base_coder, "gpt_prompts"):
            self.gpt_prompts = self.base_coder.gpt_prompts
        else:
            # Fallback: import and use EditBlockPrompts directly
            from .editblock_prompts import EditBlockPrompts

            self.gpt_prompts = EditBlockPrompts()

        # Copy other essential attributes that might be needed
        if hasattr(self, "base_coder"):
            # Copy fence configuration
            if hasattr(self.base_coder, "fence"):
                self.fence = self.base_coder.fence
            if hasattr(self.base_coder, "fences"):
                self.fences = self.base_coder.fences

        # Ensure we have fence attributes even if base_coder doesn't have them
        if not hasattr(self, "fence"):
            # Use the default fence from base_coder
            from .base_coder import all_fences

            self.fences = all_fences
            self.fence = self.fences[0]

    def __getattr__(self, name):
        """
        Delegate missing attributes to the base coder for transparent wrapper behavior.

        This ensures that CortCoder acts as a transparent proxy for all base coder
        functionality while adding CORT capabilities.
        """
        # Prevent recursion by using __dict__ access instead of hasattr
        if "base_coder" in self.__dict__ and self.base_coder is not None:
            if hasattr(self.base_coder, name):
                return getattr(self.base_coder, name)

        # If the attribute doesn't exist, raise the standard AttributeError
        raise AttributeError(
            f"'{type(self).__name__}' object has no attribute '{name}'"
        )

    def send_message(self, inp: str) -> Generator[str, None, None]:
        """
        Override send_message to provide CORT thinking capabilities.

        This is the main entry point for CORT processing. It intercepts
        user input, performs CORT thinking, then delegates to the base
        coder for actual file editing.

        Args:
            inp: User input message

        Yields:
            Response content (streamed)
        """
        try:
            # Initialize CORT session
            self.io.tool_output("\n" + "=" * 50)
            self.io.tool_output("🤔 CORT: RECURSIVE THINKING PROCESS STARTING")
            self.io.tool_output("=" * 50)

            # Ensure Aider systems are ready
            self.threading_manager.ensure_aider_systems_ready()

            # Start CORT thinking session
            cort_state = self.conversation_manager.start_thinking_session(inp)
            self.current_cort_session = cort_state

            self.io.tool_output(
                f"\n🤔 CORT: Planning {cort_state.thinking_rounds_planned} thinking rounds"
            )

            # Generate initial response
            self.io.tool_output("\n=== CORT: GENERATING INITIAL RESPONSE ===")
            current_best = self.conversation_manager.generate_initial_response(inp)
            self.io.assistant_output(current_best, pretty=self.show_pretty())
            self.io.tool_output("=" * 50)

            # Perform thinking rounds
            for round_num in range(1, cort_state.thinking_rounds_planned + 1):
                self.io.tool_output(
                    f"\n=== CORT: THINKING ROUND {round_num}/{cort_state.thinking_rounds_planned} ==="
                )

                thinking_round = self.conversation_manager.process_thinking_round(
                    round_num
                )

                if thinking_round.status == CortRoundStatus.COMPLETED:
                    self.io.tool_output(
                        f"✅ Round {round_num} completed: {thinking_round.evaluation_reason}"
                    )
                    current_best = thinking_round.selected_response
                else:
                    self.io.tool_output(
                        f"❌ Round {round_num} failed: {thinking_round.evaluation_reason}"
                    )

                self.io.tool_output("=" * 50)

            # Finalize CORT session
            cort_state.mark_complete()
            self.cort_history.append(cort_state)

            self.io.tool_output("\n" + "=" * 50)
            self.io.tool_output("🎯 CORT: FINAL RESPONSE SELECTED")
            self.io.tool_output("=" * 50)

            # Set up for normal Aider processing
            self.partial_response_content = current_best

            # Add to cur_messages for Aider's history tracking
            self.cur_messages += [
                dict(role="user", content=inp),
                dict(role="assistant", content=current_best),
            ]

            # Stream the final response
            yield from self.threading_manager._handle_streaming(current_best)

        except Exception as e:
            self.io.tool_error(f"CORT processing failed: {e}")
            if self.verbose:
                traceback.print_exc()

            # Fall back to normal processing
            self.io.tool_output("Falling back to normal Aider processing...")
            yield from super().send_message(inp)

    def get_cort_session_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the current CORT session.

        Returns:
            Dictionary with session statistics and information
        """
        if not self.current_cort_session:
            return {"status": "no_active_session"}

        state = self.current_cort_session
        return {
            "session_id": state.session_id,
            "status": "completed" if state.is_complete() else "active",
            "rounds_planned": state.thinking_rounds_planned,
            "rounds_completed": len(state.rounds_history),
            "total_duration": state.total_duration,
            "success_rate": state.success_rate,
            "total_api_calls": state.total_api_calls,
            "total_tokens": state.total_tokens_used,
            "alternatives_generated": state.total_alternatives_generated,
        }

    def get_cort_history_summary(self) -> List[Dict[str, Any]]:
        """
        Get a summary of all CORT sessions.

        Returns:
            List of session summaries
        """
        return [
            {
                "session_id": session.session_id,
                "original_prompt": (
                    session.original_prompt[:100] + "..."
                    if len(session.original_prompt) > 100
                    else session.original_prompt
                ),
                "rounds_completed": len(session.rounds_history),
                "total_duration": session.total_duration,
                "success_rate": session.success_rate,
                "start_time": session.start_time,
            }
            for session in self.cort_history
        ]

    # Delegate actual editing to a wrapped coder - for now just return empty
    def get_edits(self, mode="update"):
        """
        Extract edits from the CORT-processed response.

        In the future, this will work with a wrapped coder to extract edits
        from the CORT-processed response using the appropriate edit format.
        """
        # For now, return empty edits since we're working on core CORT functionality
        return []

    def apply_edits(self, edits):
        """
        Apply edits using the wrapped coder's edit format.

        In the future, this will delegate to the wrapped coder for actual
        file editing using the selected edit format.
        """
        # For now, no actual edits are applied
        return

    def __str__(self):
        """String representation showing CORT wrapper status"""
        base_str = f"CortCoder(model={self.main_model.name}, format=wrapper)"
        if self.current_cort_session:
            base_str += f", active_session={self.current_cort_session.session_id}"
        return base_str

    def __repr__(self):
        """Detailed representation for debugging"""
        return (
            f"CortCoder(model={self.main_model.name}, "
            f"sessions={len(self.cort_history)}, "
            f"config={self.cort_config})"
        )
