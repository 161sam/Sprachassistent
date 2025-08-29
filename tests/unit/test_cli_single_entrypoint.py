from ws_server import cli as va_cli


def test_cli_parses_new_flags():
    args = va_cli._parse_args(["va", "--host", "0.0.0.0", "--port", "1234",
                               "--tts-progress", "1",
                               "--zonos-local-dir", "models/zonos/local",
                               "--zonos-model-id", "Zyphra/Zonos-v0.1-transformer",
                               "--zonos-speaker", "thorsten",
                               "--language", "de-DE"])  # type: ignore
    assert args.host == "0.0.0.0"
    assert args.port == 1234
    assert args.tts_progress == "1"
    assert args.zonos_local_dir.endswith("models/zonos/local")
    assert args.zonos_model_id.startswith("Zyphra/")
    assert args.zonos_speaker == "thorsten"
    assert args.language == "de-DE"

