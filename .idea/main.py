from flask import Flask, render_template_string, request, session
import webbrowser
import threading
import google.generativeai as genai
import re

genai.configure(api_key="AIzaSyBgxZmfMysn6BinrQuNk_12XXReteeoD6A")  # Replace with your Gemini API key

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Needed for session

HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Rashmi 🤖</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { background: #f0f2f5; font-family: 'Segoe UI', Arial, sans-serif; }
        .chat-container { 
            max-width: 420px; 
            margin: 40px auto; 
            background: #fff; 
            border-radius: 18px; 
            box-shadow: 0 4px 24px rgba(0,0,0,0.08); 
            padding: 0 0 20px 0;
        }
        .header {
            background: linear-gradient(90deg, #4caf50 0%, #1976d2 100%);
            color: #fff;
            border-radius: 18px 18px 0 0;
            padding: 24px 0 16px 0;
            text-align: center;
            font-size: 1.5em;
            font-weight: 600;
            letter-spacing: 1px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        }
        .messages { 
            display: flex; 
            flex-direction: column; 
            padding: 18px 18px 0 18px; 
            min-height: 320px;
            max-height: 650px;   /* Fixed height */
            overflow-y: auto;    /* Enable vertical scroll */
            background: #fff;
        }
        .message { 
            margin: 10px 0; 
            padding: 12px 18px; 
            border-radius: 20px; 
            max-width: 80%; 
            font-size: 1em;
            word-break: break-word;
            position: relative;
        }
        .user { 
            background: #e3f2fd; 
            align-self: flex-end; 
            text-align: right; 
            border-bottom-right-radius: 6px;
        }
        .bot { 
            background: #f5f5f5; 
            align-self: flex-start; 
            text-align: left; 
            border-bottom-left-radius: 6px;
        }
        .avatar {
            width: 32px; height: 32px; border-radius: 50%; 
            display: inline-block; vertical-align: middle; margin-right: 8px;
            background: #1976d2; color: #fff; text-align: center; line-height: 32px; font-weight: bold;
            font-size: 1.1em;
        }
        .input-container { 
            display: flex; 
            margin: 24px 18px 0 18px; 
        }
        input[type="text"] { 
            flex: 1; 
            padding: 12px; 
            border-radius: 20px; 
            border: 1px solid #ccc; 
            font-size: 1em;
            outline: none;
            transition: border 0.2s;
        }
        input[type="text"]:focus {
            border: 1.5px solid #1976d2;
        }
        button { 
            padding: 12px 24px; 
            border-radius: 20px; 
            border: none; 
            background: #1976d2; 
            color: #fff; 
            margin-left: 10px; 
            cursor: pointer; 
            font-size: 1em;
            font-weight: 500;
            transition: background 0.2s;
        }
        button:hover {
            background: #145ea8;
        }
        .command { color: #1976d2; font-weight: bold; }
        .typing {
            display: inline-block;
            height: 16px;
        }
        .dot {
            height: 12px;
            width: 12px;
            margin: 0 2px;
            border-radius: 50%;
            display: inline-block;
            animation: bounce 1s infinite;
        }
        .dot1 { background: #ff5252; animation-delay: 0s; }
        .dot2 { background: #ffeb3b; animation-delay: 0.2s; }
        .dot3 { background: #4caf50; animation-delay: 0.4s; }
        @keyframes bounce {
            0%, 80%, 100% { transform: translateY(0); }
            40% { transform: translateY(-8px); }
        }
        @media (max-width: 500px) {
            .chat-container { max-width: 98vw; }
            .messages, .input-container { padding-left: 6px; padding-right: 6px; }
        }
    </style>
</head>
<body>
    <div class="chat-container">
        <div class="header">
            <span class="avatar">R</span> Rashmi Chatbot
        </div>
        <div class="messages" id="messages"></div>
        <form class="input-container" id="chat-form">
            <input type="text" id="user-input" autocomplete="off" placeholder="Type a message..." required>
            <button type="submit">Send</button>
        </form>
    </div>
    <script>
        const form = document.getElementById('chat-form');
        const input = document.getElementById('user-input');
        const messages = document.getElementById('messages');

        function addMessage(text, sender) {
            let html = text;
            const div = document.createElement('div');
            div.className = 'message ' + sender;
            if(sender === 'bot') {
                html = `<span class="avatar">R</span> ` + html;
            }
            div.innerHTML = html;
            messages.appendChild(div);
            messages.scrollTop = messages.scrollHeight;
            return div;
        }

        function addTyping() {
            const typingDiv = document.createElement('div');
            typingDiv.className = 'message bot';
            typingDiv.innerHTML = `<span class="avatar">R</span> <span class='typing'><span class='dot dot1'></span><span class='dot dot2'></span><span class='dot dot3'></span> Typing...</span>`;
            messages.appendChild(typingDiv);
            messages.scrollTop = messages.scrollHeight;
            return typingDiv;
        }

        form.onsubmit = async (e) => {
            e.preventDefault();
            const userText = input.value;
            addMessage(userText, 'user');
            input.value = '';
            const typingDiv = addTyping();
            const res = await fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: userText })
            });
            const data = await res.json();
            messages.removeChild(typingDiv);
            addMessage(data.response, 'bot');
        };
    </script>
</body>
</html>
"""

def format_response(text):
    # Bold "**Title:** explanation" and put explanation on next line
    def bold_colon_replacer(match):
        return f"<b>{match.group(1)}:</b><br>{match.group(2).strip()}"
    text = re.sub(r"\*\*(.+?):\*\*\s*(.+?)(?=\n|\*|$)", bold_colon_replacer, text)

    # Bold any remaining **text** (not just those ending with a colon)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)

    # Only convert lines that start with "* " to bullets
    lines = text.splitlines()
    formatted_lines = []
    for line in lines:
        if line.strip().startswith("* "):
            formatted_lines.append(f"<br>&bull; {line.strip()[2:]}")
        elif line.strip().startswith("• "):
            formatted_lines.append(f"<br>&bull; {line.strip()[2:]}")
        elif line.strip():  # skip empty lines
            formatted_lines.append(line.strip())
    return "<br>".join(formatted_lines)

def get_response(history):
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        prompt = (
            "You are Rashmi, a powerfull helping Assistant. it asked any defination then make it it correct it thinking own 4-5 time and make sure every defenation output should me formal standered . make sure every question give very very very short ans .Make sure every answer is short; if the answer is long, make it point-wise and concise.please reply like real humen not sound robotic "
            "If the user asks for a command, provide a Windows command in a <span class='command'></span> tag. "
            "Remember the previous conversation and answer accordingly.\n"
        )
        for entry in history:
            prompt += f"{entry['role'].capitalize()}: {entry['content']}\n"
        response = model.generate_content(prompt)
        return format_response(response.text.strip())
    except Exception as e:
        return "Sorry, I couldn't process your request."

@app.route('/')
def index():
    session['history'] = []  # Clear chat history on page load/refresh
    return render_template_string(HTML_PAGE)

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message', '')
    # Initialize history in session if not present
    if 'history' not in session:
        session['history'] = []
    # Add user message to history
    session['history'].append({'role': 'user', 'content': user_message})
    # Get response from Gemini
    response = get_response(session['history'])
    # Add bot response to history
    session['history'].append({'role': 'bot', 'content': response})
    session.modified = True
    return {'response': response}

def open_browser():
    webbrowser.open("http://127.0.0.1:5000")

if __name__ == "__main__":
    threading.Timer(1.5, open_browser).start()
    app.run()