"""Review repro for run-llama/llama_index#23971 (workflow validation).

`Direct` reaches the join from StartEvent; `Recovered` reaches it only
through a @catch_error handler delivering StepFailedEvent. Validation
must accept both.
"""
import asyncio

from workflows import Context, Workflow, catch_error, step
from workflows.events import Event, StartEvent, StepFailedEvent, StopEvent


class Fork(Event):
    pass


class Left(Event):
    pass


class Right(Event):
    pass


class LeftDone(Event):
    value: int


class RightDone(Event):
    value: int


class Joined(Workflow):
    @step
    async def fork(self, ctx: Context, ev: Fork) -> Left | Right | None:
        ctx.send_event(Left())
        ctx.send_event(Right())
        return None

    @step
    async def left(self, ev: Left) -> LeftDone:
        return LeftDone(value=1)

    @step
    async def right(self, ev: Right) -> RightDone:
        return RightDone(value=2)

    @step
    async def join(self, first: LeftDone, second: RightDone) -> StopEvent:
        return StopEvent(result=first.value + second.value)


class Direct(Joined):
    @step
    async def begin(self, ev: StartEvent) -> Fork:
        return Fork()


class Recovered(Joined):
    @step
    async def begin(self, ev: StartEvent) -> StopEvent:
        raise RuntimeError("fails")  # Only the handler below produces Fork.

    @catch_error(for_steps=["begin"])
    async def recover(self, ev: StepFailedEvent) -> Fork:
        return Fork()


async def main():
    outcomes = {}
    for workflow in (Direct, Recovered):
        for validation in (True, False):
            try:
                result = await workflow(timeout=10, disable_validation=not validation).run()
                outcomes[(workflow.__name__, validation)] = result
                print(f"{workflow.__name__:9s} validation={validation!s:5s} -> result {result}")
            except Exception as e:
                outcomes[(workflow.__name__, validation)] = f"{type(e).__name__}: {e}"
                print(f"{workflow.__name__:9s} validation={validation!s:5s} -> {type(e).__name__}: {str(e)[:90]}")

    ok = (
        isinstance(outcomes[("Direct", True)], int)
        and isinstance(outcomes[("Direct", False)], int)
        and isinstance(outcomes[("Recovered", True)], int)
        and isinstance(outcomes[("Recovered", False)], int)
    )
    print("VERDICT:", "ALL_FOUR_RUN" if ok else "VALIDATION_REJECTS_RECOVERED")


asyncio.run(main())
