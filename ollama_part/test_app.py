import argparse
import sys

from services import ollama_services
from utility import get_pdf_page_image


def main():
    parser = argparse.ArgumentParser(description="Test PDF image OCR flow.")
    parser.add_argument("pdf_path", help="Path to a PDF file.")
    parser.add_argument(
        "--model",
        default=None,
        help="Ollama model name for OCR (default: llava).",
    )
    args = parser.parse_args()

    service = ollama_services()
    result = service.get_pdfimg_text(args.pdf_path, model=args.model)
    if isinstance(result, str) and result.startswith("Error:"):
        print(f"get_pdfimg_text error: {result}")
        return 1

    print(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
