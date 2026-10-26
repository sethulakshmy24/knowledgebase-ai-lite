
import ipaddress
import socket
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup


def validate_article_url(url: str) -> str:
    parsed = urlparse(url.strip())

    if parsed.scheme != "https" and parsed.scheme != "http":
        raise ValueError("Only HTTP and HTTPS article URLs are supported.")

    if not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Please provide a valid article URL.")

    hostname = parsed.hostname.lower()

    if hostname in {"localhost", "localhost.localdomain"} or hostname.endswith(".local"):
        raise ValueError("Local URLs are not allowed.")

    try:
        addresses = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise ValueError("Could not resolve the article website.") from exc

    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if not ip.is_global:
            raise ValueError("Private or local network URLs are not allowed.")

    return url.strip()


def extract_article_text(url: str) -> str:
    url = validate_article_url(url)

    with httpx.Client(
        timeout=15.0,
        follow_redirects=False,
        headers={"User-Agent": "KnowledgeBaseAI/1.0"},
    ) as client:
        response = client.get(url)
        response.raise_for_status()

    if "text/html" not in response.headers.get("content-type", "").lower():
        raise ValueError("The URL did not return an HTML article.")

    soup = BeautifulSoup(response.text, "html.parser")

    for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
        element.decompose()

    article = soup.find("article") or soup.find("main") or soup.body

    if article is None:
        raise ValueError("Could not find readable article content.")

    paragraphs = [
        element.get_text(" ", strip=True)
        for element in article.find_all(["p", "h1", "h2", "h3", "li"])
    ]

    text = "\n".join(paragraph for paragraph in paragraphs if paragraph)

    if len(text) < 100:
        raise ValueError(
            "Not enough readable text found. The website may block extraction."
        )

    return text[:50000]
