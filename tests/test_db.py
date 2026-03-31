"""Tests for ResearchDB — file-based session storage."""

import json
from pathlib import Path

import pytest

from backend.db import ResearchDB, _current_task_id


@pytest.fixture
def db(tmp_path):
    """Create a ResearchDB rooted in a temp directory."""
    d = ResearchDB(base_dir=str(tmp_path))
    d.create_session("test idea")
    return d


class TestSessionCreation:
    def test_creates_directory(self, db, tmp_path):
        sessions = list(tmp_path.iterdir())
        assert len(sessions) == 1
        assert sessions[0].is_dir()

    def test_research_id_contains_slug(self, db):
        assert "test" in db.research_id
        assert "idea" in db.research_id

    def test_tasks_dir_created(self, db, tmp_path):
        session_dir = list(tmp_path.iterdir())[0]
        assert (session_dir / "tasks").is_dir()

    def test_no_session_raises(self, tmp_path):
        d = ResearchDB(base_dir=str(tmp_path))
        with pytest.raises(RuntimeError, match="No active research session"):
            d.save_idea("test")


class TestReadWrite:
    def test_idea_round_trip(self, db):
        db.save_idea("my idea")
        assert db.get_idea() == "my idea"

    def test_refined_idea_round_trip(self, db):
        db.save_refined_idea("refined")
        assert db.get_refined_idea() == "refined"

    def test_calibration_round_trip(self, db):
        db.save_calibration("calibration text")
        assert db.get_calibration() == "calibration text"

    def test_strategy_round_trip(self, db):
        db.save_strategy("strategy text")
        assert db.get_strategy() == "strategy text"

    def test_paper_round_trip(self, db):
        db.save_paper("paper content")
        root = Path(db._base) / db.research_id
        assert (root / "paper.md").read_text() == "paper content"

    def test_task_output_round_trip(self, db):
        db.save_task_output("task_1", "output text")
        assert db.get_task_output("task_1") == "output text"

    def test_plan_round_trip(self, db):
        flat = [{"id": "1", "description": "test", "dependencies": []}]
        tree = {"id": "0", "children": []}
        db.save_plan(flat, tree)
        assert json.loads(db.get_plan_list()) == flat
        assert json.loads(db.get_plan_tree()) == tree

    def test_missing_file_returns_empty(self, db):
        assert db.get_idea() == ""
        assert db.get_refined_idea() == ""
        assert db.get_calibration() == ""
        assert db.get_strategy() == ""
        assert db.get_plan_list() == ""
        assert db.get_task_output("nonexistent") == ""


class TestScoreAndEvaluation:
    def test_score_direction_default_minimize(self, db):
        assert db.get_score_minimize() is True

    def test_score_direction_maximize(self, db):
        db.save_score_direction(minimize=False)
        assert db.get_score_minimize() is False

    def test_iteration_count(self, db):
        assert db.get_iteration() == 0
        db.save_evaluation({"score": 0.5}, iteration=0)
        assert db.get_iteration() == 1
        db.save_evaluation({"score": 0.6}, iteration=1)
        assert db.get_iteration() == 2

    def test_latest_score(self, db):
        assert db.get_latest_score() is None
        db.save_evaluation({"score": 0.8}, iteration=0)
        assert db.get_latest_score() == 0.8
        db.save_evaluation({"score": 0.9}, iteration=1)
        assert db.get_latest_score() == 0.9


