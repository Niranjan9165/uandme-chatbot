var chatHistory = [];

function handleKey(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

function sendSuggestion(text) {
    document.getElementById('userInput').value = text;
    sendMessage();
}

function addMessage(text, isUser) {
    var welcome = document.getElementById('welcome');
    if (welcome) welcome.style.display = 'none';

    var container = document.getElementById('chatContainer');
    var typing = document.getElementById('typing');

    var div = document.createElement('div');
    div.className = 'message ' + (isUser ? 'user-message' : 'ai-message');

    if (!isUser) {
        var sender = document.createElement('div');
        sender.className = 'sender';
        sender.textContent = 'U&Me AI';
        div.appendChild(sender);
    }

    var textNode = document.createElement('div');
    textNode.textContent = text;
    div.appendChild(textNode);

    container.insertBefore(div, typing);
    container.scrollTop = container.scrollHeight;
}

async function sendMessage() {
    var input = document.getElementById('userInput');
    var text = input.value.trim();

    if (!text) return;

    input.value = '';
    document.getElementById('sendBtn').disabled = true;

    addMessage(text, true);

    chatHistory.push({
        role: 'user',
        content: text
    });

    document.getElementById('typing').style.display = 'block';
    var container = document.getElementById('chatContainer');
    container.scrollTop = container.scrollHeight;

    try {
        var response = await fetch('https://uandme-chatbot.onrender.com/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: text,
                history: chatHistory.slice(-10)
            })
        });

        var data = await response.json();

        document.getElementById('typing').style.display = 'none';

        addMessage(data.reply, false);

        chatHistory.push({
            role: 'assistant',
            content: data.reply
        });

    } catch (error) {
        document.getElementById('typing').style.display = 'none';
        addMessage('Error connecting to AI! Make sure the server is running!', false);
    }

    document.getElementById('sendBtn').disabled = false;
}
