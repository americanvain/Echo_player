
import base64
import json
import os

import requests
from ollama import Client

from utility import get_pdf_page_count, get_pdf_page_image

try:
    import config as _config
except ImportError:
    try:
        from . import config as _config
    except ImportError:
        _config = None

OLLAMA_BASE_URL = getattr(_config, "OLLAMA_BASE_URL", "") if _config else ""
OLLAMA_TOKEN = getattr(_config, "OLLAMA_TOKEN", "") if _config else ""


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

            model = model or "llava"
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
