from pathlib import Path
import numpy as np
import pytest
from drt_analyzer.data.importers import load_spectrum
from drt_analyzer.data.column_detection import ImportErrorDetail, SignAmbiguity


def write_data(path, header="Frequency (Hz);Re(Z);Im(Z)", sep=";", sign=-1):
    rows = [sep.join([str(10**(i/2)), "12,3", str(sign*(i+1))]) for i in range(10)]
    path.write_text(header+"\n"+"\n".join(rows), encoding="utf-8")
    return path


def test_decimal_comma_and_immutable(tmp_path):
    raw = load_spectrum(write_data(tmp_path/"test.csv"))
    assert raw.real[0] == 12.3
    assert raw.impedance[0].imag == -1
    with pytest.raises(ValueError):
        raw.real[0] = 9
    with pytest.raises(ValueError):
        raw.real.setflags(write=True)


def test_negative_im_header(tmp_path):
    a = load_spectrum(write_data(tmp_path/"a.csv"))
    b = load_spectrum(write_data(tmp_path/"b.csv", header="f;Z';-Z''", sign=1))
    np.testing.assert_array_equal(a.impedance, b.impedance)
    assert b.imaginary_original[0] == 1
    assert b.info.im_multiplier == -1


def test_ambiguous_positive_sign(tmp_path):
    path = write_data(tmp_path/"test.csv", sign=1)
    with pytest.raises(SignAmbiguity):
        load_spectrum(path)
    assert load_spectrum(path, im_multiplier=-1).impedance[0].imag < 0


@pytest.mark.parametrize("bad", ["nan", "inf", "oops"])
def test_bad_row(tmp_path, bad):
    path = write_data(tmp_path/"test.csv")
    text = path.read_text(encoding="utf-8").replace("12,3", bad, 1)
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ImportErrorDetail):
        load_spectrum(path)


def test_duplicates_and_negative_frequency(tmp_path):
    path = tmp_path/"bad.txt"
    for f in ("1", "-1", "0"):
        path.write_text("f;Re;Im\n"+"\n".join(f"{f};2;-3" for _ in range(10)))
        with pytest.raises(ImportErrorDetail):
            load_spectrum(path)


def test_ambiguous_columns(tmp_path):
    path = tmp_path/"bad.csv"
    path.write_text("f;Frequency;Re;Im\n1;2;3;-4")
    with pytest.raises(ImportErrorDetail):
        load_spectrum(path)


def test_xlsx(tmp_path):
    from openpyxl import Workbook
    path = tmp_path/"test.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.append(["Frequency", "Zre", "Zim"])
    for i in range(10):
        ws.append([10**i, 3., -i-1.])
    wb.save(path)
    raw = load_spectrum(path)
    assert len(raw.frequency) == 10
    assert raw.info.sheet == "Sheet"


@pytest.mark.parametrize("header", ["f Re Im", "Frequency (Hz) Re (Ohm) Im (Ohm)", "f/Hz Re(Z)/Ohm Im(Z)/Ohm"])
def test_single_space_and_unit_suffixes(tmp_path, header):
    path = tmp_path/"space.txt"
    path.write_text(header+"\n"+"\n".join(f"{i+1} 3 -4" for i in range(10)))
    raw = load_spectrum(path)
    assert raw.frequency[0] == 1
    assert raw.impedance[0] == 3-4j


def test_real_examples():
    files = list(Path("data_test").glob("*.txt"))
    assert len(files) == 35
    for path in files:
        try:
            raw = load_spectrum(path)
        except SignAmbiguity:
            raw = load_spectrum(path, im_multiplier=-1)  # explicitly asserted for legacy examples
        assert len(raw.frequency) >= 8
        assert np.isfinite(raw.impedance).all()
