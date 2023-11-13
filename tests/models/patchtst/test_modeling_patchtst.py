# coding=utf-8
# Copyright 2023 The HuggingFace Inc. team. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
""" Testing suite for the PyTorch PatchTST model. """

import inspect
import random
import tempfile
import unittest

from huggingface_hub import hf_hub_download

from transformers import is_torch_available
from transformers.models.auto import get_values
from transformers.testing_utils import is_flaky, require_torch, slow, torch_device

from ...test_configuration_common import ConfigTester
from ...test_modeling_common import ModelTesterMixin, floats_tensor, ids_tensor
from ...test_pipeline_mixin import PipelineTesterMixin


TOLERANCE = 1e-4

if is_torch_available():
    import torch

    from transformers import (
        MODEL_FOR_TIME_SERIES_CLASSIFICATION_MAPPING,
        MODEL_FOR_TIME_SERIES_REGRESSION_MAPPING,
        PatchTSTConfig,
        PatchTSTForClassification,
        PatchTSTForPrediction,
        PatchTSTForPretraining,
        PatchTSTForRegression,
        PatchTSTModel,
    )


@require_torch
class PatchTSTModelTester:
    def __init__(
        self,
        parent,
        batch_size=13,
        prediction_length=7,
        context_length=14,
        patch_length=5,
        patch_stride=5,
        num_input_channels=1,
        num_time_features=1,
        is_training=True,
        hidden_size=16,
        num_hidden_layers=2,
        num_attention_heads=4,
        intermediate_size=4,
        hidden_act="gelu",
        hidden_dropout_prob=0.1,
        attention_probs_dropout_prob=0.1,
        lags_sequence=[1, 2, 3, 4, 5],
        distil=False,
        seed_number=42,
        num_targets=2,
        num_output_channels=2,
    ):
        self.parent = parent
        self.batch_size = batch_size
        self.prediction_length = prediction_length
        self.context_length = context_length
        self.patch_length = patch_length
        self.patch_stride = patch_stride
        self.num_input_channels = num_input_channels
        self.num_time_features = num_time_features
        self.lags_sequence = lags_sequence
        self.is_training = is_training
        self.hidden_size = hidden_size
        self.num_hidden_layers = num_hidden_layers
        self.num_attention_heads = num_attention_heads
        self.intermediate_size = intermediate_size
        self.hidden_act = hidden_act
        self.hidden_dropout_prob = hidden_dropout_prob
        self.attention_probs_dropout_prob = attention_probs_dropout_prob

        self.seed_number = seed_number
        self.num_targets = num_targets
        self.num_output_channels = num_output_channels
        self.distil = distil
        self.num_patches = (max(self.context_length, self.patch_length) - self.patch_length) // self.patch_stride + 1

    def get_config(self):
        return PatchTSTConfig(
            prediction_length=self.prediction_length,
            patch_length=self.patch_length,
            patch_stride=self.patch_stride,
            num_input_channels=self.num_input_channels,
            d_model=self.hidden_size,
            encoder_layers=self.num_hidden_layers,
            encoder_attention_heads=self.num_attention_heads,
            encoder_ffn_dim=self.intermediate_size,
            dropout=self.hidden_dropout_prob,
            attention_dropout=self.attention_probs_dropout_prob,
            context_length=self.context_length,
            activation_function=self.hidden_act,
            seed_number=self.seed_number,
            num_targets=self.num_targets,
            num_output_channels=self.num_output_channels,
        )

    def prepare_patchtst_inputs_dict(self, config):
        _past_length = config.context_length
        # bs, num_input_channels, num_patch, patch_len

        # [bs x seq_len x num_input_channels]
        past_values = floats_tensor([self.batch_size, _past_length, self.num_input_channels])

        future_values = floats_tensor([self.batch_size, config.prediction_length, self.num_input_channels])

        inputs_dict = {
            "past_values": past_values,
            "future_values": future_values,
        }
        return inputs_dict

    def prepare_config_and_inputs(self):
        config = self.get_config()
        inputs_dict = self.prepare_patchtst_inputs_dict(config)
        return config, inputs_dict

    def prepare_config_and_inputs_for_common(self):
        config, inputs_dict = self.prepare_config_and_inputs()
        return config, inputs_dict


