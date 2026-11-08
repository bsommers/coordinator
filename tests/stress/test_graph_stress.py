import random
import time

from coordinator import graph


def test_large_cyclic_graph_no_recursion_error():
    n = 20000
    e = {str(i): {str((i + 1) % n)} for i in range(n)}  # one giant cycle, deep chain
    t = time.time()
    comps = graph.sccs(e)
    assert len(comps) == 1 and len(comps[0]) == n and time.time() - t < 5
