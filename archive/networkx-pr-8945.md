## Reference Issues
Fixes #8945

## Description
`weisfeiler_lehman_graph_hash` / `weisfeiler_lehman_subgraph_hashes` silently
collided directed graphs that differ only by edge direction when an
`edge_attr` was supplied.

Root cause: in `_neighborhood_aggregate_directed` the directionality prefix was
built with an operator-precedence bug:

```python
prefix = "s_" + "" if edge_attr is None else str(G[node][nbr][edge_attr])
```

This parses as `("s_" + "") if edge_attr is None else str(...)`, so whenever
`edge_attr` was supplied the `"s_"`/`"p_"` prefix was dropped entirely, erasing
directionality. An outward star `DiGraph([(0,1),(0,2)])` and an inward star
`DiGraph([(1,0),(2,0)])` with identical edge labels therefore hashed to the same
value.

Fix: parenthesize the conditional so the prefix is always `"s_"`/`"p_"` followed
by the edge-attribute value (or empty when `edge_attr is None`):

```python
prefix = "s_" + ("" if edge_attr is None else str(G[node][nbr][edge_attr]))
```

I verified the fix with the issue reproducer (outward vs inward star now differ)
and confirmed isomorphic/relabeled directed graphs still hash identically. Added
`test_directed_edge_attr_direction_preserved` regression test; the full
`test_graph_hashing.py` suite passes (30 passed).

## AI tool disclosure
I used an AI coding assistant to help draft this change. I reviewed, understood,
and tested it myself: I reproduced the bug, confirmed the fix flips the behavior,
and ran the regression suite. No AI-generated text is pasted blindly; all changes
are my own and verified.

## Checklist
- [x] Tests added / pass
- [x] Code follows networkx style (black)
