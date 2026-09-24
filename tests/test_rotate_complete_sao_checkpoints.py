"""Safety checks for bounded SAO checkpoint retention."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/train/rotate_complete_sao_checkpoints.py"


class RotationTest(unittest.TestCase):
    def test_preview_then_prune_only_oldest_complete_step(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as temp:
            root = Path(temp) / "sao-qwen35-9b-swesmith" / "sao-qwen35-9b-swesmith-64k-full-sp8-tokenpack-v1"
            root.mkdir(parents=True)
            (root / "latest_checkpointed_iteration.txt").write_text("4")
            for step in range(1, 5):
                folder = root / f"global_step_{step}"
                folder.mkdir()
                (folder / "data.pt").write_bytes(b"data")
                for role in ("actor", "critic"):
                    (folder / role).mkdir()
                    for kind in ("model", "optim", "extra_state"):
                        for rank in range(8):
                            (folder / role / f"{kind}_world_size_8_rank_{rank}.pt").write_bytes(b"x")

            cmd = [sys.executable, str(SCRIPT), "--root", str(root), "--expect-latest", "4", "--keep", "3"]
            preview = subprocess.check_output(cmd, text=True)
            self.assertIn("remove: [1]", preview)
            self.assertTrue((root / "global_step_1").exists())

            mismatch = subprocess.run(cmd[:-3] + ["3", "--keep", "3", "--apply"], capture_output=True)
            self.assertNotEqual(mismatch.returncode, 0)
            self.assertTrue((root / "global_step_1").exists())

            subprocess.run(cmd + ["--apply"], check=True, stdout=subprocess.DEVNULL)
            self.assertFalse((root / "global_step_1").exists())
            self.assertTrue(all((root / f"global_step_{step}").exists() for step in (2, 3, 4)))


if __name__ == "__main__":
    unittest.main()
