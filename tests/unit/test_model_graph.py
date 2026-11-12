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


def test_graph_markdown_mermaid_and_cycles():
    from coordinator import view
    ps = [P('we"ird<a>', ["b"]), P("b", ["we\"ird<a>"]), P("c", ["b"]), P("solo")]
    comps = graph.rollup(ps)
    md = view.graph_markdown([p.key for p in ps], graph.build_edges(ps), comps)
    assert "```mermaid" in md and "flowchart LR" in md
    assert '["we\'ird&lt;a&gt;"]' in md          # label escaped; node ids synthetic (n0..)
    assert "classDef cyc" in md and "## Cycles (collapsed)" in md
    assert "solo" in md.split("## No dependencies")[1]


def test_graph_markdown_empty():
    from coordinator import view
    md = view.graph_markdown(["a"], {"a": set()}, [["a"]])
    assert "No dependencies found" in md and 'subgraph iso' in md


def test_infer_edges_from_manifests(tmp_path):
    for n in ("app", "lib", "web", "rs", "gm"):
        (tmp_path / n).mkdir()
    (tmp_path / "lib" / "sub").mkdir()
    (tmp_path / "app" / "pyproject.toml").write_text(
        '[tool.uv.sources]\nlib = { path = "../lib/sub" }\nself = { path = "." }\n')
    (tmp_path / "web" / "package.json").write_text('{"dependencies": {"x": "file:../app", "y": "^1"}}')
    (tmp_path / "rs" / "Cargo.toml").write_text('[dependencies]\nlib = { path = "../lib" }\n')
    (tmp_path / "gm" / "go.mod").write_text("module gm\nreplace a => ../web\n")
    (tmp_path / "lib" / "pyproject.toml").write_text("not [valid toml")
    ps = [Project(key=n, path=str(tmp_path / n), name=n) for n in ("app", "lib", "web", "rs", "gm")]
    e = graph.infer_edges(ps)
    assert e["app"] == {"lib"} and e["web"] == {"app"} and e["rs"] == {"lib"} and e["gm"] == {"web"}
    assert e["lib"] == set()
    merged, only, comps = graph.full_graph(ps)
    assert ("app", "lib") in only and merged["app"] == {"lib"}
