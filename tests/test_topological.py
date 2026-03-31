"""Tests for topological_batches() — DAG scheduling."""

import pytest

from backend.pipeline.research import topological_batches


class TestTopologicalBatches:
    def test_no_dependencies(self):
        """All independent tasks → single batch."""
        tasks = [
            {"id": "1", "description": "a", "dependencies": []},
            {"id": "2", "description": "b", "dependencies": []},
            {"id": "3", "description": "c", "dependencies": []},
        ]
        batches = topological_batches(tasks)
        assert len(batches) == 1
        assert len(batches[0]) == 3

    def test_linear_chain(self):
        """1 → 2 → 3 → each in its own batch."""
        tasks = [
            {"id": "1", "description": "a", "dependencies": []},
            {"id": "2", "description": "b", "dependencies": ["1"]},
            {"id": "3", "description": "c", "dependencies": ["2"]},
        ]
        batches = topological_batches(tasks)
        assert len(batches) == 3
        assert batches[0][0]["id"] == "1"
        assert batches[1][0]["id"] == "2"
        assert batches[2][0]["id"] == "3"

    def test_diamond_dag(self):
        """Diamond: 1 → {2,3} → 4."""
        tasks = [
            {"id": "1", "description": "a", "dependencies": []},
            {"id": "2", "description": "b", "dependencies": ["1"]},
            {"id": "3", "description": "c", "dependencies": ["1"]},
            {"id": "4", "description": "d", "dependencies": ["2", "3"]},
        ]
        batches = topological_batches(tasks)
        assert len(batches) == 3
        batch_ids = [[t["id"] for t in b] for b in batches]
        assert batch_ids[0] == ["1"]
        assert set(batch_ids[1]) == {"2", "3"}
        assert batch_ids[2] == ["4"]

    def test_empty_list(self):
        assert topological_batches([]) == []

    def test_single_task(self):
        tasks = [{"id": "1", "description": "only", "dependencies": []}]
        batches = topological_batches(tasks)
        assert len(batches) == 1
        assert batches[0][0]["id"] == "1"

    def test_missing_dependencies_key(self):
        """Tasks without 'dependencies' key default to empty."""
        tasks = [
            {"id": "1", "description": "a"},
            {"id": "2", "description": "b"},
        ]
        batches = topological_batches(tasks)
        assert len(batches) == 1

    def test_circular_dependency_raises(self):
        """Circular deps should raise ValueError, not silently degrade."""
        tasks = [
            {"id": "1", "description": "a", "dependencies": ["2"]},
            {"id": "2", "description": "b", "dependencies": ["1"]},
        ]
        with pytest.raises(ValueError, match="cycle"):
            topological_batches(tasks)

    def test_missing_dependency_raises(self):
        """Reference to non-existent task should raise ValueError."""
        tasks = [
            {"id": "1", "description": "a", "dependencies": ["999"]},
        ]
        with pytest.raises(ValueError, match="unknown"):
            topological_batches(tasks)
