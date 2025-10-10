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

@app.route('/vidfeed')
def video_feed():
    # Return the response generated along with the specific media type (mime type)
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# @app.route('/')
# def index():
#     return render_template('index.html')

@app.route('/click', methods=['POST'])
def click():
    coordinates = request.get_json()
    pyautogui.click(x=w*coordinates['x'], y=h*coordinates['y'], button=request.args.get('act', 'middle'))
    return '', 200

@app.route('/scroll', methods=['POST'])
def scroll():
    lines = request.get_json()['x'];
    # pyautogui.moveTo(x=w*coordinates['x'], y=h*coordinates['y'])
    pyautogui.hscroll(lines)
    return '', 200

@app.route('/', defaults={'wair': 'roaming/'})
#add a folder roaming

@app.route('/<path:wair>')
def WatsIn(wair):
   laqt1 = [];
   laqt2 = [];
   if(os.path.exists(wair)):
      if(os.path.isdir(wair)):
         for i in os.listdir(wair):
            if(os.path.isfile(wair+i)):
               #laqt[0] += '<li><a href="'+wair+i+'">'+i+'</a></li>'
               laqt1.append(i)
            if(os.path.isdir(wair+i)):
               #laqt[1] += '<li><a href="'+wair+i+'/">'+i+'</a></li>'
               laqt2.append(i)
         # for root, directories, files in os.walk(wair, topdown=False, onerror=None, followlinks=False):
         #    for name in files:
         #       laqt += '<li><a href="?wair='+os.path.join(root, name)+'">'+name+'</a></li>';
         #    for name in directories:
         #       laqt += '<li><a href="?wair='+os.path.join(root, name)+'">'+name+'</a></li>';

         return render_template('index.html', files=laqt1, folders=laqt2, pth=wair)
      if(os.path.isfile(wair)):
         return send_file(wair)
   else:
      return abort(404)

@app.errorhandler(404) 
def not_found(e): 
   return redirect('http://millow-stack.github.io/alternate') 
   raise e

if __name__ == '__main__':
   app.run(host = '0.0.0.0', port = 80, debug = True, threaded = True)