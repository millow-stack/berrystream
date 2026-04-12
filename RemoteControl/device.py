from flask import *
import xml.etree.ElementTree as ET
import time
import hashlib
import json
import os
import cv2
import numpy as np
import pyautogui
from PIL import ImageGrab
import tkinter as tk

app = Flask(__name__)
root = tk.Tk()
w = root.winfo_screenwidth()
h = root.winfo_screenheight()
temp = 0;
root.destroy()

sgn = lambda x: (x > 0) - (x < 0)

def capture_screen():
    # Capture the screen
    screen = ImageGrab.grab()
    # Convert to NumPy array
    frame = np.array(screen)
    # Convert from RGB to BGR (OpenCV uses BGR format)
    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    return frame

def generate_frames():
    while True:
        frame = capture_screen()
        # Encode frame as JPEG
        ret, buffer = cv2.imencode('.jpg', frame)
        # Convert to bytes
        frame = buffer.tobytes()
        # Yield the frame in the required format
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

    h = ctypes.windll.kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE = -11
    csbi = CONSOLE_SCREEN_BUFFER_INFO()
    ctypes.windll.kernel32.GetConsoleScreenBufferInfo(h, ctypes.byref(csbi))
    return csbi.dwCursorPosition.Y + 1, csbi.dwCursorPosition.X + 1

@app.route('/', methods=['GET', 'POST', 'PUT', 'DELETE'])
def index():
    return render_template('index.html');

@app.route('/vidfeed')
def video_feed():
    # Return the response generated along with the specific media type (mime type)
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
   return redirect('http://millow-stack.github.io/alternate') 
   raise e

if __name__ == '__main__':
   app.run(host = '0.0.0.0', port = 80, debug = True, threaded = True)