@require_torch
class PatchTSTModelTest(ModelTesterMixin, PipelineTesterMixin, unittest.TestCase):
    all_model_classes = (
        (
            PatchTSTModel,
            PatchTSTForPrediction,
            PatchTSTForPretraining,
            PatchTSTForClassification,
            PatchTSTForRegression,
        )
        if is_torch_available()
        else ()
    )
    all_generative_model_classes = (
        (PatchTSTForPrediction, PatchTSTForRegression, PatchTSTForPretraining) if is_torch_available() else ()
    )
    pipeline_model_mapping = {"feature-extraction": PatchTSTModel} if is_torch_available() else {}
    test_pruning = False
    test_head_masking = False
    test_missing_keys = False
    test_torchscript = False
    test_inputs_embeds = False
    test_model_common_attributes = False

    test_resize_embeddings = True
    test_resize_position_embeddings = False
    test_mismatched_shapes = True
    test_model_parallel = False
    has_attentions = False

    def setUp(self):
        self.model_tester = PatchTSTModelTester(self)
        self.config_tester = ConfigTester(
            self,
            config_class=PatchTSTConfig,
            has_text_modality=False,
            prediction_length=self.model_tester.prediction_length,
        )

    def test_config(self):
        self.config_tester.run_common_tests()

    def _prepare_for_class(self, inputs_dict, model_class, return_labels=False):
        inputs_dict = super()._prepare_for_class(inputs_dict, model_class, return_labels=return_labels)

        #  if PatchTSTForPretraining
        if model_class == PatchTSTForPretraining:
            inputs_dict.pop("future_values")
        # else if classification model:
        elif model_class in get_values(MODEL_FOR_TIME_SERIES_CLASSIFICATION_MAPPING):
            rng = random.Random(self.model_tester.seed_number)
            labels = ids_tensor([self.model_tester.batch_size], self.model_tester.num_targets, rng=rng)
            inputs_dict["target_values"] = labels
            inputs_dict.pop("future_values")
        elif model_class in get_values(MODEL_FOR_TIME_SERIES_REGRESSION_MAPPING):
            rng = random.Random(self.model_tester.seed_number)
            target_values = floats_tensor(
                [self.model_tester.batch_size, self.model_tester.num_output_channels], rng=rng
            )
            inputs_dict["target_values"] = target_values
            inputs_dict.pop("future_values")
        return inputs_dict

    def test_save_load_strict(self):
        config, _ = self.model_tester.prepare_config_and_inputs()
        for model_class in self.all_model_classes:
            model = model_class(config)

            with tempfile.TemporaryDirectory() as tmpdirname:
                model.save_pretrained(tmpdirname)
                model2, info = model_class.from_pretrained(tmpdirname, output_loading_info=True)
            self.assertEqual(info["missing_keys"], [])

    def test_hidden_states_output(self):
        def check_hidden_states_output(inputs_dict, config, model_class):
            model = model_class(config)
            model.to(torch_device)
            model.eval()

            with torch.no_grad():
                outputs = model(**self._prepare_for_class(inputs_dict, model_class))

            hidden_states = outputs.hidden_states

            expected_num_layers = getattr(
                self.model_tester, "expected_num_hidden_layers", self.model_tester.num_hidden_layers
            )
            self.assertEqual(len(hidden_states), expected_num_layers)

            num_patch = self.model_tester.num_patches
            self.assertListEqual(
                list(hidden_states[0].shape[-2:]),
                [num_patch, self.model_tester.hidden_size],
            )

        config, inputs_dict = self.model_tester.prepare_config_and_inputs_for_common()

        for model_class in self.all_model_classes:
            inputs_dict["output_hidden_states"] = True
            print("model_class: ", model_class)

            check_hidden_states_output(inputs_dict, config, model_class)

            # check that output_hidden_states also work using config
            del inputs_dict["output_hidden_states"]
            config.output_hidden_states = True

            check_hidden_states_output(inputs_dict, config, model_class)

    @unittest.skip(reason="we have no tokens embeddings")
    def test_resize_tokens_embeddings(self):
        pass

    def test_model_main_input_name(self):
        model_signature = inspect.signature(getattr(PatchTSTModel, "forward"))
        # The main input is the name of the argument after `self`
        observed_main_input_name = list(model_signature.parameters.keys())[1]
        self.assertEqual(PatchTSTModel.main_input_name, observed_main_input_name)

    def test_forward_signature(self):
        config, _ = self.model_tester.prepare_config_and_inputs_for_common()

        for model_class in self.all_model_classes:
            model = model_class(config)
            signature = inspect.signature(model.forward)
            # signature.parameters is an OrderedDict => so arg_names order is deterministic
            arg_names = [*signature.parameters.keys()]

            expected_arg_names = [
                "past_values",
                "past_observed_mask",
                "future_values",
            ]
            if model_class == PatchTSTForPretraining:
                expected_arg_names.remove("future_values")
            elif model_class in get_values(MODEL_FOR_TIME_SERIES_CLASSIFICATION_MAPPING) or model_class in get_values(
                MODEL_FOR_TIME_SERIES_REGRESSION_MAPPING
            ):
                expected_arg_names.remove("future_values")
                expected_arg_names.remove("past_observed_mask")
                expected_arg_names.append("target_values") if model_class in get_values(
                    MODEL_FOR_TIME_SERIES_CLASSIFICATION_MAPPING
                ) else expected_arg_names.append("target_values")
                expected_arg_names.append("past_observed_mask")
            expected_arg_names.extend(
                [
                    "output_hidden_states",
                    "output_attentions",
                    "return_dict",
                ]
            )

            self.assertListEqual(arg_names[: len(expected_arg_names)], expected_arg_names)

    @is_flaky()
    def test_retain_grad_hidden_states_attentions(self):
        super().test_retain_grad_hidden_states_attentions()


