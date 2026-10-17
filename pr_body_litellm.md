## TLDR

Problem this solves:

- Some OpenAI-compatible backends stream `delta.content` as a list of content parts instead of a string
- Accumulating that into the wrapper's running text raised `TypeError: can only concatenate str (not "list") to str`
- Every chunk after the first was dropped as empty, because the empty-chunk check only accepts a non-empty string

How it solves it:

- `_delta_content_as_str` joins the text parts of a content-part list into one string
- The openai/azure chunk handler reads delta content through it, so the chunk is no longer treated as empty
- The three places that append delta content to the running text go through it too

## User Flow

Before: a developer streaming a chat completion from a Mistral deployment on Azure AI Foundry loses the response after a tool result

1. They send POST https://litellm-domain/v1/chat/completions with `"stream": true`, one tool, and a tool result message
2. The first chunk arrives with text, then the stream dies with `APIConnectionError: can only concatenate str (not "list") to str`
3. Where the crash does not fire, only the first chunk reaches them and the rest of the answer is dropped

After: the same request streams the full answer

1. They send the same POST https://litellm-domain/v1/chat/completions with `"stream": true`, one tool, and a tool result message
2. Every chunk arrives with its text part joined into a plain string
3. They receive the complete answer, and the logged and aggregated text matches what they saw

## Relevant issues

Fixes #46209

## Pre-Submission checklist

- [ ] I have added meaningful tests
- [ ] The handful of test files covering my change pass locally, e.g. `uv run pytest tests/unit/<your_test_file>.py -v`
- [ ] My PR passes all required CI/CD checks (e.g., lint, schema.d.ts sync check, etc.)
- [x] My PR's scope is as isolated as possible; it only solves 1 specific problem
- [ ] Every automated review on my PR's latest commit has finished

## Screenshots / Proof of Fix

No live provider credentials here, so the proof is the regression test mutated and restored, one case, streaming two chunks whose delta content is a content-part list

### Before (fb051f9647)

1. Run `pytest tests/unit/litellm_core_utils/test_streaming_handler.py -k delta_content_list`
2. It fails with `TypeError: can only concatenate str (not "list") to str`, the same error as the issue

### After (040bddaf32adc2d59d59e5f76966bc0d2c77a9b2)

1. Run `pytest tests/unit/litellm_core_utils/test_streaming_handler.py -k delta_content_list`
2. It passes, and the wrapper's running text is `hello world`, so both chunks survived

## Type

🐛 Bug Fix
