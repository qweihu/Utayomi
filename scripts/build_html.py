#!/usr/bin/env python3
"""Render the final in-memory lyric pairs as a self-contained HTML page.

This module is a renderer used by ``utayomi.py``. It does not own file paths,
intermediate Markdown files, image export or a second command-line workflow.
"""

from __future__ import annotations

import html
import re


HEADER_RE = re.compile(r"^\*\*(?P<inner>.+)\*\*$")
LABEL_RE = re.compile(r"^歌曲\s*[:：]\s*(?P<content>.+)$")
ROMAJI_RT_RE = re.compile(r"<rt>[A-Za-zāīūēōâîûêô\s'’-]+</rt>")
ALLOWED_TAGS = ("ruby", "/ruby", "rt", "/rt", "rp", "/rp")
PAGE_PLACEHOLDER_RE = re.compile(r"__(LANG|TITLE|ARTIST|DOC_TITLE|PAIRS|SOURCE)__")

DEFAULT_TITLE = "Untitled Song"
DEFAULT_ARTIST = "Unknown Artist"

PAGE_TEMPLATE = """<!doctype html>
<html lang="__LANG__">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__DOC_TITLE__</title>
<style>
  :root {
    --ink: #1f2430; --muted: #6b7280; --accent: #2fb38b; --accent-2: #5b8def;
    --card: #ffffff; --pair-bg: #fbfcff; --line: #e5e7ef;
    --shadow: 0 10px 30px rgba(31, 36, 48, 0.08);
    --bg: linear-gradient(160deg, #f7f8fc 0%, #eef1f8 100%); --radius: 18px;
  }
  :root[data-theme="umi"] {
    --accent: #5b8def; --accent-2: #2fb38b;
    --bg: linear-gradient(160deg, #f5f8fd 0%, #e8effb 100%);
  }
  :root[data-theme="akane"] {
    --accent: #e25563; --accent-2: #e58a2f;
    --bg: linear-gradient(160deg, #fdf7f6 0%, #f9ecec 100%);
  }
  :root[data-theme="yoru"] {
    --ink: #e8eaf1; --muted: #9aa3b5; --accent: #8f7ff5; --accent-2: #5bb8e8;
    --card: #1d2230; --pair-bg: #232939; --line: #353d52;
    --shadow: 0 10px 30px rgba(0, 0, 0, 0.45);
    --bg: linear-gradient(160deg, #12151f 0%, #171b28 100%);
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  html, body { background: var(--bg); }
  body {
    font-family: "Hiragino Sans", "Hiragino Kaku Gothic ProN", "Yu Gothic UI",
      "PingFang SC", "Noto Sans CJK SC", "Microsoft YaHei", sans-serif;
    color: var(--ink); padding: 56px 24px 96px; -webkit-font-smoothing: antialiased;
  }
  .card {
    background: var(--card); border: 1px solid var(--line);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    padding: 36px 40px; margin: 0 auto; max-width: 860px;
  }
  .header {
    display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap;
    padding-bottom: 20px; margin-bottom: 24px; border-bottom: 1px solid var(--line);
  }
  .header .dot {
    width: 10px; height: 10px; border-radius: 50%; background: var(--accent);
    box-shadow: 0 0 0 4px color-mix(in srgb, var(--accent) 15%, transparent);
    align-self: center;
  }
  .header .title { font-size: 22px; font-weight: 700; letter-spacing: 0.02em; }
  .header .artist { font-size: 14px; color: var(--muted); }
  ruby { ruby-align: center; }
  rt { font-size: 0.55em; color: var(--accent); font-weight: 600; letter-spacing: 0.02em; }
  body.romaji rt { color: var(--accent-2); }
  .pair {
    border: 1px solid var(--line); border-radius: 14px;
    padding: 16px 20px; background: var(--pair-bg);
  }
  .pair + .pair { margin-top: 14px; }
  .pair .ja { font-size: 24px; font-weight: 600; line-height: 2.3; }
  .pair .translation { font-size: 15px; color: var(--muted); margin-top: 2px; }
  .footer {
    margin-top: 24px; padding-top: 14px; border-top: 1px solid var(--line);
    font-size: 12px; color: var(--muted); text-align: right; letter-spacing: 0.04em;
  }
  .footer .source { margin-left: 8px; }
  .section-break { height: 18px; }
  .toolbar {
    position: fixed; right: 24px; bottom: 24px; display: flex; gap: 10px; align-items: center;
  }
  .themes {
    display: flex; gap: 8px; padding: 8px 12px; border-radius: 999px;
    background: var(--card); border: 1px solid var(--line); box-shadow: var(--shadow);
  }
  .theme-dot {
    width: 20px; height: 20px; border-radius: 50%; border: none; cursor: pointer;
    background: var(--dot); padding: 0;
  }
  .theme-dot.active { box-shadow: 0 0 0 3px var(--card), 0 0 0 5px var(--dot); }
  .toolbar #export {
    border: none; border-radius: 999px; padding: 12px 22px;
    font-size: 14px; font-weight: 700; font-family: inherit; cursor: pointer;
    color: #fff; background: var(--accent);
    box-shadow: 0 8px 20px color-mix(in srgb, var(--accent) 35%, transparent);
  }
  .toolbar #export:hover { filter: brightness(1.06); }
  .toolbar #export:disabled { opacity: 0.6; cursor: wait; }
</style>
</head>
<body>
  <main class="card" id="card">
    <div class="header">
      <span class="dot"></span>
      <span class="title">__TITLE__</span>
      <span class="artist">__ARTIST__</span>
    </div>
__PAIRS__
    <div class="footer">Utayomi · Japanese lyrics<span class="source">__SOURCE__</span></div>
  </main>
  <div class="toolbar">
    <div class="themes" id="themes">
      <button class="theme-dot active" type="button" data-theme="matcha" style="--dot: #2fb38b" title="Matcha"></button>
      <button class="theme-dot" type="button" data-theme="umi" style="--dot: #5b8def" title="Umi"></button>
      <button class="theme-dot" type="button" data-theme="akane" style="--dot: #e25563" title="Akane"></button>
      <button class="theme-dot" type="button" data-theme="yoru" style="--dot: #8f7ff5" title="Yoru"></button>
    </div>
    <button id="export" type="button">Export PNG</button>
  </div>
<script>
(function () {
  var EXPORT_SCALE = 2;
  var THEME_STORAGE_KEY = "utayomi-theme";

  function applyTheme(theme) {
    var name = theme || "matcha";
    if (name === "matcha") {
      document.documentElement.removeAttribute("data-theme");
    } else {
      document.documentElement.setAttribute("data-theme", name);
    }
    var dots = document.querySelectorAll(".theme-dot");
    for (var i = 0; i < dots.length; i++) {
      dots[i].classList.toggle("active", dots[i].getAttribute("data-theme") === name);
    }
    try { localStorage.setItem(THEME_STORAGE_KEY, name); } catch (error) { /* file:// pages may forbid it */ }
  }

  document.getElementById("themes").addEventListener("click", function (event) {
    var dot = event.target.closest(".theme-dot");
    if (dot) { applyTheme(dot.getAttribute("data-theme")); }
  });
  try {
    var saved = localStorage.getItem(THEME_STORAGE_KEY);
    if (saved) { applyTheme(saved); }
  } catch (error) { /* fall back to the default theme */ }

  function inlineComputedStyles(source, target) {
    var sourceNodes = [source].concat(Array.prototype.slice.call(source.querySelectorAll("*")));
    var targetNodes = [target].concat(Array.prototype.slice.call(target.querySelectorAll("*")));
    sourceNodes.forEach(function (node, index) {
      var computed = getComputedStyle(node);
      var css = "";
      for (var i = 0; i < computed.length; i++) {
        var prop = computed[i];
        css += prop + ":" + computed.getPropertyValue(prop) + ";";
      }
      targetNodes[index].style.cssText = css;
    });
  }

  function downloadBlob(blob, filename) {
    var link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    setTimeout(function () { URL.revokeObjectURL(link.href); }, 1000);
  }

  function exportCard() {
    var button = document.getElementById("export");
    button.disabled = true;
    var card = document.getElementById("card");
    var rect = card.getBoundingClientRect();
    var width = Math.ceil(rect.width);
    var height = Math.ceil(rect.height);

    var wrapper = document.createElement("div");
    wrapper.setAttribute("xmlns", "http://www.w3.org/1999/xhtml");
    var clone = card.cloneNode(true);
    inlineComputedStyles(card, clone);
    clone.style.width = width + "px";
    clone.style.height = height + "px";
    clone.style.margin = "0";
    clone.style.maxWidth = "none";
    wrapper.appendChild(clone);

    var serialized = new XMLSerializer().serializeToString(wrapper);
    var svg = '<svg xmlns="http://www.w3.org/2000/svg" width="' + width + '" height="' + height + '">' +
      '<foreignObject x="0" y="0" width="' + width + '" height="' + height + '">' +
      serialized + "</foreignObject></svg>";
    var url = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg);

    var image = new Image();
    image.onload = function () {
      var canvas = document.createElement("canvas");
      canvas.width = width * EXPORT_SCALE;
      canvas.height = height * EXPORT_SCALE;
      var context = canvas.getContext("2d");
      context.scale(EXPORT_SCALE, EXPORT_SCALE);
      context.drawImage(image, 0, 0);
      canvas.toBlob(function (blob) {
        button.disabled = false;
        if (blob) {
          downloadBlob(blob, document.title.replace(/[\\/:*?"<>|]/g, "_") + ".png");
        } else {
          alert("Export failed: this browser cannot encode the canvas");
        }
      }, "image/png");
    };
    image.onerror = function () {
      button.disabled = false;
      alert("Export failed: this browser cannot render the SVG snapshot");
    };
    image.src = url;
  }

  document.getElementById("export").addEventListener("click", exportCard);
})();
</script>
</body>
</html>
"""


