
// Function to fetch chat history and populate in the chat container
function fetchChatHistory() {
    fetch('/get_chat_history')
        .then(response => response.json())
        .then(data => {
            const username = data.username || 'Unknown';
            const chatHistoryDiv = document.getElementById('chat-history');
            data.chat_history.forEach(msgObj => {
                const p = document.createElement('p');
                if (msgObj.role === 'user') {
                    p.textContent = username + ": " + msgObj.content;
                    p.className = 'message user-message';
                } else if (msgObj.role === 'assistant') {
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

let totalCalories = 0;

function addCalories() {
    console.log("addCalories function is triggered");
    const foodItem = document.getElementById('food-item').value;
    const calories = parseInt(document.getElementById('calories').value);
    if (!foodItem || isNaN(calories)) {
        alert("Please enter a valid food item and calorie amount.");
        return;
    }
    totalCalories += calories;
    document.getElementById('total-calories').textContent = totalCalories;
    // Clear the input fields
    document.getElementById('food-item').value = '';
    document.getElementById('calories').value = '';
}

function openMenu() {
    document.getElementById("rightMenu").style.width = "250px";
}

function closeMenu() {
    document.getElementById("rightMenu").style.width = "0";
}

// Optional: Handle form submission (you can replace this with your own logic)
document.getElementById("userForm").addEventListener("submit", function(event) {
    event.preventDefault();
    const formData = new FormData(event.target);
    const weight = formData.get("weight");
    const height = formData.get("height");
    const goal = formData.get("goal");
    console.log(`Weight: ${weight}, Height: ${height}, Goal: ${goal}`);
    closeMenu(); // This will close the menu when Submit is clicked
});

let isChatMinimized = false;

function toggleChat() {
    const chatContainer = document.querySelector('.chat-container');
    const minimizeButton = document.getElementById('minimize-button');
    console.log(isChatMinimized);  // Add this line

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

const apiKey = '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';
let lastMessageSentTime = 0;

// Function to add user messages to the chat history
function addUserMessage(message) {
    const chatHistoryDiv = document.getElementById('chat-history');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message user-message';
    messageDiv.innerHTML = `<strong>You:</strong><p>${message}</p>`;
    chatHistoryDiv.appendChild(messageDiv);
    chatHistoryDiv.scrollTop = chatHistoryDiv.scrollHeight; // Automatically scroll to the bottom
}

// Function to handle Enter key press in the chat input field
document.getElementById('user-message').addEventListener('keyup', function(event) {
    if (event.key === 'Enter') {
        sendMessage();
    }
});

function capitalizeFirstLetter(string) {
    return string.charAt(0).toUpperCase() + string.slice(1);
}

async function sendMessage() {
    const userMessage = document.getElementById('user-message').value;
    if (!userMessage.trim()) {
        alert("Please enter a message before sending.");
        return;
    }
    const currentTime = Date.now();
    if (currentTime - lastMessageSentTime < 10000) {
        alert("You can only send one message every 10 seconds.");
        return;
    }
    // Show loading animation while processing
    const loading = document.getElementById('loading');
    loading.style.display = 'flex';
    // Add user message to chat history
    addUserMessage(userMessage);
    // Send the message to your fine-tuned model
    const response = await fetch('/chat', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${apiKey}`,
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            user_message: userMessage
        })
    });
    // Hide loading animation after response is received
    loading.style.display = 'none';
    const data = await response.json();
    const assistantResponse = data.assistant_response;
    // Create a new message div and apply the appropriate class based on role
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${assistantResponse.role}-message`;
    messageDiv.innerHTML = `<strong>FitTrack-GPT:</strong><p>${assistantResponse.content}</p>`;
    // Append the message to the chat history
    document.getElementById('chat-history').appendChild(messageDiv);
    // Scroll to the bottom of the chat history
    const chatHistoryDiv = document.getElementById('chat-history');
    chatHistoryDiv.scrollTop = chatHistoryDiv.scrollHeight;
    lastMessageSentTime = currentTime;
    // Clear user input
    document.getElementById('user-message').value = '';
}
function openMenu() {
    document.getElementById("rightMenu").style.width = "250px";
  }
  
  function closeMenu() {
    document.getElementById("rightMenu").style.width = "0";
  }