class TestArtifacts:
    def test_artifacts_dir_creation(self, db):
        d = db.get_artifacts_dir()
        assert d.is_dir()

    def test_task_artifacts_dir(self, db):
        d = db.get_artifacts_dir("task_1")
        assert d.is_dir()
        assert d.name == "task_1"

    def test_save_script(self, db):
        token = _current_task_id.set("task_1")
        try:
            path, name = db.save_script("print('hello')", "python")
            assert name == "001.py"
            assert path.read_text() == "print('hello')"
            # Second script gets sequential numbering
            path2, name2 = db.save_script("print('world')", "python")
            assert name2 == "002.py"
        finally:
            _current_task_id.reset(token)

    def test_promote_best_score(self, db):
        token = _current_task_id.set("task_1")
        try:
            task_dir = db.get_artifacts_dir("task_1")
            (task_dir / "best_score.json").write_text(json.dumps({"score": 0.9}))
            db.save_score_direction(minimize=False)
            db.promote_best_score()

            artifacts_root = db.get_artifacts_dir()
            best = json.loads((artifacts_root / "best_score.json").read_text())
            assert best["score"] == 0.9
        finally:
            _current_task_id.reset(token)

    def test_promote_best_score_only_when_better(self, db):
        db.save_score_direction(minimize=False)
        artifacts_root = db.get_artifacts_dir()

        # First score: 0.9
        token = _current_task_id.set("t1")
        try:
            t1_dir = db.get_artifacts_dir("t1")
            (t1_dir / "best_score.json").write_text(json.dumps({"score": 0.9}))
            db.promote_best_score()
        finally:
            _current_task_id.reset(token)

        # Second score: 0.7 (worse for maximize)
        token = _current_task_id.set("t2")
        try:
            t2_dir = db.get_artifacts_dir("t2")
            (t2_dir / "best_score.json").write_text(json.dumps({"score": 0.7}))
            db.promote_best_score()
        finally:
            _current_task_id.reset(token)

        # best_score should still be 0.9
        best = json.loads((artifacts_root / "best_score.json").read_text())
        assert best["score"] == 0.9
        # latest_score should be 0.7
        latest = json.loads((artifacts_root / "latest_score.json").read_text())
        assert latest["score"] == 0.7


    def test_promote_best_score_minimize(self, db):
        """When minimize=True, a higher score (worse) should NOT be promoted."""
        db.save_score_direction(minimize=True)
        artifacts_root = db.get_artifacts_dir()

        # First score: 0.5
        token = _current_task_id.set("t1")
        try:
            t1_dir = db.get_artifacts_dir("t1")
            (t1_dir / "best_score.json").write_text(json.dumps({"score": 0.5}))
            db.promote_best_score()
        finally:
            _current_task_id.reset(token)

        # Second score: 0.8 (worse for minimize)
        token = _current_task_id.set("t2")
        try:
            t2_dir = db.get_artifacts_dir("t2")
            (t2_dir / "best_score.json").write_text(json.dumps({"score": 0.8}))
            db.promote_best_score()
        finally:
            _current_task_id.reset(token)

        # best_score should still be 0.5 (lower is better)
        best = json.loads((artifacts_root / "best_score.json").read_text())
        assert best["score"] == 0.5

        # Third score: 0.3 (better for minimize)
        token = _current_task_id.set("t3")
        try:
            t3_dir = db.get_artifacts_dir("t3")
            (t3_dir / "best_score.json").write_text(json.dumps({"score": 0.3}))
            db.promote_best_score()
        finally:
            _current_task_id.reset(token)

        # best_score should now be 0.3
        best = json.loads((artifacts_root / "best_score.json").read_text())
        assert best["score"] == 0.3


class TestClearAndList:
    def test_list_completed_tasks(self, db):
        db.save_task_output("1", "result 1")
        db.save_task_output("2", "result 2")
        tasks = db.list_completed_tasks()
        assert len(tasks) == 2
        ids = {t["id"] for t in tasks}
        assert ids == {"1", "2"}

    def test_clear_tasks(self, db):
        db.save_task_output("1", "result")
        db.clear_tasks()
        assert db.list_completed_tasks() == []

    def test_clear_plan(self, db):
        flat = [{"id": "1", "description": "test", "dependencies": []}]
        tree = {"id": "0", "children": []}
        db.save_plan(flat, tree)
        db.save_evaluation({"score": 0.5}, 0)
        db.clear_plan()
        assert db.get_plan_list() == ""
        assert db.get_plan_tree() == ""
        assert db.get_iteration() == 0


