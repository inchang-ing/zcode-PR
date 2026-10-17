"""Regression check for diffusers#15021.

add_noise() called *before* set_timesteps() must use the noise level of the
requested timestep, not of `999 - t`.

VP schedulers must agree with DDPMScheduler; flow_sigmas schedulers must give
the linear flow noise (1 - t/N) * x0 + (t/N) * eps.
"""
import torch

from diffusers import (
    DDPMScheduler,
    DPMSolverMultistepScheduler,
    DPMSolverSinglestepScheduler,
    UniPCMultistepScheduler,
    DEISMultistepScheduler,
)

x0 = torch.ones(3, 4, 8, 8)
noise = torch.randn(3, 4, 8, 8)
t = torch.tensor([200, 500, 800])

ddpm = DDPMScheduler(num_train_timesteps=1000)
n_ddpm = ddpm.add_noise(x0, noise, t)

for Sched in (
    DPMSolverMultistepScheduler,
    DPMSolverSinglestepScheduler,
    UniPCMultistepScheduler,
    DEISMultistepScheduler,
):
    # VP
    sched = Sched(num_train_timesteps=1000)
    n = sched.add_noise(x0, noise, t)
    err = (n - n_ddpm).abs().max().item()
    print(f"{Sched.__name__} VP max err vs DDPM: {err:.2e}")
    assert err < 1e-4, f"{Sched.__name__} VP mismatch (err={err})"

    # flow
    sched_f = Sched(num_train_timesteps=1000, use_flow_sigmas=True)
    n_f = sched_f.add_noise(x0, noise, t)
    expected = (1 - t / 1000.0).view(-1, 1, 1, 1) * x0 + (t / 1000.0).view(-1, 1, 1, 1) * noise
    err_f = (n_f - expected).abs().max().item()
    print(f"{Sched.__name__} flow max err vs expected: {err_f:.2e}")
    assert err_f < 1e-4, f"{Sched.__name__} flow mismatch (err={err_f})"

# set_timesteps() must still work afterwards
sched = DPMSolverMultistepScheduler(num_train_timesteps=1000)
sched.set_timesteps(10)
n_after = sched.add_noise(x0, noise, sched.timesteps[:3])
assert n_after.shape == x0.shape
print("post-set_timesteps add_noise OK, shape", tuple(n_after.shape))

print("ALL PASS")
