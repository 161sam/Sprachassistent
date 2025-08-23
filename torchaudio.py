import numpy as np


def load(path):
    return np.zeros((1, 10)), 44100


class functional:
    @staticmethod
    def resample(wav, src_sr, dst_sr):
        return wav

# TODO: replace this torchaudio stub with the real dependency when available
#       (see TODO-Index.md: Backend)