def sanitize_lyric(text: str) -> str:
    """Escape everything, then restore the allowed ruby annotation tags."""
    escaped = html.escape(text.strip(), quote=False)
    for tag in ALLOWED_TAGS:
        escaped = escaped.replace(f"&lt;{tag}&gt;", f"<{tag}>")
    return escaped


def parse_markdown(text: str) -> tuple[str, str, list[tuple[str, str]]]:
    """Split the final Markdown into (title, artist, [(ja, zh), ...])."""
    lines = text.splitlines()
    title, artist = DEFAULT_TITLE, DEFAULT_ARTIST
    body = lines
    if lines:
        header = HEADER_RE.match(lines[0].strip())
        if header:
            inner = header.group("inner")
            label = LABEL_RE.match(inner)
            content = label.group("content") if label else inner
            parts = re.split(r"\s*/\s*", content, maxsplit=1)
            title = parts[0].strip() or DEFAULT_TITLE
            artist = parts[1].strip() if len(parts) > 1 else ""
            body = lines[1:]

    pairs: list[tuple[str, str]] = []
    group: list[str] = []
    for line in body + [""]:
        if line.strip():
            group.append(line)
            continue
        if group:
            ja = group[0]
            zh = group[1] if len(group) > 1 else ""
            pairs.append((ja, zh))
            group = []
    return title, artist, pairs


