"""Reviewer case 1 for accelerate#4504: DDP resume with mid-window gradients.

Two CPU ranks, gradient_accumulation_steps=3, same six micro-batches on both
ranks, checkpoint saved after 4 and resumed with fresh objects. Each rank
must keep its own partial gradients: a single main-process gradients file
restored onto every rank makes the final weights diverge.

Usage: python ddp_repro.py <rank> <uninterrupted|resume>
"""
import os
import sys
import tempfile

os.environ["MASTER_ADDR"] = "127.0.0.1"
os.environ["MASTER_PORT"] = "29533"
os.environ["RANK"] = sys.argv[1]
os.environ["WORLD_SIZE"] = "2"
os.environ["LOCAL_RANK"] = sys.argv[1]

import torch
import torch.distributed as dist
import datetime

def mark(msg):
    print(f"[rank {rank}] {msg}", flush=True)

from accelerate import Accelerator
from accelerate.utils import set_seed

rank = int(sys.argv[1])
mode = sys.argv[2]
init_file = sys.argv[3]
ckpt_dir = sys.argv[4]

# File-based rendezvous: TCPStore on Windows chokes on non-ASCII machine
# hostnames, and a file store exercises the same per-rank gradient files.
dist.init_process_group(
    backend="gloo",
    init_method=f"file://{init_file}",
    world_size=2,
    rank=rank,
)


def make():
    set_seed(0)
    accelerator = Accelerator(cpu=True, gradient_accumulation_steps=3)
    model = torch.nn.Linear(1, 1, bias=False)
    optimizer = torch.optim.SGD(model.parameters(), lr=0.1)
    model, optimizer = accelerator.prepare(model, optimizer)
    return accelerator, model, optimizer


# Sharded per rank (as a distributed DataLoader would): mid-window ranks
# hold DIFFERENT local gradients, which is what breaks a single
# main-process gradients file.
data = torch.linspace(0.5, 6.0, 12)[rank::2]

if mode == "uninterrupted":
    accelerator, model, optimizer = make()
    for x in data:
        with accelerator.accumulate(model):
            accelerator.backward(model(x.view(1, 1)).pow(2).sum())
            optimizer.step()
            optimizer.zero_grad()
    weight = accelerator.unwrap_model(model).weight.item()
else:
    accelerator, model, optimizer = make()
    mark("prepared")
    d = ckpt_dir
    for i, x in enumerate(data):
        if i == 4:
            mark("saving")
            accelerator.save_state(d)  # every rank saves its own gradients
            mark("saved; entering barrier")
            dist.barrier()  # all rank files exist before any rank loads
            mark("barrier passed")
            accelerator, model, optimizer = make()
            mark("remade")
            accelerator.load_state(d)
            mark("loaded")
        with accelerator.accumulate(model):
            accelerator.backward(model(x.view(1, 1)).pow(2).sum())
            optimizer.step()
            optimizer.zero_grad()
    weight = accelerator.unwrap_model(model).weight.item()

weights = [None] * 2
dist.all_gather_object(weights, weight)
if rank == 0:
    print(f"{mode}: rank weights = {weights}")
    print(f"{mode}: {'MATCH' if ws[0] == ws[1] else 'MISMATCH'} across ranks".replace("ws[0]", str(weights[0])).replace("ws[1]", str(weights[1])))
