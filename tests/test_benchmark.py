import os
import tempfile
import unittest
from pathlib import Path

from transformers import GPT2Config, is_torch_available

from .utils import require_torch


if is_torch_available():
    from transformers import (
        PyTorchBenchmarkArguments,
        PyTorchBenchmark,
    )


@require_torch
class BenchmarkTest(unittest.TestCase):
    def check_results_dict_not_empty(self, results):
        for model_result in results.values():
            for batch_size, sequence_length in zip(model_result["bs"], model_result["ss"]):
                result = model_result["result"][batch_size][sequence_length]
                self.assertIsNotNone(result)

    def test_inference_no_configs(self):
        MODEL_ID = "sshleifer/tiny-gpt2"
        benchmark_args = PyTorchBenchmarkArguments(
            models=[MODEL_ID], training=False, no_inference=False, sequence_lengths=[8], batch_sizes=[1]
        )
        benchmark = PyTorchBenchmark(benchmark_args)
        results = benchmark.run()
        self.check_results_dict_not_empty(results.time_inference_result)
        self.check_results_dict_not_empty(results.memory_inference_result)

    def test_train_no_configs(self):
        MODEL_ID = "sshleifer/tiny-gpt2"
        benchmark_args = PyTorchBenchmarkArguments(
            models=[MODEL_ID], training=True, no_inference=True, sequence_lengths=[8], batch_sizes=[1]
        )
        benchmark = PyTorchBenchmark(benchmark_args)
        results = benchmark.run()
        self.check_results_dict_not_empty(results.time_train_result)
        self.check_results_dict_not_empty(results.memory_train_result)

    def test_inference_with_configs(self):
        MODEL_ID = "sshleifer/tiny-gpt2"
        config = GPT2Config.from_pretrained(MODEL_ID)
        benchmark_args = PyTorchBenchmarkArguments(
            models=[MODEL_ID], training=False, no_inference=False, sequence_lengths=[8], batch_sizes=[1]
        )
        benchmark = PyTorchBenchmark(benchmark_args, configs=[config])
        results = benchmark.run()
        self.check_results_dict_not_empty(results.time_inference_result)
        self.check_results_dict_not_empty(results.memory_inference_result)

    def test_train_with_configs(self):
        MODEL_ID = "sshleifer/tiny-gpt2"
        config = GPT2Config.from_pretrained(MODEL_ID)
        benchmark_args = PyTorchBenchmarkArguments(
            models=[MODEL_ID], training=True, no_inference=True, sequence_lengths=[8], batch_sizes=[1]
        )
        benchmark = PyTorchBenchmark(benchmark_args, configs=[config])
        results = benchmark.run()
        self.check_results_dict_not_empty(results.time_train_result)
        self.check_results_dict_not_empty(results.memory_train_result)

    def test_save_csv_files(self):
        MODEL_ID = "sshleifer/tiny-gpt2"
        with tempfile.TemporaryDirectory() as tmp_dir:
            benchmark_args = PyTorchBenchmarkArguments(
                models=[MODEL_ID],
                training=True,
                no_inference=False,
                save_to_csv=True,
                sequence_lengths=[8],
                batch_sizes=[1],
                inference_time_csv_file=os.path.join(tmp_dir, "inf_time.csv"),
                train_memory_csv_file=os.path.join(tmp_dir, "train_mem.csv"),
                inference_memory_csv_file=os.path.join(tmp_dir, "inf_mem.csv"),
                train_time_csv_file=os.path.join(tmp_dir, "train_time.csv"),
                env_info_csv_file=os.path.join(tmp_dir, "env.csv"),
            )
            benchmark = PyTorchBenchmark(benchmark_args)
            benchmark.run()
            self.assertTrue(Path(os.path.join(tmp_dir, "inf_time.csv")).exists())
            self.assertTrue(Path(os.path.join(tmp_dir, "train_time.csv")).exists())
            self.assertTrue(Path(os.path.join(tmp_dir, "inf_mem.csv")).exists())
            self.assertTrue(Path(os.path.join(tmp_dir, "train_mem.csv")).exists())
            self.assertTrue(Path(os.path.join(tmp_dir, "env.csv")).exists())
