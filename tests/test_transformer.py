import os
import uuid
import keras
from importlib import reload
from keras import backend as K
from unittest import TestCase, SkipTest
from transformer.model import create_model, load_openai_model
from transformer.layers import SelfAttention, LayerNormalization, Gelu, TiedEmbeddingsTransposed


def set_keras_backend(backend):
    if K.backend() != backend:
        os.environ['KERAS_BACKEND'] = backend
        reload(K)
        assert K.backend() == backend


class TestTransformer(TestCase):
    def __init__(self, method_name: str = 'runTest') -> None:
        super().__init__(methodName=method_name)
        self.vocab_size = 37
        self.num_heads = 3
        self.num_layers = 2
        self.embedding_dim = 12
        self.d_hid = 13
        self.max_len = 24
        # TODO make theano work
        # TODO make cntk work too :D, but first install it :D, pip install cntk + agi libopencv-dev + agi openmpi-bin did not work
        self.supported_backends = {'tensorflow'}
        self.original_backend = K.backend()

    def tearDown(self):
        set_keras_backend(self.original_backend)

    def list_backends(self, orig_backend=None):
        if orig_backend is None:
            orig_backend = K.backend()
        # always start from the default backend
        return [orig_backend] + list(self.supported_backends - {orig_backend})

    def create_small_model(self, ignore_mask: bool, debug: bool = True):
        return create_model(ignore_mask=ignore_mask, vocab_size=self.vocab_size,
                            num_heads=self.num_heads, num_layers=self.num_layers,
                            embedding_dim=self.embedding_dim, d_hid=self.d_hid,
                            max_len=self.max_len, debug=debug, use_tied_decoder=False)

    # TODO compare with the original OpenAI implementation (tensorflow)
    def test_keras_load(self):
        pass

    @staticmethod
    def compare_two_models(model_a, model_b):
        assert len(model_a.weights) == len(model_b.weights)
        for x, y in zip(model_a.weights, model_b.weights):
            assert (K.eval(x) == K.eval(y)).all()

    # TODO this fails when the model is tied
    def test_save_load_all(self):
        for ignore_mask in [True, False]:
            model = self.create_small_model(ignore_mask, False)
            path = '/tmp/{}.model'.format(uuid.uuid4())
            try:
                model.save(path)
                new_model = keras.models.load_model(path, custom_objects={'SelfAttention': SelfAttention,
                                                                          'LayerNormalization': LayerNormalization,
                                                                          'Gelu': Gelu,
                                                                          'TiedEmbeddingsTransposed': TiedEmbeddingsTransposed})
                TestTransformer.compare_two_models(model, new_model)
            except Exception as e:
                raise e
            finally:
                if os.path.exists(path):
                    os.remove(path)

    def test_save_load_weights(self):
        for ignore_mask in [True, False]:
            model = self.create_small_model(ignore_mask, False)
            path = '/tmp/{}.model'.format(uuid.uuid4())
            try:
                model.save_weights(path)
                model.load_weights(path)
            except Exception as e:
                raise e
            finally:
                if os.path.exists(path):
                    os.remove(path)

    def test_different_backends_load_openai(self):
        if len(self.supported_backends) == 1:
            raise SkipTest('only one backend is supported for now :(')
        for ignore_mask in [True, False]:
            for use_one_embedding_dropout in [True, False]:
                orig_backend = K.backend()
                results_x = {}
                results_logit = {}
                for backend in self.list_backends(orig_backend):
                    try:
                        set_keras_backend(backend)
                    except ModuleNotFoundError:
                        continue
                    K.set_learning_phase(0)  # test
                    model = load_openai_model(ignore_mask=ignore_mask,
                                              use_one_embedding_dropout=use_one_embedding_dropout, debug=True)
                    results_x[backend] = K.eval(model.outputs[0])
                    results_logit[backend] = K.eval(model.outputs[1])
                    del model
                set_keras_backend(orig_backend)
                for k1 in results_x.keys():
                    for k2 in results_x.keys():
                        if k1 == k2:
                            continue
                        assert (results_x[k1] == results_x[k2]).all(), 'k1={}, k2={}'.format(k1, k2)
                        assert (results_logit[k1] == results_logit[k2]).all(), 'k1={}, k2={}'.format(k1, k2)

    def test_different_backends_work(self):
        for ignore_mask in [True, False]:
            orig_backend = K.backend()
            results_x = {}
            results_logit = {}
            for backend in self.list_backends(orig_backend):
                try:
                    set_keras_backend(backend)
                except ModuleNotFoundError:
                    pass
                K.set_learning_phase(0)  # test
                model = self.create_small_model(ignore_mask=ignore_mask)
                results_x[backend] = K.eval(model.outputs[0])
                results_logit[backend] = K.eval(model.outputs[1])
                del model
            set_keras_backend(orig_backend)