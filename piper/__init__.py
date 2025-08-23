class PiperVoice:
    def __init__(self, model_path: str = ""):
        self.model_path = model_path

    @classmethod
    def load(cls, model_path: str):
        return cls(model_path)

    def synthesize(self, text, cfg=None):
        return b"", 22050


class SynthesisConfig:
    def __init__(self, **kwargs):
        pass
