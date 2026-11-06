
from openai.types.chat import ChatCompletionMessage

from llama_index.core.base.llms.types import ChatMessage, ChatResponse
from llama_index.core.callbacks import TokenCountingHandler
from llama_index.core.callbacks.schema import CBEventType, EventPayload
from llama_index.llms.openai.utils import from_openai_message


def completion_tokens(message):
    # No usage in the response (e.g. a provider that does not report it): the handler estimates.
    handler = TokenCountingHandler()
    handler.on_event_end(CBEventType.LLM, payload={
        EventPayload.MESSAGES: [ChatMessage(role="user", content="Weather in Paris?")],
        EventPayload.RESPONSE: ChatResponse(message=message),
    })
    event = handler.llm_token_counts[0]
    return event.completion, event.completion_token_count


arguments = '{"city": "Paris", "unit": "celsius", "days": 3, "include": ["humidity", "wind", "uv_index"]}'
tool_call = ChatCompletionMessage(role="assistant", content=None, tool_calls=[{
    "id": "call_1", "type": "function", "function": {"name": "get_weather_forecast", "arguments": arguments}}])
print("tool-call reply:", completion_tokens(from_openai_message(tool_call, modalities=["text"])))
print("empty reply:    ", completion_tokens(ChatMessage(role="assistant", content=None)))
text, count = completion_tokens(from_openai_message(tool_call, modalities=["text"]))
assert "get_weather_forecast" in text, "the generated tool name and arguments are not counted as completion tokens"