def is_romaji(pairs: list[tuple[str, str]]) -> bool:
    joined = "\n".join(ja for ja, _ in pairs)
    readings = ROMAJI_RT_RE.findall(joined)
    return bool(readings) and len(readings) >= joined.count("<rt>") / 2


def build_html(
    title: str,
    artist: str,
    pairs: list[tuple[str, str]],
    *,
    language: str = "und",
    source: str | None = None,
) -> str:
    pair_blocks = []
    for ja, zh in pairs:
        if not ja.strip() and not zh.strip():
            pair_blocks.append('    <div class="section-break" aria-hidden="true"></div>')
            continue
        translation_line = (
            f'      <div class="translation">'
            f'{html.escape(zh.strip(), quote=False)}</div>\n'
            if zh.strip()
            else ""
        )
        pair_blocks.append(
            '    <div class="pair">\n'
            f'      <div class="ja">{sanitize_lyric(ja)}</div>\n'
            f"{translation_line}"
            "    </div>"
        )
    replacements = {
        "LANG": html.escape(language or "und", quote=True),
        "TITLE": html.escape(title, quote=False),
        "ARTIST": html.escape(artist, quote=False),
        "DOC_TITLE": html.escape(f"{title} / {artist}".rstrip(" /"), quote=False),
        "PAIRS": "\n".join(pair_blocks),
        "SOURCE": f"Source: {html.escape(source, quote=False)}" if source else "",
    }
    page = PAGE_PLACEHOLDER_RE.sub(
        lambda match: replacements[match.group(1)], PAGE_TEMPLATE
    )
    if is_romaji(pairs):
        page = page.replace("<body>", '<body class="romaji">', 1)
    return page + "\n"



def render_html_from_markdown(text: str, *, language: str = "und") -> str:
    """Render a final Markdown string to HTML without touching the filesystem."""

    if not text.strip():
        raise ValueError("不能从空的 Markdown 内容生成 HTML")
    title, artist, pairs = parse_markdown(text)
    if not pairs:
        raise ValueError("Markdown 中没有可排版的歌词内容")
    return build_html(title, artist, pairs, language=language)
