from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import openai
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from dotenv import load_dotenv
import os
import textwrap

app = Flask(__name__)
CORS(app)

load_dotenv()
# OpenAI API Key
openai.api_key = os.getenv("OPENAI_API_KEY")

# messages
starter_msg = [
    {"role": "system", "content": "Your name is CENA and will not change."},
    {"role": "system", "content": "Always respond in points or steps, not paragraphs."},
    {"role": "system", "content": "You are a legal aid for users in India; use legal terminology."},
    {"role": "system", "content": "Strictly only answer legal doubts and greetings. On being asked, mention that this was developed and coded by Tanay Kashyap in 2024."},
    {
        "role": "system",
        "content": "Your responses are based on: 1. Indian Laws: Relevant statutes and codes. 2. Judicial Precedents: Key Supreme Court and High Court rulings. 3. Legal Procedures: Guidance on complaints and processes. 4. Consumer Rights: Consumer protection laws. 5. General Legal Queries: Answers to common legal questions."
    },
    {"role": "system", "content": "Responses should have line breaks using 'backslash n space'."},
    {"role": "system", "content": "Cite exact articles and sections, sounding like a lawyer."},
    {"role": "system", "content": "Console victims and offer empathetic support."},
]

messages_hist = []

@app.route('/api/cena-chat', methods=['POST'])
def chat():
    global messages_hist
    global starter_msg
    data = request.get_json()
    message = data.get('message')
    
    # Check if message is provided
    if not message:
        return jsonify({"error": "Message is required"}), 400
    
    if not messages_hist:
        messages_hist.extend(starter_msg)
    
    messages_hist.append({"role": "user", "content": message})
    try:
        # Use the new chat completion API for GPT models
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages_hist,
            max_tokens=500
        )
        # Get response from the OpenAI API
        bot_reply = response.choices[0].message.content.strip()
        messages_hist.append({"role": "assistant", "content": bot_reply})
        #print(messages_hist)
        return jsonify({"message": bot_reply}), 200

    except openai.OpenAIError as e:
        # Handle OpenAI server issues and return "OpenAI server down"
        print(str(e))
        return jsonify({"message": "OpenAI Server down"}), 500

    except Exception as e:
        # Catch any other errors
        print(str(e))
        return jsonify({"message": "An unexpected error occurred"}), 500

@app.route('/api/chat-reset', methods=['POST'])
def reset():
    global messages_hist
    messages_hist = []  # Clear the message history
    return "", 204

# Route to generate the summary PDF
@app.route('/api/generate-summary', methods=['POST'])
def generate_summary():
    summary = ""
    summary_prompt = ""
    # Step 1: Generate the summary using OpenAI API based on the chat history
    global messages_hist

    summary_prompt = "Summarize the following legal conversation with headings: Problem, Steps to take, Laws Applicable(Be Specific with sections/articles/IPC/CRPC applicable).\n\n" + \
                      "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in messages_hist if msg['role'] == 'user'])
    
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": summary_prompt}],
            max_tokens=500
        )
        summary = response.choices[0].message.content.strip()

    except openai.OpenAIError as e:
        return jsonify({"message": "OpenAI Server down"}), 500

    # Step 2: Create the PDF using the summary
    pdf_buffer = BytesIO()
    pdf = canvas.Canvas(pdf_buffer, pagesize=letter)
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(30, 750, "CENA: The Legal AID")
    pdf.setFont("Helvetica", 14)
    pdf.drawString(30, 730, "Chat Summary")

    pdf.setFont("Helvetica", 12)
    # Split the summary into lines to fit the PDF
    lines = summary.split('\n')
    
    y = 700
    max_width = 100

    for line in lines:
        if line in ("Problem:", "Steps to take:", "Laws Applicable:") :
            y-=40
            pdf.setFont("Helvetica-Bold", 12)
            pdf.drawString(30, y, line)
            y-=20
            pdf.setFont("Helvetica", 12)

        else:
            wrapped_lines = textwrap.wrap(line, width=max_width)
            for wrapped_line in wrapped_lines:
                pdf.drawString(30, y, wrapped_line)
                y -= 20  # Move down for the next line

    pdf.save()
    pdf_buffer.seek(0)

    # Step 3: Return the PDF as a file download
    return send_file(pdf_buffer, as_attachment=True, download_name="chat_summary.pdf", mimetype='application/pdf')


if __name__ == '__main__':
    app.run(debug=True)