# WhatsApp Parser

Parse phone numbers with WhatsApp links from web pages.

## How it works

```
sites.txt  → HTTP requests → HTML parsing → find wa.me / tel: / phone numbers → whatsapp_numbers.txt
```

## Setup

**Windows (recommended):** install Python once, then run:

```bat
install.bat
run.bat
```

Or manually:

```bat
py -3.13 -m pip install -r requirements.txt
py -3.13 parser.py
```

**Linux / macOS:**

```bash
python3 -m pip install -r requirements.txt
python3 parser.py
```

### Fix `No module named 'bs4'`

If you see errors like `No module named 'bs4'` / `already satisfied`, make sure you install dependencies with the same Python you use to run the script:

```bat
python -m pip install -r requirements.txt
```

Check which Python executable is used:

```bat
python -c "import sys; print(sys.executable)"
```

## Usage

1. Add URLs to `sites.txt` (one per line):

```
https://example.com
example.org
# comments are ignored
```

2. Run the parser:

```bat
run.bat
```

Or `py -3.13 parser.py` / `python parser.py` (ensure `python -m pip` installed dependencies for the same interpreter).

3. Output is written to `whatsapp_numbers.txt` in format `+E164`, e.g. `+79001234567`, `+14155551234`.

## Parameters

| Parameter | Description |
|----------|----------|
| `-i sites.txt` | Input file with sites/URLs |
| `-o whatsapp_numbers.txt` | Output file |
| `-t 15` | Request timeout (seconds) |
| `-d 1` | Delay between sites (seconds) |
| `--append` | Append to output instead of overwriting |

Example:

```bash
python parser.py -i my_sites.txt -o result.txt -d 2
```

## What it looks for

- Links in HTML: `wa.me`, `api.whatsapp.com`, `tel:`
- Phone numbers in **visible text** (excluding `script`/`style`)
- Phone number normalization: E.164 format with `+`, 8	6 digits; for Russia (RF) also supports `8 (9xx) ...` style numbers without the extra `+`

