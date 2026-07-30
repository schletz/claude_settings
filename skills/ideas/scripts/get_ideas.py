"""Print an RSS news feed as compact Markdown for an LLM's context window.

The output starts with the feed's title as a level-1 heading (``#``). Each
feed item follows as a level-2 heading (``##``) with the item's description
text (HTML stripped) below it. Advertisements are skipped because they carry
no news value.

Usage: ``python get_ideas.py <url>``. Exit code 0 on success, 1 on error.
"""

from __future__ import annotations

import argparse
import html
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET

# Matches any HTML tag so it can be removed from the description text.
_HTML_TAG = re.compile(r"<[^>]+>")
# Collapses runs of whitespace (including newlines) into a single space.
_WHITESPACE = re.compile(r"\s+")
# Titles of sponsored items, e.g. "Anzeige: 140W-Ladegerät ..." on golem.de.
_AD_TITLE = re.compile(r"^(anzeige|werbung|sponsored)\b", re.IGNORECASE)
# Seconds to wait for a feed server before giving up.
_TIMEOUT = 30


def strip_html(text: str) -> str:
    """Remove HTML markup and normalise whitespace in a feed text fragment.

    Feed descriptions often contain escaped HTML (e.g. ``&lt;a&gt;`` links or
    ``<img>`` tags). Entities are unescaped first, then tags are removed and
    whitespace is collapsed so the result is plain, readable text.

    :param text: Raw description text from the RSS feed.
    :return: Cleaned plain-text string.
    """
    if not text:
        return ""
    # Unescape twice: feeds frequently double-encode (e.g. ``&amp;lt;``).
    text = html.unescape(html.unescape(text))
    text = _HTML_TAG.sub(" ", text)
    return _WHITESPACE.sub(" ", text).strip()


def local_name(tag: str) -> str:
    """Return an XML tag's local name, stripping any ``{namespace}`` prefix.

    ``ElementTree`` prefixes tags with their namespace URI in Clark notation
    (e.g. ``{http://purl.org/rss/1.0/}item``). RSS 1.0/RDF feeds use a default
    namespace, so matching on the bare local name keeps both RSS 2.0 and
    RSS 1.0 feeds working.

    :param tag: The fully qualified element tag.
    :return: The local name without the namespace prefix.
    """
    return tag.rpartition("}")[2]


def find_child_text(element: ET.Element, name: str) -> str:
    """Return the text of ``element``'s first child with the given local name.

    :param element: The element to search (a channel or an item).
    :param name: The local tag name to look for (e.g. ``title``).
    :return: The child's text, or an empty string if no such child exists.
    """
    for child in element:
        if local_name(child.tag) == name:
            return child.text or ""
    return ""


def load_feed_bytes(url: str) -> bytes:
    """Download the raw feed bytes from an HTTP(S) URL.

    :param url: The ``http``/``https`` URL of the feed.
    :return: The raw XML bytes. The XML declaration's encoding is honoured by
        the parser later, so the bytes are returned undecoded.
    :raises urllib.error.URLError: If the URL cannot be retrieved.
    """
    # A User-Agent is set because some feed servers reject the default one.
    request = urllib.request.Request(url, headers={"User-Agent": "get_ideas/1.0"})
    with urllib.request.urlopen(request, timeout=_TIMEOUT) as response:
        return response.read()


def feed_to_markdown(xml_bytes: bytes, url: str) -> str:
    """Convert a single RSS feed into a Markdown string.

    :param xml_bytes: The raw RSS 1.0 or 2.0 document.
    :param url: The feed's URL, used as heading if the feed has no title.
    :return: Markdown text with a ``# feed title`` heading followed by one
        ``## item title`` section per news item.
    """
    # ``ET.fromstring`` parses the raw bytes and respects the declared encoding.
    root = ET.fromstring(xml_bytes)

    channel = next((e for e in root.iter() if local_name(e.tag) == "channel"), None)
    feed_title = strip_html(find_child_text(channel, "title")) if channel is not None else ""
    sections: list[str] = [f"# {feed_title or url}"]

    for item in root.iter():
        if local_name(item.tag) != "item":
            continue
        title = strip_html(find_child_text(item, "title"))
        if not title or _AD_TITLE.match(title):
            continue
        body = strip_html(find_child_text(item, "description"))
        sections.append(f"## {title}\n\n{body}" if body else f"## {title}")

    return "\n\n".join(sections)


def main(argv: list[str] | None = None) -> int:
    """Parse arguments, fetch the feed and print it as Markdown.

    :param argv: Optional argument list (defaults to ``sys.argv``).
    :return: Process exit code, 0 on success and 1 on error.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", help="http(s) URL of the RSS feed.")
    args = parser.parse_args(argv)

    try:
        markdown = feed_to_markdown(load_feed_bytes(args.url), args.url)
    except (OSError, ValueError, ET.ParseError) as error:
        # OSError covers URLError and timeouts, ValueError malformed URLs.
        print(f"Failed to read feed {args.url}: {error}", file=sys.stderr)
        return 1

    # Ensure UTF-8 output regardless of the console's default encoding.
    sys.stdout.reconfigure(encoding="utf-8")
    print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
