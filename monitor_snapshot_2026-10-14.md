# PR 监控快照 — 2026-10-14 10:18 UTC

- 在飞总数: **66**（OSS 上游 45 / 个人 fork 21）
- 范围: GitHub `author=inchang-ing is:open`（权威源）
- 说明: 监控为手动触发（无 automation）；本快照即基线，下次手动跑对比 diff。


## BLOCKED (19)

- #2736 `567-labs/instructor` · review=REVIEW_REQUIRED · upd=2026-10-10 · fix: replace deprecated gpt-3.5-turbo defaults
- #2717 `567-labs/instructor` · review=REVIEW_REQUIRED · upd=2026-10-11 · fix(gemini): do not mutate caller-owned messag
- #3998 `Arize-ai/openinference` · review=REVIEW_REQUIRED · upd=2026-10-11 · fix(agno): don't resolve an async tools factor
- #46262 `BerriAI/litellm` · review=REVIEW_REQUIRED · upd=2026-10-14 · fix(streaming_handler): coerce list delta cont
- #20883 `DataDog/dd-trace-py` · review=REVIEW_REQUIRED · upd=2026-10-10 · Fix #20783: include tool_use_prompt_token_coun
- #20877 `DataDog/dd-trace-py` · review=REVIEW_REQUIRED · upd=2026-10-09 · Fix #20858: reset ASGI ExecutionContext betwee
- #20873 `DataDog/dd-trace-py` · review=REVIEW_REQUIRED · upd=2026-10-10 · Fix #20782: map Anthropic 1h cache creation to
- #20769 `DataDog/dd-trace-py` · review=REVIEW_REQUIRED · upd=2026-10-10 · fix(vllm): guard num_cached_tokens access for 
- #682 `OpenBMB/ChatDev` · review=REVIEW_REQUIRED · upd=2026-09-29 · fix(utils): register dynamic tool modules in s
- #14017 `aio-libs/aiohttp` · review=- · upd=2026-10-12 · Fix RequestHandler crash after connection_lost
- #2826 `deepchecks/deepchecks` · review=REVIEW_REQUIRED · upd=2026-10-13 · Fix single dataset performance conditions for 
- #443 `executablebooks/markdown-it-py` · review=- · upd=2026-10-10 · fix(parser): fail fast on rules that don't adv
- #442 `executablebooks/markdown-it-py` · review=- · upd=2026-10-10 · fix(block): HTML block start outside a list it
- #682 `mala-project/mala` · review=- · upd=2026-10-09 · Return a scalar float from Density.get_number_
- #14586 `microsoft/semantic-kernel` · review=REVIEW_REQUIRED · upd=2026-10-13 · Python: FIX: honor overwrite=False for default
- #29928 `pola-rs/polars` · review=REVIEW_REQUIRED · upd=2026-10-14 · fix: allow `scan_delta` filter on struct colum
- #3050 `snowflakedb/snowflake-connector-python` · review=REVIEW_REQUIRED · upd=2026-10-08 · Fix #3049: apply force_microsecond_precision t
- #3046 `snowflakedb/snowflake-connector-python` · review=REVIEW_REQUIRED · upd=2026-10-10 · fix: honor external_browser_timeout in the ext
- #967 `yaml/pyyaml` · review=- · upd=2026-10-10 · Quote leading-zero digit strings when dumping

## UNSTABLE (10)

- #1546 `bottlepy/bottle` · review=- · upd=2026-10-12 · Fix mounted apps using the parent's error hand
- #12636 `dask/dask` · review=- · upd=2026-10-14 · fix(array): widen shuffle taker dtype to cover
- #3543 `hydra-ecosystem/hydra` · review=- · upd=2026-10-14 · Handle missing Structured Config root when app
- 【个人】#161 `inchang-ing/code-security-workbench` · review=- · upd=2026-10-07 · D6-25：公网 HTTPS 评审入口与实际代理边界验证
- 【个人】#153 `inchang-ing/code-security-workbench` · review=- · upd=2026-10-07 · D6-11：SQL/YAML 真实资格基线与未完成网页验收
- #2332 `jupyter/nbconvert` · review=- · upd=2026-10-13 · Preserve safe subdirectories in extracted outp
- #578 `mahmoud/boltons` · review=- · upd=2026-10-12 · Fix urlutils parsing of unencoded ? and / in U
- #5349 `pypa/setuptools` · review=- · upd=2026-10-12 · Restore hashability of Extension via eq=False 
- #5337 `pypa/setuptools` · review=- · upd=2026-10-10 · Extract tar members through the tarfile data f
- #2180 `weaviate/weaviate-python-client` · review=- · upd=2026-10-10 · fix(batch): filter re-added errors by uuid and

## DIRTY (1)

- #2385 `pydicom/pydicom` · review=APPROVED · upd=2026-10-10 · fix(charset): handle ISO 2022 IR 58 (GB2312) e

## UNKNOWN (12)

- #3995 `Arize-ai/openinference` · review=REVIEW_REQUIRED · upd=2026-10-12 · fix(google-genai): record tuple-valued content
- #3982 `Arize-ai/openinference` · review=REVIEW_REQUIRED · upd=2026-10-11 · Fix #3904: do not record the SDK placeholder t
- #3981 `Arize-ai/openinference` · review=REVIEW_REQUIRED · upd=2026-10-08 · Fix #3803: record attributes for tuple-valued 
- #20935 `DataDog/dd-trace-py` · review=- · upd=2026-10-12 · fix(tracing): keep dd= member within W3C 256-c
- #20886 `DataDog/dd-trace-py` · review=APPROVED · upd=2026-10-08 · fix(bootstrap): keep logging.captureWarnings w
- #7795 `crewAIInc/crewAI` · review=REVIEW_REQUIRED · upd=2026-10-10 · fix(openai): allow multimodal file inputs for 
- #4439 `docling-project/docling` · review=- · upd=2026-10-14 · fix(xb): don't dereference memberQname on type
- #15023 `huggingface/diffusers` · review=REVIEW_REQUIRED · upd=2026-10-14 · fix(schedulers): use timestep-indexed sigma in
- #3187 `repowise-dev/repowise` · review=REVIEW_REQUIRED · upd=2026-10-11 · fix(doc_drift): treat agent/editor config path
- #10472 `statsmodels/statsmodels` · review=- · upd=2026-10-08 · Fix #9237: index 0-d array as a scalar
- #3791 `tornadoweb/tornado` · review=- · upd=2026-10-12 · Fix Subprocess.wait_for_exit hanging when chil
- #2307 `tortoise/tortoise-orm` · review=REVIEW_REQUIRED · upd=2026-10-13 · fix(migrations): scope leaf/root nodes to same

## 需关注

- #1546 `bottlepy/bottle`: CI 未全绿
- #12636 `dask/dask`: CI 未全绿
- #3543 `hydra-ecosystem/hydra`: CI 未全绿
- #161 `inchang-ing/code-security-workbench`: CI 未全绿
- #153 `inchang-ing/code-security-workbench`: CI 未全绿
- #2332 `jupyter/nbconvert`: CI 未全绿
- #578 `mahmoud/boltons`: CI 未全绿
- #5349 `pypa/setuptools`: CI 未全绿
- #5337 `pypa/setuptools`: CI 未全绿
- #2180 `weaviate/weaviate-python-client`: CI 未全绿