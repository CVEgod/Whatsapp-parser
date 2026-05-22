#!/usr/bin/env python3

from __future__ import annotations
import argparse
import re
import sys
import time
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

try:
    import requests
    from bs4 import BeautifulSoup
except ModuleNotFoundError as e:
    import sys

    print(
        f"Module not installed: {e.name}\n"
        f"Python: {sys.executable}\n\n"
        "Install dependencies in THIS same Python:\n"
        f'  "{sys.executable}" -m pip install -r requirements.txt\n\n'
        "On Windows also: install.bat  then  run.bat",
        file=sys.stderr,
    )
    sys.exit(1)

DEFAULT_SITES = Path("sites.txt")
DEFAULT_OUTPUT = Path("whatsapp_numbers.txt")
DEFAULT_TIMEOUT = 30
DEFAULT_RETRIES = 3
CONNECT_TIMEOUT = 15

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# E.164: 8 to 15 digits (without +)
MIN_PHONE_DIGITS = 8
MAX_PHONE_DIGITS = 15

# International format in visible text — "+" required
INTL_TEXT_PHONE_RE = re.compile(
    r"(?<!\d)\+"
    r"[1-9]\d{0,2}[\s\-().]*"
    r"(?:\(?\d{1,4}\)?[\s\-().]*)?"
    r"\d{2,4}[\s\-().]*\d{2,4}[\s\-().]*\d{2,4}"
    r"(?!\d)",
)

# Russia in text: +7... or 8...
RU_TEXT_PHONE_RE = re.compile(
    r"(?<!\d)"
    r"(?:\+7|8)[\s\-().]*"
    r"(?:\(?\d{3}\)?[\s\-().]*)?"
    r"\d{3}[\s\-().]*\d{2}[\s\-().]*\d{2}"
    r"(?!\d)",
)

RU_MOBILE_RE = re.compile(r"^7[3-9]\d{9}$")
RU_TOLLFREE_RE = re.compile(r"^7800\d{7}$|^78\d{9}$")


def is_valid_phone(digits: str) -> bool:
    if not digits.isdigit():
        return False
    n = len(digits)
    if n < MIN_PHONE_DIGITS or n > MAX_PHONE_DIGITS:
        return False
    if digits[0] == "0":
        return False
    if len(set(digits)) <= 2:
        return False
    if n == 13:
        return False
    if n >= 11 and digits[:4] in ("2024", "2025", "2026", "2019", "1997"):
        return False
    if "36073607" in digits or digits.count("607") >= 3:
        return False

    if n == 11 and digits.startswith("7"):
        if digits.startswith(("70", "71")):
            return False
        return bool(RU_MOBILE_RE.match(digits) or RU_TOLLFREE_RE.match(digits))

    if n == 11 and digits.startswith("1"):
        return digits[1] not in "01" and digits[4] not in "01"

    if n == 12 and digits.startswith("91"):
        return digits[2] in "6789"

    if n == 12 and digits[:2] in ("44", "49", "33", "39", "34", "86", "55", "52"):
        return True

    if n == 12 and digits[:3] in ("380", "375", "371", "370"):
        return True

    if n == 10:
        return False

    if n == 12 and digits[:2] in ("77", "78", "50", "66", "54", "23", "61"):
        return False

    return 8 <= n <= 15


def normalize_phone(raw: str) -> str | None:
    raw = raw.strip()
    if raw.startswith("00"):
        raw = "+" + raw[2:]
    digits = re.sub(r"\D", "", raw)
    if not digits:
        return None

    had_plus = "+" in raw

    if len(digits) == 11 and digits.startswith("8"):
        digits = "7" + digits[1:]
    elif len(digits) == 10 and digits[0] == "9" and not had_plus:
        digits = "7" + digits

    if not is_valid_phone(digits):
        return None
    return f"+{digits}"


def extract_from_whatsapp_url(url: str) -> str | None:
    url = unquote(url.strip().rstrip(".,;)]}\"'"))
    lower = url.lower()

    if lower.startswith("whatsapp://"):
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        if "phone" in qs:
            return normalize_phone(qs["phone"][0])
        return None

    parsed = urlparse(url if "://" in url else "https://" + url)
    host = (parsed.netloc or "").lower()
    path = parsed.path.strip("/")

    if "wa.me" in host or "api.whatsapp.com" in host or "web.whatsapp.com" in host:
        qs = parse_qs(parsed.query)
        if "phone" in qs:
            return normalize_phone(qs["phone"][0])
        if path:
            first = path.split("/")[0].split("?")[0].lstrip("+")
            if first.isdigit() and 8 <= len(first) <= 15:
                return normalize_phone(first)

    return None


def _add_phone(found: set[str], raw: str | None) -> None:
    if raw:
        found.add(raw)


def extract_phones_from_html(html: str) -> set[str]:
    found: set[str] = set()
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup.find_all(["a", "link"], href=True):
        href = tag["href"]
        lower = href.lower()
        if "whatsapp" in lower or "wa.me" in lower:
            _add_phone(found, extract_from_whatsapp_url(href))
        elif lower.startswith("tel:"):
            _add_phone(found, normalize_phone(href[4:]))

    for tag in soup.find_all(attrs={"data-href": True}):
        val = tag.get("data-href", "")
        if "whatsapp" in val.lower() or "wa.me" in val.lower():
            _add_phone(found, extract_from_whatsapp_url(val))

    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()

    visible = soup.get_text(" ", strip=True)
    for match in RU_TEXT_PHONE_RE.findall(visible):
        _add_phone(found, normalize_phone(match))
    for match in INTL_TEXT_PHONE_RE.findall(visible):
        _add_phone(found, normalize_phone(match))

    return found


