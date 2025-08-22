from scripts.repo_hygiene import find_issues


def names(issues):
    return {i.path.name: i.reason for i in issues}


def test_detects_backup_and_pycache(tmp_path):
    backup = tmp_path / "foo.py.bak"
    backup.write_text("# test")
    pycache = tmp_path / "__pycache__"
    pycache.mkdir()
    compiled = pycache / "mod.cpython-311.pyc"
    compiled.write_bytes(b"0")

    issues = find_issues(tmp_path)
    mapping = names(issues)

    assert backup.name in mapping and mapping[backup.name] == "Sicherungsdatei"
    assert pycache.name in {i.path.name for i in issues}
    assert compiled.name in mapping and mapping[compiled.name] == "Kompilierte Python-Datei"
