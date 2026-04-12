from flask import *
from io import BytesIO
from PIL import Image
from PIL import ImageGrab
import base64
import cv2
import hashlib
import json
import numpy as np
import os
import pyautogui
import re
import time
import tkinter as tk
import win32clipboard
import win32con
import xml.etree.ElementTree as ET

app = Flask(__name__)
root = tk.Tk()
w = root.winfo_screenwidth()
h = root.winfo_screenheight()
temp = 0;
root.destroy()

sgn = lambda x: (x > 0) - (x < 0)

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

def capture_screen():
    screen = ImageGrab.grab()
    frame = np.array(screen)
    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    return frame

def generate_frames():
    while True:
        frame = capture_screen()
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


def get_cursor_pos_windows():
    class COORD(ctypes.Structure):
        _fields_ = [("X", ctypes.c_short), ("Y", ctypes.c_short)]

    class CONSOLE_SCREEN_BUFFER_INFO(ctypes.Structure):
        _fields_ = [
            ("dwSize", COORD),
            ("dwCursorPosition", COORD),
            ("wAttributes", ctypes.c_uint16),
            ("srWindow", ctypes.c_uint16 * 4),
            ("dwMaximumWindowSize", COORD)
        ]

    h = ctypes.windll.kernel32.GetStdHandle(-11)  
    csbi = CONSOLE_SCREEN_BUFFER_INFO()
    ctypes.windll.kernel32.GetConsoleScreenBufferInfo(h, ctypes.byref(csbi))
    return csbi.dwCursorPosition.Y + 1, csbi.dwCursorPosition.X + 1

@app.route('/', methods=['GET', 'POST', 'PUT', 'DELETE'])
def index():
    return render_template('index.public.html');

@app.route('/drawing', methods=['GET'])
def drawings():
    return render_template('drawing.html');

@app.route('/drawing', methods=['POST'])
def drawingr():
    copy_data_uri_image_to_clipboard(request.get_json()['uri']);
    return '', 200

@app.route('/vidfeed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame');

@app.route('/click', methods=['POST'])
def click():
    coordinates = request.get_json()
    pyautogui.click(x=w*coordinates['x'], y=h*coordinates['y'], button=request.args.get('act', 'middle'))
    print('Clicking at (%d, %d)', w*coordinates['x'], h*coordinates['y'])
    return '', 200

@app.route('/scroll', methods=['POST'])
def scroll():
    lines = int(request.get_json()['x']/5);
    columns = -int(request.get_json()['y']/5);
    pyautogui.hscroll(lines)
    pyautogui.vscroll(columns)
    print('Scrolling', lines, 'lines and ', columns, 'columns.')
    return '', 200

@app.route('/mouse', methods=['POST'])
def mouse():
    x = int(request.get_json()['y']);
    y = -int(request.get_json()['x']);
    pyautogui.move(sgn(x)*10, sgn(y)*10)
    print('Moving cursor through:', x, y)
    return '', 200

@app.errorhandler(404) 
def not_found(e): 
   return redirect('/alternate') 
   raise e

if __name__ == '__main__':
   app.run(host = '0.0.0.0', port = 80, debug = True, threaded = True)