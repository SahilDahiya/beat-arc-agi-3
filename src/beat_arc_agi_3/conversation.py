import os
from dataclasses import replace
from pathlib import Path
from typing import Sequence

from pydantic import ValidationError
from pydantic_ai import ModelMessage, ModelMessagesTypeAdapter, ModelRequest


class ConversationError(RuntimeError):
    """Base error for persisted model conversation state."""


class ConversationCorruptionError(ConversationError):
    """Raised when persisted model messages cannot be validated."""


class ConversationNotFoundError(ConversationError):
    """Raised when a conversation file has not been created."""


class JsonlConversation:
    """Append-only Pydantic AI message batches for one Session."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        if not self.path.exists():
            raise ConversationNotFoundError(
                f"conversation does not exist: {self.path}"
            )
        if not self.path.is_file():
            raise ConversationError(
                f"conversation path is not a file: {self.path}"
            )
        self._messages = self._load()

    @classmethod
    def create(cls, path: str | Path) -> "JsonlConversation":
        conversation_path = Path(path)
        conversation_path.parent.mkdir(parents=True, exist_ok=True)
        with conversation_path.open("x", encoding="utf-8") as handle:
            handle.flush()
            os.fsync(handle.fileno())
        return cls(conversation_path)

    def messages(self) -> tuple[ModelMessage, ...]:
        return tuple(self._messages)

    def context_messages(self) -> tuple[ModelMessage, ...]:
        """Project durable messages into the provider-bound context."""

        return tuple(self._messages)

    def append(self, messages: Sequence[ModelMessage]) -> None:
        batch = self._deduplicate_instructions(messages)
        if not batch:
            raise ValueError("conversation message batch cannot be empty")
        payload = ModelMessagesTypeAdapter.dump_json(batch).decode("utf-8")
        try:
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(f"{payload}\n")
                handle.flush()
                os.fsync(handle.fileno())
        except FileNotFoundError as exc:
            raise ConversationNotFoundError(
                f"conversation does not exist: {self.path}"
            ) from exc
        self._messages.extend(batch)

    def _deduplicate_instructions(
        self, messages: Sequence[ModelMessage]
    ) -> list[ModelMessage]:
        seen = {
            message.instructions
            for message in self._messages
            if isinstance(message, ModelRequest) and message.instructions is not None
        }
        deduplicated: list[ModelMessage] = []
        for message in messages:
            if not isinstance(message, ModelRequest) or message.instructions is None:
                deduplicated.append(message)
                continue
            if message.instructions in seen:
                deduplicated.append(replace(message, instructions=None))
                continue
            seen.add(message.instructions)
            deduplicated.append(message)
        return deduplicated

    def _load(self) -> list[ModelMessage]:
        messages: list[ModelMessage] = []
        try:
            handle = self.path.open("r", encoding="utf-8")
        except FileNotFoundError as exc:
            raise ConversationNotFoundError(
                f"conversation does not exist: {self.path}"
            ) from exc

        with handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    raise ConversationCorruptionError(
                        f"conversation line {line_number} is empty"
                    )
                try:
                    batch = ModelMessagesTypeAdapter.validate_json(line)
                except (ValidationError, ValueError) as exc:
                    raise ConversationCorruptionError(
                        f"invalid conversation batch on line {line_number}: {exc}"
                    ) from exc
                if not batch:
                    raise ConversationCorruptionError(
                        f"conversation batch on line {line_number} is empty"
                    )
                messages.extend(batch)
        return messages
