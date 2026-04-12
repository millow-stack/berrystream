#!/usr/bin/env python3
"""
mouse_ws_server.py
WebSocket server that accepts gesture JSON from a phone and performs mouse actions locally.

Usage:
    python mouse_ws_server.py --host 0.0.0.0 --port 8765

Security note:
This server accepts unauthenticated connections by default. Run only on a trusted network,
or add your own authentication if exposing it to untrusted networks.
"""

import asyncio
import json
import argparse
import time
from typing import Optional

# Try pyautogui first (gives absolute move/drag/scroll), otherwise fallback to pynput
try:
    import pyautogui
    HAS_PYAUTOGUI = True
    # pyautogui.FAILSAFE = False  # optionally disable
except Exception:
    HAS_PYAUTOGUI = False

try:
    from pynput.mouse import Controller as MouseController, Button as PynButton
    HAS_PYNPUT = True
except Exception:
    HAS_PYNPUT = False

import websockets

# Setup mouse wrapper that provides move_to(x,y), click(button), press(), release(), scroll(dx, dy)
class MouseBackend:
    def __init__(self):
        if HAS_PYAUTOGUI:
            self.mode = "pyautogui"
            self.screen_w, self.screen_h = pyautogui.size()
        elif HAS_PYNPUT:
            self.mode = "pynput"
            self.mouse = MouseController()
            # try get screen size in a cross-platform way
            try:
                import tkinter as tk
                root = tk.Tk()
                self.screen_w = root.winfo_screenwidth()
                self.screen_h = root.winfo_screenheight()
                root.destroy()
            except Exception:
                # fallback
                self.screen_w, self.screen_h = (1920, 1080)
        else:
            raise RuntimeError("Need either pyautogui or pynput installed")

        print(f"[server] mouse backend: {self.mode}, screen: {self.screen_w}x{self.screen_h}")

    def move_to(self, x: int, y: int, duration: float = 0.0):
        if self.mode == "pyautogui":
            # clamp
            x = max(0, min(self.screen_w - 1, int(x)))
            y = max(0, min(self.screen_h - 1, int(y)))
            if duration and duration > 0:
                pyautogui.moveTo(x, y, duration=duration)
            else:
                pyautogui.moveTo(x, y)
        else:
            # pynput's move is relative; compute delta from current position
            cur_x, cur_y = self.mouse.position
            dx = int(x - cur_x)
            dy = int(y - cur_y)
            self.mouse.move(dx, dy)

    def click(self, button: str = "left", clicks: int = 1):
        if self.mode == "pyautogui":
            pyautogui.click(button=button, clicks=clicks)
        else:
            btn = PynButton.left if button == "left" else PynButton.right
            for _ in range(clicks):
                self.mouse.click(btn)

    def press(self, button: str = "left"):
        if self.mode == "pyautogui":
            pyautogui.mouseDown(button=button)
        else:
            btn = PynButton.left if button == "left" else PynButton.right
            self.mouse.press(btn)

    def release(self, button: str = "left"):
        if self.mode == "pyautogui":
            pyautogui.mouseUp(button=button)
        else:
            btn = PynButton.left if button == "left" else PynButton.right
            self.mouse.release(btn)

    def drag_to(self, x: int, y: int, duration: float = 0.0, button: str = "left"):
        if self.mode == "pyautogui":
            pyautogui.dragTo(x, y, duration=duration, button=button)
        else:
            # simple implementation: move to by small steps while holding button
            btn = PynButton.left if button == "left" else PynButton.right
            self.mouse.press(btn)
            try:
                curx, cury = self.mouse.position
                steps = max(1, int(max(abs(x - curx), abs(y - cury)) / 10))
                for i in range(1, steps + 1):
                    nx = int(curx + (x - curx) * i / steps)
                    ny = int(cury + (y - cury) * i / steps)
                    dx = nx - self.mouse.position[0]
                    dy = ny - self.mouse.position[1]
                    self.mouse.move(dx, dy)
                    if duration:
                        time.sleep(duration / steps)
            finally:
                self.mouse.release(btn)

    def scroll(self, dx: int = 0, dy: int = 0):
        # pyautogui.scroll takes vertical amount; positive scrolls up
        if self.mode == "pyautogui":
            if dy:
                pyautogui.scroll(dy)
            if dx:
                # horizontal scroll not always supported by pyautogui; emulate by small vertical scrolls?
                pyautogui.hscroll(dx)
        else:
            # pynput provides scroll(dx, dy)
            self.mouse.scroll(dx, dy)

