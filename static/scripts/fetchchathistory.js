function fetchChatHistory() {
    fetch('/get_chat_history')
        .then(response => response.json())
        .then(data => {
            const username = data.username || 'Unknown';

            const chatHistoryDiv = document.getElementById('chat-history');
            data.chat_history.forEach(msgObj => {
                const p = document.createElement('p');
                
                if(msgObj.role === 'user') {
                    p.textContent = username + ": " + msgObj.content;
                    p.className = 'message user-message';
                }
                else if(msgObj.role === 'assistant'){
                    p.textContent = "FitTrack-GPT: " + msgObj.content.content;
                    p.className = 'message assistant-message';
                }
                chatHistoryDiv.appendChild(p);
                chatHistoryDiv.scrollTop = chatHistoryDiv.scrollHeight;

            });
        })
        .catch((error) => {
            console.error('Error:', error);
        });
}

// Event handler for window load
window.onload = function() {
    fetchChatHistory();
};