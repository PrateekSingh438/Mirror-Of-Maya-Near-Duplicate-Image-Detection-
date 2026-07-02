"""Tests for _safe_extract_zip: path traversal and zip-bomb limits are
enforced before anything is written to disk."""
import os
import zipfile

import pytest

import config
from ui_components import _safe_extract_zip


def make_zip(path, entries):
    with zipfile.ZipFile(path, "w") as zf:
        for name, data in entries:
            zf.writestr(name, data)
    return str(path)


def test_normal_archive_extracts(tmp_path):
    zp = make_zip(tmp_path / "ok.zip", [("a/x.jpg", b"data"), ("b/y.jpg", b"data2")])
    target = tmp_path / "out"
    _safe_extract_zip(zp, str(target))
    assert (target / "a" / "x.jpg").read_bytes() == b"data"


def test_path_traversal_rejected(tmp_path):
    zp = make_zip(tmp_path / "bad.zip", [("../evil.txt", b"x")])
    target = tmp_path / "out"
    target.mkdir()
    with pytest.raises(ValueError, match="Unsafe path"):
        _safe_extract_zip(zp, str(target))
    assert not (tmp_path / "evil.txt").exists()


def test_entry_count_limit_blocks_before_extraction(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "MAX_ZIP_ENTRIES", 3)
    zp = make_zip(tmp_path / "many.zip", [(f"f{i}.jpg", b"x") for i in range(5)])
    target = tmp_path / "out"
    target.mkdir()
    with pytest.raises(ValueError, match="entries"):
        _safe_extract_zip(zp, str(target))
    assert os.listdir(target) == []


def test_uncompressed_size_limit_blocks_before_extraction(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "MAX_ZIP_UNCOMPRESSED_MB", 1)
    zp = make_zip(tmp_path / "big.zip", [("huge.bin", b"\0" * (2 * 1024 * 1024))])
    target = tmp_path / "out"
    target.mkdir()
    with pytest.raises(ValueError, match="MB"):
        _safe_extract_zip(zp, str(target))
    assert os.listdir(target) == []
