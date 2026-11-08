import random

from coordinator import graph
from coordinator.model import DAY, Project, horizon

NOW = 1_000_000_000


def test_horizons():
    h = (7, 30, 90)
    assert horizon(NOW - 1 * DAY, NOW, h) == 1
    assert horizon(NOW - 8 * DAY, NOW, h) == 2
    assert horizon(NOW - 31 * DAY, NOW, h) == 3
    assert horizon(NOW - 200 * DAY, NOW, h) == 0
    assert horizon(0, NOW, h) == 0


def P(key, deps=(), ts=0):
    return Project(key=key, path=key, name=key, depends=list(deps), activity_ts=ts)


def test_cycle_collapsed_and_rollup_converges():
    ps = [P("a", ["b"], 5), P("b", ["a"], 9), P("c", ["a"], 1), P("d", ["d"], 2)]
    comps = graph.rollup(ps)
    assert ["a", "b"] in comps and ["d"] in comps
    by = {p.key: p for p in ps}
    assert by["a"].rollup_ts == by["b"].rollup_ts == 9
    assert by["c"].rollup_ts == 9  # joins dependency component
    assert by["d"].rollup_ts == 2  # self-edge dropped


def test_refresh_order_deps_first_self_last():
    ps = [P("coordinator", ["x"]), P("x"), P("y", ["x"])]
    order = graph.refresh_order(["coordinator", "x", "y"], ps, {"coordinator"})
    assert order.index("x") < order.index("y") and order[-1] == "coordinator"


def test_sccs_random_graphs_partition_nodes():
    rnd = random.Random(1)
    for _ in range(50):
        n = rnd.randint(1, 30)
        e = {str(i): {str(rnd.randrange(n)) for _ in range(rnd.randint(0, 4))} for i in range(n)}
        comps = graph.sccs(e)
        flat = [k for c in comps for k in c]
        assert sorted(flat) == sorted(e) and len(flat) == len(set(flat))
