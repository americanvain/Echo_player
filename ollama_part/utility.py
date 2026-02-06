import json
import os
import subprocess
import tempfile
import time

import requests

try:
    import config as _config
except ImportError:
    try:
        from . import config as _config
    except ImportError:
        _config = None


def get_pdf_page_count(pdf_path: str):
    if not pdf_path:
        return "No PDF path."
    if not os.path.exists(pdf_path):
        return f"File not found: {pdf_path}"

    cmd = ["pdfinfo", pdf_path]
    try:
        result = subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except Exception as exc:
        return f"Error: {exc}"

    for line in result.stdout.splitlines():
        if line.startswith("Pages:"):
            try:
                return int(line.split(":", 1)[1].strip())
            except ValueError:
                return "Failed to parse page count."
    return "Failed to read page count."


def get_pdf_page_image(pdf_path: str, page_number: int, cache_root: str):
    if not pdf_path:
        return "No PDF path."
    if not os.path.exists(pdf_path):
        return f"File not found: {pdf_path}"
    if page_number < 1:
        return "Invalid page number."

    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0] or "unknown"
    cache_dir = os.path.join(cache_root, pdf_name)
    output_path = os.path.join(cache_dir, f"page_{page_number}.png")
    if os.path.exists(output_path):
        return None

    os.makedirs(cache_dir, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="echo_player_pdf_") as output_dir:
        cmd = [
            "pdftoppm",
            "-f",
            str(page_number),
            "-l",
            str(page_number),
            "-png",
            "-singlefile",
            pdf_path,
            os.path.join(output_dir, f"page_{page_number}"),
        ]
        try:
            subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except Exception as exc:
            return f"Error: {exc}"

        temp_path = os.path.join(output_dir, f"page_{page_number}.png")
        if not os.path.exists(temp_path):
            return "Failed to render page."
        with open(temp_path, "rb") as handle:
            image_bytes = handle.read()
        with open(output_path, "wb") as handle:
            handle.write(image_bytes)
        return None


def _write_jsonl(segments, output_path: str):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as handle:
        for idx, segment in enumerate(segments, start=1):
            handle.write(json.dumps([idx, segment], ensure_ascii=False))
            handle.write("\n")


def _read_jsonl_texts(path: str) -> list[str]:
    texts = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            if isinstance(item, list) and len(item) >= 2:
                texts.append(item[1])
    return texts


def split_text_with_wtpsplit(text: str,
                             threshold: float | None = None,
                             base_url: str | None = None,
                             token: str | None = None) -> list[str]:
    base_url = (
        base_url
        if base_url is not None
        else (getattr(_config, "WTPSPLIT_BASE_URL", "") if _config else "")
    )
    token = (
        token
        if token is not None
        else (getattr(_config, "TOKEN", "") if _config else "")
    )
    if not base_url:
        raise ValueError("WTPSPLIT_BASE_URL is empty; set it to the /split endpoint URL.")

    payload = {"texts": text}
    if threshold is not None:
        payload["threshold"] = float(threshold)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    max_retries = 3
    backoff_seconds = 1.0
    response = None
    for attempt in range(max_retries):
        response = requests.post(base_url, headers=headers, json=payload, timeout=60)
        if response.status_code != 503:
            break
        if attempt < max_retries - 1:
            time.sleep(backoff_seconds)
            backoff_seconds *= 2
    if response is None or response.status_code == 503:
        raise ValueError("WTPSPLIT request failed with 503 after retries.")
    try:
        payload = response.json()
    except ValueError as exc:
        raise ValueError(f"Invalid JSON response: {exc}") from exc

    segments_nested = payload.get("segments", [])
    return [seg for group in segments_nested for seg in group if seg]


def split_text_with_isanlp_rst(text: str,
                               base_url: str | None = None,
                               token: str | None = None) -> list[str]:
    base_url = (
        base_url
        if base_url is not None
        else (getattr(_config, "ISANLP_RST_URL", "") if _config else "")
    )
    token = (
        token
        if token is not None
        else (getattr(_config, "TOKEN", "") if _config else "")
    )
    if not base_url:
        raise ValueError("ISANLP_RST_URL is empty; set it to the isanlp rst endpoint URL.")

    payload = {"text": text}
    headers: dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    response = requests.post(base_url, json=payload, headers=headers, timeout=120)
    response.raise_for_status()
    try:
        data = response.json()
    except ValueError as exc:
        raise ValueError(f"Invalid JSON response: {exc}") from exc

    return [text[start:end + 1] for start, end in data]


def split_json_to_jsonl(input_path: str,
                        threshold: float | None = None,
                        base_url: str | None = None,
                        token: str | None = None) -> bool:
    with open(input_path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    text = data["text"]
    segments = split_text_with_wtpsplit(
        text,
        threshold=threshold,
        base_url=base_url,
        token=token,
    )
    output_path = os.path.splitext(input_path)[0] + ".jsonl"
    _write_jsonl(segments, output_path)
    return True


def fix_page_boundary(prev_jsonl_path: str,
                      next_jsonl_path: str,
                      threshold: float | None = None,
                      base_url: str | None = None,
                      token: str | None = None) -> None:
    prev_texts = _read_jsonl_texts(prev_jsonl_path)
    next_texts = _read_jsonl_texts(next_jsonl_path)
    if len(prev_texts) < 2 or len(next_texts) < 2:
        return None

    merged_texts = prev_texts[-2:] + next_texts[:2]
    combined_text = " ".join(merged_texts)
    segments = split_text_with_wtpsplit(
        combined_text,
        threshold=threshold,
        base_url=base_url,
        token=token,
    )
    if not segments:
        raise ValueError("No segments returned from wtpsplit.")
    if segments == merged_texts:
        return None

    updated_prev = prev_texts[:-2] + segments
    updated_next = next_texts[2:]
    _write_jsonl(updated_prev, prev_jsonl_path)
    _write_jsonl(updated_next, next_jsonl_path)
    return None
