import time

from coordinator.model import Project
from coordinator.store import Store, effective


def test_note_overrides_only_while_newer_than_docs(tmp_path):
    st = Store(tmp_path / "db")
    p = Project(key="a/b", path="/x", name="b", signal_ts=100, status="old", gaps=["no-next-step"])
    st.put(p); st.commit()
    st.add_note("a/b", "why", status="new", next_step="run it")
    note = st.latest_note("a/b")
    q = effective(p, note)
    assert q.status == "new" and q.next_step == "run it" and q.gaps == []
    p.signal_ts = int(time.time()) + 100  # docs updated after the note -> docs win
    assert effective(p, note).status == "old"


def test_resolve_ambiguous(tmp_path):
    import pytest
    st = Store(tmp_path / "db")
    st.put(Project(key="x/app", path="1", name="app")); st.put(Project(key="y/app", path="2", name="app"))
    assert st.resolve("x/app").path == "1"
    with pytest.raises(LookupError):
        st.resolve("app")
