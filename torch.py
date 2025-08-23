import contextlib
import numpy as np

float16 = 'float16'
float32 = 'float32'

# TODO: replace this minimal torch stub with the actual library or a proper
#       test double (see TODO-Index.md: Backend)

class _Cuda:
    @staticmethod
    def is_available() -> bool:
        return False

cuda = _Cuda()

class Tensor:
    def __init__(self, data):
        self._data = np.array(data)
        self.dtype = float32

    # basic tensor-like helpers
    def dim(self):
        return self._data.ndim

    def size(self, idx):
        return self._data.shape[idx]

    def mean(self, dim=0, keepdim=False):
        return Tensor(self._data.mean(axis=dim, keepdims=keepdim))

    def cpu(self):
        return self

    def detach(self):
        return self

    def numpy(self):
        return self._data

    def squeeze(self, axis=None):
        return Tensor(np.squeeze(self._data, axis=None if axis is None else axis))

    def __getitem__(self, item):
        return Tensor(self._data[item])


def zeros(*shape):
    return Tensor(np.zeros(shape, dtype=np.float32))


@contextlib.contextmanager
def autocast(*args, **kwargs):
    yield
