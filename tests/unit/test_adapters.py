from coordinator import adapters as A
from conftest import CHECKPOINT


def test_status_line_variants():
    assert A.status_line("**Status:** DONE x") == "DONE x"
    assert A.status_line("Status: ok") == "ok"
    assert A.status_line("**Status**: fine") == "fine"
    assert A.status_line("nothing") == ""


def test_next_step_and_boxes():
    assert A.next_step(CHECKPOINT) == "`pytest -q`"
    assert A.checkboxes("- [x] a\n- [ ] b\n* [X] c") == (2, 3)


def test_frontmatter_nested():
    fm = A.frontmatter("---\nstatus: ok\nprogress:\n  completed_plans: 3\n---\nbody")
    assert fm["status"] == "ok" and fm["progress.completed_plans"] == "3"


def test_gsd_and_checkpoint(make_repo):
    p = make_repo("a", {".planning/STATE.md": "---\nstatus: executing\ncurrent_phase: 02\n"
                        "current_phase_name: Core\nprogress:\n  total_plans: 4\n  completed_plans: 1\n---\n",
                        "docs/CHECKPOINT.md": CHECKPOINT})
    kinds = {f.framework: f for f in A.detect(p)}
    assert kinds["gsd"].status == "executing" and (kinds["gsd"].done, kinds["gsd"].total) == (1, 4)
    assert kinds["gsd"].phase == "02 Core"
    assert kinds["checkpoint"].next_step == "`pytest -q`"


def test_speckit_openspec_superpowers_kiro(make_repo):
    p = make_repo("b", {"specs/001-x/tasks.md": "- [x] a\n- [ ] b\n", ".specify/memory/constitution.md": "c",
                        "openspec/changes/add-y/tasks.md": "- [ ] z\n",
                        "docs/superpowers/plans/p.md": "- [x] one\n",
                        ".kiro/specs/s/tasks.md": "- [ ] k\n"})
    got = {f.framework: (f.done, f.total) for f in A.detect(p)}
    assert got["spec-kit"] == (1, 2) and got["openspec"] == (0, 1)
    assert got["superpowers"] == (1, 1) and got["kiro"] == (0, 1)


def test_no_frameworks(make_repo):
    assert A.detect(make_repo("c")) == []


def test_numbered_next_steps_heading():
    assert A.next_step("## 6. Next Steps (Exact Commands In Order)\n1. Verify: `git status`\n") == "Verify: `git status`"
