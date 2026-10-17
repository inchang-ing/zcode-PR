## Summary

`add_noise()` called **before** `set_timesteps()` resolved the noise level from the
wrong timestep. `self.timesteps` is the full descending schedule (`[999, …, 0]`)
while `self.sigmas` is indexed by timestep *value*, so looking the sigma up via
`index_for_timestep(t)` returned `sigmas[999 - t]` instead of `sigmas[t]`.

Concretely, at `t = 200` `DPMSolverMultistepScheduler` produced `a = 0.0391`
(= the value DDPM gives at `t = 799`) instead of the correct `a ≈ 0.8102`. With
`use_flow_sigmas=True` (SanaPipeline) the result was even further off
(`-24.5 * x0 + 25.5 * eps` instead of `0.8 * x0 + 0.2 * eps`).

Fine-tune / probe scripts and SanaPipeline call `add_noise` before
`set_timesteps()`; this is the supported call order introduced by #5981 / #6006,
so the scheduler must handle it.

## Fix

In `add_noise`, when `set_timesteps()` has not run yet (`self.num_inference_steps
is None`), look the sigma up by timestep value directly:

- VP / exponential / beta schedules: `self.sigmas[timesteps]`
- flow schedules: `timesteps / num_train_timesteps` (linear flow sigma)

The post-`set_timesteps()` path (which uses `index_for_timestep` on the aligned
schedule) is unchanged.

## Verification

Added `tests/schedulers/test_scheduler_add_noise_pretimesteps.py`:
- the four affected schedulers (`DPMSolverMultistep`, `DPMSolverSinglestep`,
  `UniPCMultistep`, `DEISMultistep`) now match `DDPMScheduler.add_noise` on the
  pre-`set_timesteps` call order (max abs error < 1e-4);
- with `use_flow_sigmas=True` they produce the expected linear flow noise
  `(1 - t/N) * x0 + (t/N) * eps`;
- `add_noise` still works after `set_timesteps()`.

Fixes #15021
