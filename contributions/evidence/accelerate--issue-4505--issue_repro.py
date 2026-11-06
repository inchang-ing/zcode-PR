import torch
from torch.utils.data import BatchSampler, DataLoader
from accelerate.data_loader import prepare_data_loader

class StoredBatchSampler(BatchSampler):
    def __init__(self, n):
        super().__init__(range(n), 4, False)
        self.batches = list(super().__iter__())

    def __iter__(self):
        return iter(self.batches)

sampler = StoredBatchSampler(2)
raw = DataLoader(torch.arange(2), batch_sampler=sampler)
prepared = prepare_data_loader(
    raw, device=torch.device("cpu"), num_processes=2,
    process_index=0, split_batches=True, even_batches=True,
)
print([b.tolist() for b in prepared])  # [[0, 1]]
print([b.tolist() for b in raw])       # [[0, 1, 0, 1]]; expected [[0, 1]]
