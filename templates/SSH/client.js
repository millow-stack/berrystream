document.addEventListener("DOMContentLoaded", function() {
    const terminal = document.getElementById("terminal");
    const input = document.getElementById("input");

    const ws = new WebSocket("ws://localhost:8765");

    ws.onopen = function() {
        terminal.innerHTML += "Connected to the SSH server.<br>";
    };

    ws.onmessage = function(event) {
        terminal.innerHTML += event.data + "<br>";
        terminal.scrollTop = terminal.scrollHeight;
    };

    ws.onclose = function() {
        terminal.innerHTML += "Disconnected from the SSH server.<br>";
    };

    input.addEventListener("keydown", function(event) {
        if (event.key === "Enter") {
            const command = input.value;
            ws.send(command);
            input.value = "";
        }
    });
});