# Note: Publishing of this dataset is under internal review. The dataset is not yet downloadable.
def prepare_batch(repo_id="ibm/etth1-forecast-test", file="train-batch.pt"):
    file = hf_hub_download(repo_id=repo_id, filename=file, repo_type="dataset")
    batch = torch.load(file, map_location=torch_device)
    return batch


# Note: Publishing of pretrained weights is under internal review. Pretrained model is not yet downloadable.
@require_torch
@slow
class PatchTSTModelIntegrationTests(unittest.TestCase):
    # Publishing of pretrained weights are under internal review. Pretrained model is not yet downloadable.
    def test_pretrain_head(self):
        model = PatchTSTForPretraining.from_pretrained("ibm/patchtst-etth1-pretrain").to(torch_device)
        batch = prepare_batch()

        torch.manual_seed(0)
        with torch.no_grad():
            output = model(past_values=batch["past_values"].to(torch_device)).prediction_output
        num_patch = (
            max(model.config.context_length, model.config.patch_length) - model.config.patch_length
        ) // model.config.patch_stride + 1
        expected_shape = torch.Size([64, model.config.num_input_channels, num_patch, model.config.patch_length])
        self.assertEqual(output.shape, expected_shape)

        expected_slice = torch.tensor(
            [[[-0.5409]], [[0.3093]], [[-0.3759]], [[0.5068]], [[-0.8387]], [[0.0937]], [[0.2809]]],
            device=torch_device,
        )
        self.assertTrue(torch.allclose(output[0, :7, :1, :1], expected_slice, atol=TOLERANCE))

    # Publishing of pretrained weights are under internal review. Pretrained model is not yet downloadable.
    def test_prediction_head(self):
        model = PatchTSTForPrediction.from_pretrained("ibm/patchtst-etth1-forecast").to(torch_device)

        batch = prepare_batch(file="test-batch.pt")

        torch.manual_seed(0)
        with torch.no_grad():
            output = model(
                past_values=batch["past_values"].to(torch_device),
                future_values=batch["future_values"].to(torch_device),
            ).prediction_outputs
        expected_shape = torch.Size([64, model.config.prediction_length, model.config.num_input_channels])
        self.assertEqual(output.shape, expected_shape)

        expected_slice = torch.tensor(
            [[0.3228, 0.4320, 0.4591, 0.4066, -0.3461, 0.3094, -0.8426]],
            device=torch_device,
        )
        self.assertTrue(torch.allclose(output[0, :1, :7], expected_slice, atol=TOLERANCE))
