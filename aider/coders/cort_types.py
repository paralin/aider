#!/usr/bin/env python

"""
CORT (Chain of Recursive Thought) Type Definitions

This module defines all data structures and types used by the CORT system.
These types support the foundational architecture for extracting CORT
functionality from the monolithic base_coder.py implementation.

Architecture Overview:
- CortState: Manages the state of a CORT thinking session
- CortMessage: Internal message representation for CORT conversations
- CortThinkingRound: Tracks individual thinking iterations
- CortEvaluationResult: Results from response evaluation
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
import time


class CortMessageType(Enum):
    """Types of messages in CORT processing"""

    INITIAL = "initial"
    ALTERNATIVE = "alternative"
    EVALUATION = "evaluation"
    FINAL = "final"


class CortRoundStatus(Enum):
    """Status of a thinking round"""

    PENDING = "pending"
    GENERATING = "generating"
    EVALUATING = "evaluating"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class CortMessage:
    """
    Internal CORT message representation.

    This tracks messages within CORT's thinking process, separate from
    Aider's main conversation history. Used for organizing and tracking
    the iterative thinking process.
    """

    role: str
    content: str
    round_number: int
    message_type: CortMessageType
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Ensure message_type is properly converted to enum"""
        if isinstance(self.message_type, str):
            self.message_type = CortMessageType(self.message_type)


@dataclass
class CortThinkingRound:
    """
    Tracks a single thinking iteration in CORT processing.

    Each round consists of:
    1. Generation of alternative responses
    2. Evaluation to select the best response
    3. Tracking of the decision reasoning
    """

    round_number: int
    alternatives: List[str] = field(default_factory=list)
    selected_response: str = ""
    evaluation_reason: str = ""
    status: CortRoundStatus = CortRoundStatus.PENDING
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    api_calls_made: int = 0
    tokens_used: int = 0

    def mark_completed(self, selected: str, reason: str):
        """Mark this round as completed with final selection"""
        self.selected_response = selected
        self.evaluation_reason = reason
        self.status = CortRoundStatus.COMPLETED
        self.end_time = time.time()

    def mark_failed(self, reason: str):
        """Mark this round as failed"""
        self.evaluation_reason = f"Failed: {reason}"
        self.status = CortRoundStatus.FAILED
        self.end_time = time.time()

    @property
    def duration(self) -> Optional[float]:
        """Get the duration of this round in seconds"""
        if self.end_time is not None:
            return self.end_time - self.start_time
        return None


@dataclass
class CortEvaluationResult:
    """
    Result of evaluating multiple response alternatives.

    Contains the decision made by CORT about which response is best,
    along with the reasoning for that decision.
    """

    selected_response: str
    selected_index: int  # Index in the alternatives list
    evaluation_reasoning: str
    confidence_score: Optional[float] = None
    alternatives_considered: List[str] = field(default_factory=list)
    evaluation_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CortState:
    """
    Manages the complete state of a CORT thinking session.

    This is the central state object that tracks the entire CORT process
    from initial prompt through all thinking rounds to final response.
    Designed to be serializable for debugging and state persistence.
    """

    # Core session data
    original_prompt: str
    thinking_rounds_planned: int
    current_round: int = 0
    current_best_response: str = ""

    # History tracking
    rounds_history: List[CortThinkingRound] = field(default_factory=list)
    messages_history: List[CortMessage] = field(default_factory=list)

    # Session metadata
    session_id: str = field(default_factory=lambda: f"cort_{int(time.time())}")
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None

    # Statistics
    total_api_calls: int = 0
    total_tokens_used: int = 0
    total_alternatives_generated: int = 0

    def add_round(self, round_obj: CortThinkingRound):
        """Add a completed thinking round to history"""
        self.rounds_history.append(round_obj)
        self.current_round = len(self.rounds_history)
        self.total_api_calls += round_obj.api_calls_made
        self.total_tokens_used += round_obj.tokens_used
        self.total_alternatives_generated += len(round_obj.alternatives)

    def add_message(self, message: CortMessage):
        """Add a message to the internal CORT conversation history"""
        self.messages_history.append(message)

    def update_best_response(self, response: str):
        """Update the current best response"""
        self.current_best_response = response

    def is_complete(self) -> bool:
        """Check if CORT processing is complete"""
        return (
            self.current_round >= self.thinking_rounds_planned
            and self.end_time is not None
        )

    def mark_complete(self):
        """Mark the CORT session as complete"""
        self.end_time = time.time()

    @property
    def total_duration(self) -> Optional[float]:
        """Get total session duration in seconds"""
        if self.end_time is not None:
            return self.end_time - self.start_time
        return None

    @property
    def success_rate(self) -> float:
        """Get the success rate of thinking rounds"""
        if not self.rounds_history:
            return 0.0
        successful = sum(
            1 for r in self.rounds_history if r.status == CortRoundStatus.COMPLETED
        )
        return successful / len(self.rounds_history)


@dataclass
class CortConfig:
    """
    Configuration settings for CORT behavior.

    These settings control how CORT operates and can be customized
    without affecting the core Aider functionality.
    """

    # Thinking behavior
    max_thinking_rounds: int = 5
    min_thinking_rounds: int = 1
    num_alternatives_per_round: int = 2

    # API settings
    evaluation_temperature: float = 0.2
    generation_temperature: float = 0.7
    thinking_determination_temperature: float = 0.3

    # Integration settings
    respect_aider_settings: bool = True
    preserve_iterations: bool = True
    fallback_on_error: bool = True

    # Performance settings
    max_api_calls_per_session: int = 50
    timeout_per_round_seconds: float = 300.0

    def validate(self) -> List[str]:
        """Validate configuration settings and return any errors"""
        errors = []

        if self.max_thinking_rounds < self.min_thinking_rounds:
            errors.append("max_thinking_rounds must be >= min_thinking_rounds")

        if self.num_alternatives_per_round < 1:
            errors.append("num_alternatives_per_round must be >= 1")

        if not (0.0 <= self.evaluation_temperature <= 2.0):
            errors.append("evaluation_temperature must be between 0.0 and 2.0")

        if not (0.0 <= self.generation_temperature <= 2.0):
            errors.append("generation_temperature must be between 0.0 and 2.0")

        return errors


# Type aliases for common CORT data structures
CortHistory = List[CortThinkingRound]
CortConversation = List[CortMessage]
CortAlternatives = List[str]

# Default configuration instance
DEFAULT_CORT_CONFIG = CortConfig()