class TestSessionManagement:
    def test_list_sessions_empty(self, tmp_path):
        db = ResearchDB(base_dir=str(tmp_path))
        assert db.list_sessions() == []

    def test_list_sessions(self, tmp_path):
        db = ResearchDB(base_dir=str(tmp_path))
        db.create_session("first idea")
        id1 = db.research_id
        db2 = ResearchDB(base_dir=str(tmp_path))
        db2.create_session("second idea")
        id2 = db2.research_id

        sessions = db.list_sessions()
        assert len(sessions) == 2
        ids = [s["id"] for s in sessions]
        assert id2 in ids
        assert id1 in ids
        # Newest first
        assert ids[0] == id2

    def test_list_sessions_has_status(self, tmp_path):
        db = ResearchDB(base_dir=str(tmp_path))
        db.create_session("status test")
        db.save_idea("status test")
        sessions = db.list_sessions()
        assert sessions[0]["status"] == "created"

        db.save_refined_idea("refined")
        sessions = db.list_sessions()
        assert sessions[0]["status"] == "refining"

        db.save_plan([{"id": "1"}], {"id": "0"})
        sessions = db.list_sessions()
        assert sessions[0]["status"] == "researching"

        db.save_paper("paper content")
        sessions = db.list_sessions()
        assert sessions[0]["status"] == "completed"

    def test_get_session_detail(self, tmp_path):
        db = ResearchDB(base_dir=str(tmp_path))
        db.create_session("detail test")
        db.save_idea("my idea")
        db.save_refined_idea("my refined idea")
        db.save_task_output("t1", "output 1")
        db.save_paper("final paper")

        detail = db.get_session(db.research_id)
        assert detail is not None
        assert detail["idea"] == "my idea"
        assert detail["refined_idea"] == "my refined idea"
        assert detail["paper"] == "final paper"
        assert len(detail["tasks"]) == 1
        assert detail["tasks"][0]["id"] == "t1"

    def test_get_session_not_found(self, tmp_path):
        db = ResearchDB(base_dir=str(tmp_path))
        # Valid format but doesn't exist → None
        assert db.get_session("20200101-000000") is None
        # Invalid format → ValueError
        with pytest.raises(ValueError):
            db.get_session("nonexistent")

    def test_delete_session(self, tmp_path):
        db = ResearchDB(base_dir=str(tmp_path))
        db.create_session("to delete")
        sid = db.research_id
        # Create a new DB instance (simulate different session)
        db2 = ResearchDB(base_dir=str(tmp_path))
        assert db2.delete_session(sid) is True
        assert not (tmp_path / sid).exists()

    def test_delete_active_session_fails(self, tmp_path):
        db = ResearchDB(base_dir=str(tmp_path))
        db.create_session("active")
        assert db.delete_session(db.research_id) is False

    def test_delete_nonexistent_session(self, tmp_path):
        db = ResearchDB(base_dir=str(tmp_path))
        # Valid format but doesn't exist → False
        assert db.delete_session("20200101-000000") is False
        # Invalid format → ValueError
        with pytest.raises(ValueError):
            db.delete_session("nonexistent")

    def test_get_session_with_evaluations(self, tmp_path):
        db = ResearchDB(base_dir=str(tmp_path))
        db.create_session("eval test")
        db.save_evaluation({"score": 0.5, "notes": "v0"}, 0)
        db.save_evaluation({"score": 0.7, "notes": "v1"}, 1)

        detail = db.get_session(db.research_id)
        assert "evaluations" in detail
        assert len(detail["evaluations"]) == 2
        assert detail["evaluations"][0]["score"] == 0.5


class TestSlugify:
    def test_basic(self):
        assert ResearchDB._slugify("Hello World") == "hello-world"

    def test_special_chars(self):
        assert ResearchDB._slugify("ODE solver: v2.0!") == "ode-solver-v20"

    def test_max_words(self):
        slug = ResearchDB._slugify("one two three four five six seven")
        assert slug == "one-two-three-four-five"

    def test_empty(self):
        assert ResearchDB._slugify("") == ""
        assert ResearchDB._slugify("!!!") == ""
