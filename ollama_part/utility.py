import os
import subprocess
import tempfile


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
