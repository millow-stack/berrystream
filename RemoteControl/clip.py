data_uri = """data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAMklEQVR4AWTKwQkAMAgEQU1/6Sk9WaC5fQiiwj4c7ti+nJjaeMcHKCtkAUYh4DzqqvgAAAD"""

import base64
from io import BytesIO
from PIL import Image
import win32clipboard
import win32con
import re


def image_from_data_uri(data_uri: str) -> Image.Image:
    data_uri = data_uri.strip()
    data_uri = re.sub(r"\s+", "", data_uri)
    header, encoded = data_uri.split(",", 1)
    missing_padding = len(encoded) % 4
    if missing_padding:
        encoded += "=" * (4 - missing_padding)
    img_bytes = base64.b64decode(encoded)
    return Image.open(BytesIO(img_bytes))


def copy_pil_to_clipboard(img: Image.Image):
    output = BytesIO()
    img = img.convert("RGB")
    img.save(output, "BMP")

    bmp_data = output.getvalue()
    output.close()

    dib = bmp_data[14:]

    win32clipboard.OpenClipboard()
    try:
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32con.CF_DIB, dib)
    finally:
        win32clipboard.CloseClipboard()


def copy_data_uri_image_to_clipboard(data_uri: str):
    img = image_from_data_uri(data_uri)
    copy_pil_to_clipboard(img)

if __name__ == "__main__":
    copy_data_uri_image_to_clipboard(data_uri)
    print("Image copied to clipboard.")