"""复现 microsoft/semantic-kernel#14582:
PromptTemplateConfig.add_execution_settings(overwrite=False) 仍覆盖 default 条目,
且警告日志在错误位置(每次成功 add 都打, 真正拒绝时反而不打)。
"""
import logging

logging.basicConfig(level=logging.WARNING, format="LOG:%(levelname)s:%(message)s")

from semantic_kernel.prompt_template import PromptTemplateConfig  # noqa: E402
from semantic_kernel.connectors.ai.prompt_execution_settings import PromptExecutionSettings  # noqa: E402

a = PromptExecutionSettings(extension_data={"temperature": 0.1})
b = PromptExecutionSettings(extension_data={"temperature": 0.9})

print("--- case1: 已有 default, overwrite=False 不应覆盖 ---")
c = PromptTemplateConfig(template="hi", execution_settings=a)
print("before:", c.execution_settings["default"].extension_data)
c.add_execution_settings(b, overwrite=False)
print("after :", c.execution_settings["default"].extension_data)
assert c.execution_settings["default"].extension_data == {"temperature": 0.1}, (
    f"BUG 复现: overwrite=False 却把 default 改成了 "
    f"{c.execution_settings['default'].extension_data}"
)

print("--- case2: 全新 config 首次 add, 不应打印拒绝警告 ---")
d = PromptTemplateConfig(template="hi")
d.add_execution_settings(a, overwrite=False)
print("fresh :", d.execution_settings["default"].extension_data)

print("ALL ASSERTIONS PASSED (行为正确)")
