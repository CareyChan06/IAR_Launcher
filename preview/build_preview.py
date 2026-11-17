import base64
import pathlib
import re
import sys

from fontTools import subset

ROOT = pathlib.Path(__file__).resolve().parent
SRC = ROOT / "iar-launcher-preview.html"
FONT_DIR = pathlib.Path(r"E:\CareyFiles\Download\HarmonyOS Sans\HarmonyOS_Sans_SC")
WEIGHTS = [(400, "HarmonyOS_Sans_SC_Regular.ttf"), (500, "HarmonyOS_Sans_SC_Medium.ttf"), (700, "HarmonyOS_Sans_SC_Bold.ttf")]
PLACEHOLDER = "/*__FONT_FACE__*/"


def collect_chars(html: str) -> str:
    chars = set(chr(i) for i in range(0x20, 0x7F))
    chars.update(html)
    chars.update("“”‘’·—…×÷≥≤→←↑↓√°±（）：；，。！？、《》【】")
    return "".join(sorted(c for c in chars if c.strip() or c == " "))


def font_face_css(text: str) -> str:
    css = []
    for weight, filename in WEIGHTS:
        source = FONT_DIR / filename
        if not source.exists():
            print(f"missing font: {source}", file=sys.stderr)
            continue
        options = subset.Options()
        options.flavor = "woff2"
        options.layout_features = ["*"]
        options.desubroutinize = True
        font = subset.load_font(str(source), options)
        subsetter = subset.Subsetter(options)
        subsetter.populate(text=text)
        subsetter.subset(font)
        data = font.flavor  # ensure flavor set
        import io
        buf = io.BytesIO()
        font.flavor = "woff2"
        font.save(buf)
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        print(f"{filename}: {len(buf.getvalue()) / 1024:.1f} KB")
        css.append(
            "@font-face{font-family:'HarmonyOS Sans SC';"
            f"src:url(data:font/woff2;base64,{b64}) format('woff2');"
            f"font-weight:{weight};font-style:normal;font-display:swap;}}"
        )
    return "\n".join(css)


def main():
    html = SRC.read_text(encoding="utf-8")
    existing = re.compile(r"@font-face\{font-family:'HarmonyOS Sans SC';.*?\}", re.S)
    if PLACEHOLDER in html or existing.search(html):
        if PLACEHOLDER not in html:
            html = existing.sub('', html)
            html = html.replace('<style>', '<style>\n' + PLACEHOLDER, 1)
        print("subsetting fonts ...")
        css = font_face_css(collect_chars(html))
        html = html.replace(PLACEHOLDER, css)
    if 'src="icon.svg"' in html:
        icon = (ROOT / "icon.svg").read_bytes()
        uri = "data:image/svg+xml;base64," + base64.b64encode(icon).decode("ascii")
        html = html.replace('src="icon.svg"', f'src="{uri}"')
    SRC.write_text(html, encoding="utf-8")
    print(f"written {SRC} ({SRC.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
