const socket = io();

function sendMessage() {
    const input = document.getElementById('user-input');
    const command = input.value;
    input.value = '';
    const chatWindow = document.getElementById('messages');

    // Display user message
    chatWindow.innerHTML += `<div><strong>User:</strong> ${command}</div>`;

    // Send command to backend
    socket.emit('send_message', { command });

    // Listen for response
    socket.on('receive_message', (data) => {
        chatWindow.innerHTML += `<div><strong>Malcolm:</strong> ${data.response}</div>`;
    });
}

function uploadFile() {
    const fileInput = document.getElementById('file-input');
    const file = fileInput.files[0];
    const feedback = document.getElementById('upload-feedback');

    if (!file) {
        feedback.textContent = 'No file selected.';
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    fetch('/upload', {
        method: 'POST',
        body: formData,
    })
        .then(response => response.json())
        .then(data => {
            feedback.textContent = data.feedback;
        })
        .catch(error => {
            feedback.textContent = 'Error uploading file.';
            console.error('Error:', error);
        });
}
