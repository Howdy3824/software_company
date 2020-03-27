import logging
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from .evaluate_cnn import run_generate


articles = ["New York (CNN)When Liana Barrientos was 23 years old, she got married in Westchester County."]

logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger()


class TestT5Examples(unittest.TestCase):
    def test_t5_cli(self):
        stream_handler = logging.StreamHandler(sys.stdout)
        logger.addHandler(stream_handler)
        tmp = Path(tempfile.gettempdir()) / "utest_generations.hypo"
        with tmp.open("w") as f:
            f.write("\n".join(articles))
        testargs = ["evaluate_cnn.py", "t5-small", str(tmp), "output.txt", str(tmp), "score.txt"]
        with patch.object(sys, "argv", testargs):
            run_generate()
            self.assertTrue(Path("output.txt").exists())
            self.assertTrue(Path("score.txt").exists())