# Mapping helpers
def map_coords(client_x, client_y, client_w, client_h, server_w, server_h):
    # map normalized position
    sx = (client_x / client_w) * server_w
    sy = (client_y / client_h) * server_h
    return int(sx), int(sy)

# Gesture handling
class GestureHandler:
    def __init__(self, mouse_backend: MouseBackend):
        self.mb = mouse_backend
        self.client_w = None
        self.client_h = None
        self.dragging = False
        self.drag_button = "left"

    async def handle(self, msg: dict):
        typ = msg.get("type")
        if typ == "init":
            # client sends its screen dims so we can map coordinates
            self.client_w = msg.get("w")
            self.client_h = msg.get("h")
            print(f"[server] init from client: {self.client_w}x{self.client_h}")
            return {"status": "ok", "serverScreen": {"w": self.mb.screen_w, "h": self.mb.screen_h}}
        elif typ == "pointer":
            return await self._handle_pointer(msg)
        else:
            return {"error": "unknown message type"}

    async def _handle_pointer(self, msg: dict):
        if self.client_w is None or self.client_h is None:
            return {"error": "client dims unknown, send init first"}

        action = msg.get("action")
        x = msg.get("x")
        y = msg.get("y")
        button = msg.get("button", "left")
        # map coords
        sx, sy = map_coords(x, y, self.client_w, self.client_h, self.mb.screen_w, self.mb.screen_h)

        if action == "move":
            # move pointer (no click)
            # small smoothing can be done with duration
            self.mb.move_to(sx, sy, duration=0.0)
            return {"result": "moved", "to": [sx, sy]}
        elif action == "tap":
            self.mb.click(button=button, clicks=1)
            return {"result": "tapped"}
        elif action == "double_tap":
            self.mb.click(button=button, clicks=2)
            return {"result": "double"}
        elif action == "down":
            # start pressed (for drag)
            self.dragging = True
            self.drag_button = button
            self.mb.press(button=button)
            # optionally move to where pressed
            self.mb.move_to(sx, sy)
            return {"result": "press"}
        elif action == "up":
            if self.dragging:
                self.mb.release(button=self.drag_button)
                self.dragging = False
            else:
                # simple click release (safety)
                try:
                    self.mb.release(button=button)
                except Exception:
                    pass
            return {"result": "release"}
        elif action == "drag":
            # dragging movement while mouse down
            if not self.dragging:
                # press if not already
                self.dragging = True
                self.mb.press(button=button)
            # use drag_to for smooth dragging
            self.mb.drag_to(sx, sy, duration=0.0, button=button)
            return {"result": "dragging"}
        elif action == "right_click":
            self.mb.click(button="right", clicks=1)
            return {"result": "right"}
        elif action == "long_press":
            # treat as right click or click-and-hold depending on client intend
            self.mb.click(button=button, clicks=1)
            return {"result": "long_press"}
        elif action == "scroll":
            # msg should include dx, dy in "pixel" space of client; we'll map magnitude roughly by ratio
            dx = msg.get("dx", 0)
            dy = msg.get("dy", 0)
            # scale scroll amount based on server/client screen ratio
            vscale = max(0.2, self.mb.screen_h / (self.client_h or 1))
            sx_scroll = int(dx * vscale)
            sy_scroll = int(dy * vscale)
            # invert sign for typical scroll behaviour if needed
            self.mb.scroll(dx=0, dy= -sy_scroll)
            return {"result": "scrolled", "by": [sx_scroll, sy_scroll]}
        else:
            return {"error": "unknown pointer action"}

# WebSocket server
async def handler(websocket, path):
    print(f"[server] connection from {websocket.remote_address}")
    gh = GestureHandler(mouse)
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
            except Exception as e:
                await websocket.send(json.dumps({"error": "invalid json", "msg": str(e)}))
                continue

            resp = await gh.handle(data)
            await websocket.send(json.dumps(resp))
    except websockets.exceptions.ConnectionClosed:
        print("[server] connection closed")
    except Exception as e:
        print("[server] error:", e)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='0.0.0.0', help='host to bind (0.0.0.0 for network)')
    parser.add_argument('--port', default=8765, type=int)
    args = parser.parse_args()

    mouse = MouseBackend()
    start_server = websockets.serve(handler, args.host, args.port)
    print(f"[server] starting ws server on ws://{args.host}:{args.port}")
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()
