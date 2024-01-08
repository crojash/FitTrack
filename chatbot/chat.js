const apiKey = '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';
        let lastMessageSentTime = 0;

        // Variable to track chat minimized state
        let isChatMinimized = false;

        // Function to toggle the chat container


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

            // Check if the user's query is related to generating a diet plan
        
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