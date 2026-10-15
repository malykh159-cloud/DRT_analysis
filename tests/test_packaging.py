from pathlib import Path
import importlib.util

_spec = importlib.util.spec_from_file_location("verify_bundle", Path(__file__).resolve().parents[1]/"scripts"/"verify_bundle.py")
verify = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(verify)


def test_rejects_poppler_icu_even_with_similar_path_prefix(tmp_path):
    allowed = tmp_path/"python"
    poppler = tmp_path/"python-other"/"poppler"
    records = [
        ("Qt6Core.dll", str(allowed/"Qt6Core.dll"), "BINARY"),
        ("QtCore.pyd", str(allowed/"QtCore.pyd"), "EXTENSION"),
        ("icuuc.dll", str(poppler/"icuuc.dll"), "BINARY"),
    ]
    assert verify.foreign_binaries(records, [allowed]) == [records[-1]]


def test_collects_native_records_without_treating_documentation_as_binaries(tmp_path):
    good = ("library.dll", str(tmp_path/"library.dll"), "BINARY")
    other = ("module.pyd", str(tmp_path/"module.pyd"), "EXTENSION")
    manifest = ("output", [good, ("docs/readme.md", "unrelated/docs.md", "DATA"), other], [])
    records = list(verify.binary_records(manifest))
    assert records == [good, other]
    assert not verify.foreign_binaries(records, [tmp_path])
