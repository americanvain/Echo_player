
import base64
import json
import os

import requests
from ollama import Client

from utility import (
    fix_page_boundary,
    get_pdf_page_count,
    get_pdf_page_image,
    split_json_to_jsonl,
    split_text_with_isanlp_rst,
)

try:
    import config as _config
except ImportError:
    try:
        from . import config as _config
    except ImportError:
        _config = None

OLLAMA_BASE_URL = getattr(_config, "OLLAMA_BASE_URL", "") if _config else ""
OLLAMA_TOKEN = getattr(_config, "TOKEN", "") if _config else ""


class ollama_services:
    def __init__(self):
        self._client = Client(
            host=self._base_url() or "http://localhost:11434",
            headers=self._auth_headers(),
        )
        self._cache_root = os.path.join(os.path.dirname(__file__), "cache")

    def _auth_headers(self):
        token = os.getenv("OLLAMA_TOKEN", OLLAMA_TOKEN)
        if not token:
            return {}
        return {"Authorization": f"Bearer {token}"}

    def _base_url(self):
        return os.getenv("OLLAMA_BASE_URL", OLLAMA_BASE_URL).rstrip("/")

    def get_models(self):
        try:
            response = requests.get(
                f"{self._base_url()}/api/tags",
                headers=self._auth_headers(),
                timeout=200,
            )
            response.raise_for_status()
            data = response.json()
            return [model["name"] for model in data.get("models", [])]
        except requests.RequestException as exc:
            return [f"Error: {exc}"]
        

    def say_hello(self, select_model: str):
        if not select_model:
            return "No model selected."
        payload = {
            "model": select_model,
            "prompt": "Say hello!",
            "stream": False,
        }
        try:
            response = requests.post(
                f"{self._base_url()}/api/generate",
                json=payload,
                headers=self._auth_headers(),
                timeout=200,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("response", "No response")
        except requests.RequestException as exc:
            return f"Error: {exc}"

    def get_pdfimg_text(self, pdf_path: str, model: str | None = None):
        if not pdf_path:
            return "No PDF path."

        pdf_name = os.path.splitext(os.path.basename(pdf_path))[0] or "unknown"
        cache_dir = os.path.join(self._cache_root, pdf_name)
        os.makedirs(cache_dir, exist_ok=True)

        page_count = get_pdf_page_count(pdf_path)
        if isinstance(page_count, str):
            return page_count
        if page_count < 1:
            return "Invalid page count."

    # 找到第一个缺失或无效的页面
        start_page = 1
        for page_num in range(1, page_count + 1):
            text_path = os.path.join(cache_dir, f"page_{page_num}.json")
            if not os.path.exists(text_path):
                start_page = page_num
                break
            try:
                with open(text_path, "r", encoding="utf-8") as handle:
                    cached = json.load(handle)
                if not cached.get("text"):
                    start_page = page_num
                    break
            except Exception:
                start_page = page_num
                break

        for page_number in range(start_page, page_count + 1):
            text_path = os.path.join(cache_dir, f"page_{page_number}.json")
            image_path = os.path.join(cache_dir, f"page_{page_number}.png")
            if not os.path.exists(image_path):
                render_result = get_pdf_page_image(
                    pdf_path,
                    page_number,
                    self._cache_root,
                )
                if isinstance(render_result, str):
                    return render_result

            if not os.path.exists(image_path):
                return "Cached image not found."

            with open(image_path, "rb") as handle:
                image_payload = base64.b64encode(handle.read()).decode("ascii")

            try:
                response = self._client.chat(
                    model=model,
                    messages=[
                        {
                            "role": "user",
                            "content": "<image>\nFree OCR.",
                            "images": [image_payload],
                        }
                    ],
                )
                text = getattr(response, "message", None)
                text = getattr(text, "content", "") if text else ""
                with open(text_path, "w", encoding="utf-8") as handle:
                    json.dump({"text": text}, handle, ensure_ascii=False)
            except Exception as exc:
                return f"Error: {exc}"

        return "ok"

    def split_cache_json_to_jsonl(self, threshold: float | None = None):
        cache_root = self._cache_root
        fixed_suffix = ".fixed.jsonl"

        def _page_number(filename: str) -> int | None:
            if not filename.startswith("page_"):
                return None
            stem = os.path.splitext(filename)[0]
            try:
                return int(stem.split("_", 1)[1])
            except (IndexError, ValueError):
                return None

        def _page_paths(dirpath: str, page_num: int) -> tuple[str | None, str | None]:
            jsonl_path = os.path.join(dirpath, f"page_{page_num}.jsonl")
            fixed_path = os.path.join(dirpath, f"page_{page_num}{fixed_suffix}")
            return (jsonl_path if os.path.exists(jsonl_path) else None,
                    fixed_path if os.path.exists(fixed_path) else None)

        for dirpath, _, filenames in os.walk(cache_root):
            json_files = [name for name in filenames if name.endswith(".json")]
            for name in json_files:
                input_path = os.path.join(dirpath, name)
                output_path = os.path.splitext(input_path)[0] + ".jsonl"
                fixed_path = os.path.splitext(input_path)[0] + fixed_suffix
                # Skip if already converted (either raw or fixed).
                if os.path.exists(output_path) or os.path.exists(fixed_path):
                    continue
                split_json_to_jsonl(input_path, threshold=threshold)

        for dirpath, _, filenames in os.walk(cache_root):
            # Build a page map across raw and fixed jsonl files.
            page_nums = set()
            for name in filenames:
                if name.endswith(".jsonl"):
                    page_num = _page_number(name)
                    if page_num is not None:
                        page_nums.add(page_num)

            if not page_nums:
                continue

            page_nums = sorted(page_nums)
            for page_num, next_num in zip(page_nums, page_nums[1:]):
                if next_num != page_num + 1:
                    continue

                prev_raw, prev_fixed = _page_paths(dirpath, page_num)
                next_raw, next_fixed = _page_paths(dirpath, next_num)

                # Skip if both sides are already fixed.
                if prev_fixed and next_fixed:
                    continue

                prev_path = prev_fixed or prev_raw
                next_path = next_fixed or next_raw
                if not prev_path or not next_path:
                    continue

                # Fix boundary for the available pair.
                fix_page_boundary(prev_path, next_path, threshold=threshold)

                # Mark any raw files in this pair as fixed.
                if prev_raw and not prev_fixed:
                    os.replace(prev_raw, os.path.splitext(prev_raw)[0] + fixed_suffix)
                if next_raw and not next_fixed:
                    os.replace(next_raw, os.path.splitext(next_raw)[0] + fixed_suffix)

    def split_long_sentences_in_jsonl(self,
                                      jsonl_path: str,
                                      min_length: int = 120,
                                      output_path: str | None = None,
                                      base_url: str | None = None,
                                      token: str | None = None) -> str:
        if not os.path.exists(jsonl_path):
            return f"File not found: {jsonl_path}"

        output_path = output_path or (os.path.splitext(jsonl_path)[0] + ".rst.jsonl")
        texts: list[str] = []
        changed = False

        with open(jsonl_path, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                item = json.loads(line)
                if not (isinstance(item, list) and len(item) >= 2):
                    continue
                text = item[1]
                if not isinstance(text, str):
                    continue
                if len(text) >= min_length:
                    segments = split_text_with_isanlp_rst(
                        text,
                        base_url=base_url,
                        token=token,
                    )
                    if segments:
                        texts.extend(segments)
                        changed = True
                        continue
                texts.append(text)

        if not texts:
            return f"No text segments found in {jsonl_path}"

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as handle:
            for idx, segment in enumerate(texts, start=1):
                handle.write(json.dumps([idx, segment], ensure_ascii=False))
                handle.write("\n")

        if not changed:
            return f"No long segments found; wrote {output_path}"
        return f"Split long segments and wrote {output_path}"
