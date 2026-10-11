"""Build the self-contained HTML pitch deck.

    python docs/deck/build_html.py   ->  docs/deck/SpecSure_SIH26108_Deck.html

Inlines the screenshots in img/ (resized, WebP) and the FontAwesome icons (html_icons.json, exported from
react-icons) into deck_template.html, so the result is one file that opens offline in any modern browser.
"""
import base64
import io
import json
import re
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
MAX_W = 1600


def img_uri(name: str) -> str:
    im = Image.open(HERE / "img" / f"{name}.png").convert("RGB")
    if im.width > MAX_W:
        im = im.resize((MAX_W, round(im.height * MAX_W / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "WEBP", quality=84, method=6)
    return "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode()


def main() -> None:
    html = (HERE / "deck_template.html").read_text(encoding="utf-8")
    icons = json.loads((HERE / "html_icons.json").read_text(encoding="utf-8"))
    cache: dict[str, str] = {}

    def sub_img(m: re.Match) -> str:
        n = m.group(1)
        if n not in cache:
            cache[n] = img_uri(n)
        return cache[n]

    html = re.sub(r"\{\{IMG:([\w]+)\}\}", sub_img, html)
    html = re.sub(r"\{\{IC:(\w+)\}\}", lambda m: icons[m.group(1)].replace(' height="1em" width="1em"', ' aria-hidden="true"'), html)
    left = re.findall(r"\{\{[A-Z]+:\w+\}\}", html)
    assert not left, left
    out = HERE / "SpecSure_SIH26108_Deck.html"
    out.write_text(html, encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size / 1e6:.2f} MB, {len(cache)} images)")


if __name__ == "__main__":
    main()