def load_sites(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    sites: list[str] = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if not line.startswith(("http://", "https://")):
            line = "https://" + line
        sites.append(line)
    return sites


def fetch_html(url: str, timeout: int, retries: int) -> str | None:
    read_timeout = max(timeout, 20)
    last_err: requests.RequestException | None = None

    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(
                url,
                timeout=(CONNECT_TIMEOUT, read_timeout),
                headers={"User-Agent": USER_AGENT},
                allow_redirects=True,
            )
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding or "utf-8"
            return resp.text
        except requests.RequestException as e:
            last_err = e
            if attempt < retries:
                wait = attempt * 2
                print(
                    f"  [!] attempt {attempt}/{retries}: {e} — retry in {wait} s",
                    file=sys.stderr,
                )
                time.sleep(wait)

    print(f"  [!] Request error: {last_err}", file=sys.stderr)
    return None


def country_codes_summary(numbers: set[str]) -> dict[str, int]:
    known = (
        "998", "996", "995", "994", "993", "992", "991", "980",
        "972", "971", "970", "968", "967", "966", "965", "964", "963", "962", "961", "960",
        "95", "94", "93", "92", "91", "90",
        "86", "84", "82", "81", "66", "65", "64", "63", "62", "61", "60",
        "58", "57", "56", "55", "54", "53", "52", "51",
        "49", "48", "47", "46", "45", "44", "43", "41", "40", "39", "38", "37", "36", "34", "33", "32", "31", "30",
        "27", "20",
        "7", "1",
    )
    counts: dict[str, int] = {}
    for num in numbers:
        body = num[1:]
        code = ""
        for length in (3, 2, 1):
            prefix = body[:length]
            if prefix in known:
                code = f"+{prefix}"
                break
        if not code:
            code = f"+{body[:1]}"
        counts[code] = counts.get(code, 0) + 1
    return dict(sorted(counts.items(), key=lambda x: (-x[1], x[0])))


def parse_site(url: str, timeout: int, retries: int, delay: float) -> set[str]:
    print(f"[*] {url}")
    html = fetch_html(url, timeout, retries)
    if html is None:
        return set()
    phones = extract_phones_from_html(html)
    codes = country_codes_summary(phones)
    codes_str = ", ".join(f"{k}×{v}" for k, v in codes.items()) if codes else "—"
    print(f"    found: {len(phones)} ({codes_str})")
    if delay > 0:
        time.sleep(delay)
    return phones


def save_numbers(path: Path, numbers: set[str], append: bool) -> None:
    sorted_nums = sorted(numbers)
    mode = "a" if append and path.exists() else "w"
    with path.open(mode, encoding="utf-8") as f:
        if mode == "a" and path.stat().st_size > 0:
            f.write("\n")
        for num in sorted_nums:
            f.write(num + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="WhatsApp number parser for websites (sites.txt -> whatsapp_numbers.txt)"
    )
    ap.add_argument(
        "-i", "--input",
        type=Path,
        default=DEFAULT_SITES,
        help=f"Input file with site list (default: {DEFAULT_SITES})",
    )
    ap.add_argument(
        "-o", "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output file for numbers (default: {DEFAULT_OUTPUT})",
    )
    ap.add_argument(
        "-t", "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help="Response read timeout in seconds (connect=15 s)",
    )
    ap.add_argument(
        "-r", "--retries",
        type=int,
        default=DEFAULT_RETRIES,
        help="Retries on request error/timeout",
    )
    ap.add_argument(
        "-d", "--delay",
        type=float,
        default=1.0,
        help="Pause between requests in seconds",
    )
    ap.add_argument(
        "--append",
        action="store_true",
        help="Append numbers to the end of the output file",
    )
    args = ap.parse_args()

    if not args.input.exists():
        print(f"File not found: {args.input}", file=sys.stderr)
        print("Create sites.txt and add one URL per line.")
        return 1

    sites = load_sites(args.input)
    if not sites:
        print(f"No sites in {args.input}.", file=sys.stderr)
        return 1

    print(f"Sites: {len(sites)}")
    all_phones: set[str] = set()

    for url in sites:
        all_phones |= parse_site(url, args.timeout, args.retries, args.delay)

    if not all_phones:
        print("No numbers found.")
        return 0

    save_numbers(args.output, all_phones, args.append)
    summary = country_codes_summary(all_phones)
    print(f"\nSaved {len(all_phones)} numbers -> {args.output}")
    print("Country codes:", ", ".join(f"{k} — {v}" for k, v in summary.items()))
    if set(summary) == {"+7"}:
        print(
            "(only +7: sites.txt currently has Russian sites — no other codes there; "
            "add foreign contact pages for +1, +91, +44 …)"
        )
    for num in sorted(all_phones):
        print(f"  {num}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
