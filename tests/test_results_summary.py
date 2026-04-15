import json
import tempfile
import unittest

from backend.db import ResearchDB
from backend.pipeline.research import ResearchStage


class ResultsSummaryTests(unittest.TestCase):
    def test_research_stage_generates_deterministic_results_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = ResearchDB(base_dir=tmpdir)
            db.create_session("results summary")
            db.save_refined_idea("Measure whether transferred backdoors persist after fine-tuning.")
            db.save_score_direction(True)
            db.update_meta(current_score=0.11, previous_score=0.19, improved=True)
            db.save_evaluation({
                "feedback": "Promising trend.",
                "suggestions": ["Run a stronger baseline."],
                "score": 0.11,
                "satisfied": True,
            }, 0)
            db.save_plan({}, [{
                "id": "1",
                "description": "Train baseline",
                "dependencies": [],
                "status": "completed",
                "batch": 1,
                "summary": "Baseline completed.",
            }])
            db.save_task_output("1", "Task output")

            task_artifacts = db.get_artifacts_dir("1")
            (task_artifacts / "best_score.json").write_text(json.dumps({
                "metric": "final_asr_t",
                "score": 0.11,
                "model": "baseline",
            }), encoding="utf-8")
            (task_artifacts / "curve.png").write_text("png", encoding="utf-8")

            root_artifacts = db.get_artifacts_dir()
            (root_artifacts / "best_score.json").write_text(json.dumps({
                "metric": "final_asr_t",
                "score": 0.11,
            }), encoding="utf-8")
            (root_artifacts / "latest_score.json").write_text(json.dumps({
                "metric": "final_asr_t",
                "score": 0.13,
            }), encoding="utf-8")

            stage = ResearchStage(db=db)
            stage._task_results = {"1": "Task output"}

            stage._build_final_output()

            summary_json = db.get_results_summary_json()
            summary_text = db.get_results_summary()
            summary_md_path = db.get_tasks_dir().parent / "results_summary.md"

            self.assertEqual(
                summary_json["research_goal"],
                "Measure whether transferred backdoors persist after fine-tuning.",
            )
            self.assertEqual(summary_json["score_direction"], "minimize")
            self.assertEqual(summary_json["best_score"]["score"], 0.11)
            self.assertEqual(summary_json["latest_score"]["score"], 0.13)
            self.assertEqual(summary_json["evaluation_rounds"][0]["round"], 1)
            self.assertEqual(summary_json["completed_tasks"][0]["id"], "1")
            self.assertEqual(summary_json["completed_tasks"][0]["best_score"]["model"], "baseline")
            self.assertIn("artifacts/1/curve.png", [f["path"] for f in summary_json["figures"]])
            self.assertIn('"research_goal"', summary_text)
            self.assertIn('"completed_tasks"', summary_text)
            self.assertIn("artifacts/1/curve.png", summary_text)
            self.assertTrue(summary_md_path.exists())
            self.assertIn("# Results Summary", summary_md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
