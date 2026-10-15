import re
import unicodedata


class ImportErrorDetail(ValueError):
    pass


class SignAmbiguity(ImportErrorDetail):
    """Reserved for import modes without the capacitive-majority assumption."""


def normalized(text):
    return unicodedata.normalize("NFKC", str(text)).strip().lower().replace("−", "-").replace("′", "'")


def column_kind(header):
    s = normalized(header)
    s = re.sub(r"\([^)]*\)|\[[^]]*\]", "", s)
    s = re.sub(r"/\s*(?:hz|ohms?|ω|ом|гц)\b.*$", "", s)
    s = s.split(",")[0].strip()
    compact = re.sub(r"[\s_\-./]", "", s)
    if compact in {"f", "hz", "freq", "frequency", "frequencyhz", "freqhz", "частота"}:
        return "f"
    if compact in {"re", "zre", "rez", "real", "zreal", "realz", "z'", "z′"}:
        return "re"
    if compact in {"im", "zim", "imz", "imag", "imaginary", "zimag", "zimaginary", "z''", "z″"}:
        return "im"
    return None


def detect_columns(headers):
    result = {}
    for i, header in enumerate(headers):
        kind = column_kind(header)
        if kind:
            if kind in result:
                raise ImportErrorDetail(f"Ambiguous {kind} columns: {headers[result[kind]]!r}, {header!r}.")
            result[kind] = i
    if len(result) != 3:
        raise ImportErrorDetail("Cannot uniquely identify frequency, Re(Z), Im(Z). "
                                f"Headers: {list(headers)!r}. Use explicit column names.")
    return tuple(result[k] for k in ("f", "re", "im"))


def imaginary_sign(header, values, override=None):
    if override is not None:
        if override not in (-1, 1):
            raise ValueError("im_multiplier must be +1 or -1.")
        return override, "user-confirmed"
    # User's explicit domain assumption: spectra are predominantly capacitive.
    # Count signs of the original column BEFORE filtering any analysis window.
    import numpy as np
    positive, negative = int(np.count_nonzero(values > 0)), int(np.count_nonzero(values < 0))
    if positive != negative:
        multiplier = -1 if positive > negative else 1
        return multiplier, (f"automatic nonzero-sign majority: {positive} positive, {negative} negative; "
                            "predominantly capacitive spectra assumed; original header: " + str(header))
    multiplier = -1 if normalized(header).startswith("-") else 1
    return multiplier, (f"equal sign counts ({positive} positive, {negative} negative); header convention used")
