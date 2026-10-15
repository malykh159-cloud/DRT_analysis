from pathlib import Path
import numpy as np
import pytest
from drt_analyzer.data.importers import load_spectrum
from drt_analyzer.data.column_detection import ImportErrorDetail, imaginary_sign


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


def test_automatic_positive_sign(tmp_path):
    path = write_data(tmp_path/"test.csv", sign=1)
    raw = load_spectrum(path)
    assert raw.impedance[0].imag < 0
    assert raw.info.im_multiplier == -1
    assert "majority" in raw.info.sign_evidence
    assert load_spectrum(path, im_multiplier=1).impedance[0].imag > 0


@pytest.mark.parametrize("header,values,expected", [
    ("Im", [-1, -2, 3, -4], 1), ("-Im", [-1, -2, 3, -4], 1),
    ("Im", [1, 2, -3, 4], -1), ("-Im", [1, 2, -3, 4], -1),
    ("Im", [0, 0, -1, 2], 1), ("-Im", [0, 0, -1, 2], -1),
    ("Im", [0, 0, 0, 1], -1), ("-Im", [0, 0, 0, 0], -1),
])
def test_sign_rule_and_ties(header, values, expected):
    assert imaginary_sign(header, np.asarray(values))[0] == expected


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
        raw = load_spectrum(path)
        assert len(raw.frequency) >= 8
        assert np.isfinite(raw.impedance).all()


@pytest.mark.parametrize("sep", ["\t", ";", ",", " "])
@pytest.mark.parametrize("encoding", ["utf-8-sig", "utf-16"])
@pytest.mark.parametrize("sign", [-1, 1])
def test_headerless_drttools(tmp_path, sep, encoding, sign):
    path = tmp_path/"drttools.txt"
    path.write_text("\n".join(sep.join([str(i+1), "12.3", str(sign*(i+1))]) for i in range(10)), encoding=encoding)
    before = path.read_bytes()
    raw = load_spectrum(path)
    assert raw.info.header_row == 0
    np.testing.assert_array_equal(raw.frequency, np.arange(1, 11))
    np.testing.assert_array_equal(raw.impedance.imag, -np.arange(1, 11))
    assert path.read_bytes() == before


def test_headerless_rejects_missing_or_extra_columns(tmp_path):
    path = tmp_path/"bad.txt"
    for row in ("2\t3", "2\t3\t-4\t5", "2\tbad\t-4"):
        path.write_text("1\t3\t-4\n"+row+"\n"+"\n".join(f"{i}\t3\t-4" for i in range(3, 11)))
        with pytest.raises(ImportErrorDetail):
            load_spectrum(path)
