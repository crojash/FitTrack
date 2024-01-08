function toggleChat() {
    const chatContainer = document.querySelector('.chat-container');
    const minimizeButton = document.getElementById('minimize-button');

    if (isChatMinimized) {
        chatContainer.style.height = 'auto';
        isChatMinimized = false;
        minimizeButton.innerHTML = '<i class="fas fa-window-minimize"></i>';
    } else {
        chatContainer.style.height = '50px';
        isChatMinimized = true;
        minimizeButton.innerHTML = '<i class="fas fa-window-maximize"></i>';
    }
}