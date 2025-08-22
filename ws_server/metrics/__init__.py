# package


def get_metrics_api(voice_server=None):
    try:
        from .http_api import MetricsAPI
        return MetricsAPI(voice_server)
    except Exception:
        return None
