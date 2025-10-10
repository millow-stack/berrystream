import asyncio
import websockets
import subprocess

async def execute_command(command):
    process = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    return stdout.decode() + stderr.decode()

async def ssh_websocket_server(websocket, path):
    async for message in websocket:
        print(f"Received command: {message}")
        output = await execute_command(message)
        await websocket.send(output)

start_server = websockets.serve(ssh_websocket_server, "localhost", 8765)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
