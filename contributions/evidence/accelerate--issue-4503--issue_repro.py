import tempfile

import torch
from accelerate import Accelerator
from accelerate.utils import set_seed


def make():
    set_seed(0)
    accelerator = Accelerator(cpu=True, gradient_accumulation_steps=3)
    model = torch.nn.Linear(1, 1, bias=False)
    optimizer = torch.optim.SGD(model.parameters(), lr=0.1)
    model, optimizer = accelerator.prepare(model, optimizer)
    return accelerator, model, optimizer


def run(save_at=None):
    accelerator, model, optimizer = make()
    with tempfile.TemporaryDirectory() as d:
        for i, x in enumerate(torch.linspace(0.5, 3.0, 6)):
            if i == save_at:  # save inside the second window, resume with fresh objects
                accelerator.save_state(d)
                accelerator, model, optimizer = make()
                accelerator.load_state(d)
                print("resumed: step", accelerator.step, "grad", model.weight.grad)
            with accelerator.accumulate(model):
                accelerator.backward(model(x.view(1, 1)).pow(2).sum())
                optimizer.step()
                optimizer.zero_grad()
    return model.weight.item()


print("uninterrupted:", run())
print("resumed after 4 of 6 micro-batches:", run(save_at=4))
