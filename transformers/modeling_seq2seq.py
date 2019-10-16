# coding=utf-8
# Copyright 2018 The HuggingFace Inc. team.
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
""" Auto Model class. """

from __future__ import absolute_import, division, print_function, unicode_literals

import logging

import torch
from torch import nn

from .file_utils import add_start_docstrings
from .modeling_auto import AutoModel, AutoModelWithLMHead
from .modeling_utils import PreTrainedModel, SequenceSummary

logger = logging.getLogger(__name__)


class PreTrainedSeq2seq(nn.Module):
    r"""
        :class:`~transformers.Seq2seq` is a generic model class that will be
        instantiated as a Seq2seq model with one of the base model classes of
        the library as encoder and (optionally) as decoder when created with
        the `AutoModel.from_pretrained(pretrained_model_name_or_path)` class
        method.
    """
    def __init__(self, encoder, decoder):
        super(PreTrainedSeq2seq, self).__init__()
        self.encoder = encoder
        self.decoder = decoder

    @classmethod
    def from_pretrained(cls, encoder_pretrained_model_name_or_path, decoder_pretrained_model_name_or_path, *model_args, **kwargs):
        r""" Instantiates an encoder and a decoder from one or two base classes
        of the library from pre-trained model checkpoints.


        The model is set in evaluation mode by default using `model.eval()` (Dropout modules are deactivated)
        To train the model, you need to first set it back in training mode with `model.train()`

        Params:
            encoder_pretrained_model_name_or_path: information necessary to initiate the encoder. Either:

                - a string with the `shortcut name` of a pre-trained model to load from cache or download, e.g.: ``bert-base-uncased``.
                - a path to a `directory` containing model weights saved using :func:`~transformers.PreTrainedModel.save_pretrained`, e.g.: ``./my_model_directory/``.
                - a path or url to a `tensorflow index checkpoint file` (e.g. `./tf_model/model.ckpt.index`). In this case, ``from_tf`` should be set to True and a configuration object should be provided as ``config`` argument. This loading path is slower than converting the TensorFlow checkpoint in a PyTorch model using the provided conversion scripts and loading the PyTorch model afterwards.

            decoder_pretrained_model_name_or_path: information necessary to initiate the decoder. Either:

                - a string with the `shortcut name` of a pre-trained model to load from cache or download, e.g.: ``bert-base-uncased``.
                - a path to a `directory` containing model weights saved using :func:`~transformers.PreTrainedModel.save_pretrained`, e.g.: ``./my_model_directory/``.
                - a path or url to a `tensorflow index checkpoint file` (e.g. `./tf_model/model.ckpt.index`). In this case, ``from_tf`` should be set to True and a configuration object should be provided as ``config`` argument. This loading path is slower than converting the TensorFlow checkpoint in a PyTorch model using the provided conversion scripts and loading the PyTorch model afterwards.

            model_args: (`optional`) Sequence of positional arguments:
                All remaning positional arguments will be passed to the underlying model's ``__init__`` method

            config: (`optional`) instance of a class derived from :class:`~transformers.PretrainedConfig`:
                Configuration for the model to use instead of an automatically loaded configuation. Configuration can be automatically loaded when:

                - the model is a model provided by the library (loaded with the ``shortcut-name`` string of a pretrained model), or
                - the model was saved using :func:`~transformers.PreTrainedModel.save_pretrained` and is reloaded by suppling the save directory.
                - the model is loaded by suppling a local directory as ``pretrained_model_name_or_path`` and a configuration JSON file named `config.json` is found in the directory.

            state_dict: (`optional`) dict:
                an optional state dictionnary for the model to use instead of a state dictionary loaded from saved weights file.
                This option can be used if you want to create a model from a pretrained configuration but load your own weights.
                In this case though, you should check if using :func:`~transformers.PreTrainedModel.save_pretrained` and :func:`~transformers.PreTrainedModel.from_pretrained` is not a simpler option.

            cache_dir: (`optional`) string:
                Path to a directory in which a downloaded pre-trained model
                configuration should be cached if the standard cache should not be used.

            force_download: (`optional`) boolean, default False:
                Force to (re-)download the model weights and configuration files and override the cached versions if they exists.

            proxies: (`optional`) dict, default None:
                A dictionary of proxy servers to use by protocol or endpoint, e.g.: {'http': 'foo.bar:3128', 'http://hostname': 'foo.bar:4012'}.
                The proxies are used on each request.

            output_loading_info: (`optional`) boolean:
                Set to ``True`` to also return a dictionnary containing missing keys, unexpected keys and error messages.

            kwargs: (`optional`) Remaining dictionary of keyword arguments.
                Can be used to update the configuration object (after it being loaded) and initiate the model. (e.g. ``output_attention=True``). Behave differently depending on whether a `config` is provided or automatically loaded:

                - If a configuration is provided with ``config``, ``**kwargs`` will be directly passed to the underlying model's ``__init__`` method (we assume all relevant updates to the configuration have already been done)
                - If a configuration is not provided, ``kwargs`` will be first passed to the configuration class initialization function (:func:`~transformers.PretrainedConfig.from_pretrained`). Each key of ``kwargs`` that corresponds to a configuration attribute will be used to override said attribute with the supplied ``kwargs`` value. Remaining keys that do not correspond to any configuration attribute will be passed to the underlying model's ``__init__`` function.

                You can specify different kwargs for the decoder by prefixing the key with `decoder_` (e.g. ``decoder_output_attention=True``).

        Examples::

            model = PreTrainedSeq2seq.from_pretained('bert-base-uncased', 'bert-base-uncased') # initialize Bert2Bert
        """

        # Separate the encoder- and decoder- specific kwargs. A kwarg is
        # decoder-specific it the key starts with `decoder_`
        kwargs_decoder = {}
        kwargs_encoder = kwargs
        for key in kwargs_encoder.keys():
            if key.startswith('decoder_'):
                kwargs_decoder[key.replace('decoder_', '')] = kwargs_encoder.pop(key)

        # Load and initialize the encoder and decoder
        #  The distinction between encoder and decoder at the model level is made
        #  by the value of the flag `is_decoder` that we need to set correctly.
        encoder = kwargs.pop('encoder_model', None)
        if encoder is None:
            kwargs_encoder['is_decoder'] = False
            encoder = AutoModel.from_pretrained(encoder_pretrained_model_name_or_path, *model_args, **kwargs_encoder)

        decoder = kwargs.pop('decoder_model', None)
        if decoder is None:
            kwargs_decoder['is_decoder'] = True
            decoder = AutoModelWithLMHead.from_pretrained(decoder_pretrained_model_name_or_path, **kwargs_decoder)

        model = cls(encoder, decoder)

        return model

    def forward(self, encoder_input_ids, decoder_input_ids, **kwargs):
        """ The forward pass on a seq2eq depends what we are performing:

        - During training we perform one forward pass through both the encoder
          and decoder;
        - During prediction, we perform one forward pass through the encoder,
          and then perform several forward passes with the encoder's hidden
          state through the decoder to decode a full sequence.

        Therefore, we skip the forward pass on the encoder if an argument named
        `encoder_hidden_state` is passed to this function.

        Params:
            encoder_input_ids: ``torch.LongTensor`` of shape ``(batch_size, sequence_length)``
                Indices of encoder input sequence tokens in the vocabulary.
            decoder_input_ids: ``torch.LongTensor`` of shape ``(batch_size, sequence_length)``
                Indices of decoder input sequence tokens in the vocabulary.
        """
        # Separate the encoder- and decoder- specific kwargs. A kwarg is
        # decoder-specific it the key starts with `decoder_`
        kwargs_decoder = {}
        kwargs_encoder = kwargs
        for key in kwargs_encoder.keys():
            if key.startswith('decoder_'):
                kwargs_decoder[key.replace('decoder_', '')] = kwargs_encoder.pop(key)

        # Encode if needed (training, first prediction pass)
        encoder_hidden_states = kwargs_encoder.pop('encoder_hidden_states', None)
        if encoder_hidden_states is None:
            encoder_outputs = self.encoder(encoder_input_ids, **kwargs_encoder)
            encoder_hidden_states = encoder_outputs[0]
        else:
            encoder_outputs = ()

        # Decode
        kwargs_decoder['encoder_hidden_states'] = encoder_hidden_states
        decoder_outputs = self.decoder(decoder_input_ids, **kwargs_decoder)

        return decoder_outputs + encoder_outputs


class Model2Model(PreTrainedSeq2seq):
    def tie_weights():
        # We should tie encoder and decoder embeddings if possible here
        pass


class Model2LSTM(PreTrainedSeq2seq):
    @classmethod
    def from_pretrained(cls, *args, **kwargs):
        if kwargs.get('decoder_model', None) is None:
            # We will create a randomly initilized LSTM model as decoder
            if 'decoder_config' not in kwargs:
                raise ValueError("To load an LSTM in Seq2seq model, please supply either: "
                                 "    - a torch.nn.LSTM model as `decoder_model` parameter (`decoder_model=lstm_model`), or"
                                 "    - a dictionary of configuration parameters that will be used to initialize a"
                                 "      torch.nn.LSTM model as `decoder_config` keyword argument. "
                                 "      E.g. `decoder_config={'input_size': 768, 'hidden_size': 768, 'num_layers': 2}`")
            kwargs['decoder_model'] = torch.nn.LSTM(kwargs.pop('decoder_config'))
        model = super(Model2LSTM, cls).from_pretrained(*args, **kwargs)
        return model
