
from flask import Flask, request, jsonify, render_template
import google.generativeai as genai
import pandas as pd
from dotenv import load_dotenv
import os
import json
import re 
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from supabase import create_client, Client


# Load the environment variables
load_dotenv()

# API initialization
genai.configure(api_key=os.environ["GEMINI_API_KEY"])

# for smtp email id and app password 
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")  
APP_PASSWORD = os.getenv("APP_PASSWORD")  

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# App initialization
app = Flask(__name__)

def log_query(endpoint, query):
    """
    Log the user query along with endpoint and timestamp in Supabase.
    """
    log_entry = {
        "endpoint": endpoint,
        "query": query,
        "timestamp": datetime.utcnow().isoformat(),
    }
    try:
        response = supabase.table("chat_logs").insert(log_entry).execute()
        # print("Log entry inserted:", response)
    except Exception as e:
        print(f"Error logging query: {e}")


# Load and read CSV
csv_file = os.path.join(os.getcwd(), "projects.csv")

if not os.path.exists(csv_file):
    df = pd.read_csv(csv_file,  encoding="utf-8")
else:
    df = pd.read_csv(csv_file, encoding='utf-8', on_bad_lines='skip')

df.columns = df.columns.str.strip() 
# Ensure techTags column and remove potential image column if exists 
if 'techTags' not in df.columns:
    df['techTags'] = ""
if 'image' in df.columns:
    df.drop(columns=['image'], inplace=True)
df['techTags'] = df['techTags'].fillna("").astype(str)



#  file to store chat/log messages
# CHAT_LOG_FILE = "chat_logs.json" 

# user query log
# def log_query(endpoint, query):
#     """
#     Log the user query along with endpoint and timestamp in a JSON file.
#     """
#     log_entry = {
#         "endpoint": endpoint,
#         "query": query,
#         "timestamp": datetime.now().strftime("%y-%m-%d %H:%M:%S"),
#     }
#     logs = [] 
#     if os.path.exists(CHAT_LOG_FILE):
#         try:
#             with open(CHAT_LOG_FILE, "r", encoding="utf-8") as f:
#                 logs = json.load(f)
#         except json.JSONDecodeError:
#             logs = []
#     logs.append(log_entry)
#     try:
#         with open(CHAT_LOG_FILE, "w", encoding="utf-8") as f:
#             json.dump(logs, f, indent=4, ensure_ascii=False)
#     except Exception as e:
#         print(f"Error logging query: {e}")




# Add Data route (CRUD)
@app.route('/add_data', methods=['GET', 'POST'])
def add_data():
    global df

    if request.method == 'POST':
        try:
            # Get JSON data
            data = request.get_json()

            if not data:
                return jsonify({'status': 'error', 'message': 'Invalid request data'}), 400
            # Handle Add Action
            if data['action'] == 'add':
                title = data['title']
                description = data['description']
                video = data['video']
                # image = data['image']  
                tagline = data['tagline']
                tech_tags = data['techTags']

                # Add new row to DataFrame
                new_row = {
                    'project title': title,
                    'description': description,
                    'video': video,
                    # 'image': image, 
                    'tagline': tagline,
                    'techTags': tech_tags,
                }
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                df.to_csv(csv_file, index=False, encoding='utf-8')

                # Update LLM with new data
                query_gemini_llm("")  

                return jsonify({'status': 'success', 'message': 'Project added and LLM updated successfully!'})

            # Handle Edit Action
            elif data['action'] == 'edit':
                row_index = data.get('rowIndex')
                title = data.get('title')
                description = data.get('description')
                video = data.get('video', '')
                # image = data.get('image', '') 
                tagline = data.get('tagline', '')
                tech_tags = data.get('techTags', '')

                if row_index is None or not title or not description:
                    return jsonify({'status': 'error', 'message': 'Invalid edit data.'}), 400

                # Update the specific row in DataFrame
                row_index = int(row_index)
                df.loc[row_index, 'project title'] = title
                df.loc[row_index, 'description'] = description
                df.loc[row_index, 'video'] = video
                # df.loc[row_index, 'image'] = image 
                df.loc[row_index, 'tagline'] = tagline
                df.loc[row_index, 'techTags'] = tech_tags

                # Save updated data to CSV
                df[['project title', 'description', 'video','tagline', 'techTags']].to_csv(csv_file, index=False)

               # Update LLM with updated data
                query_gemini_llm("") 

                return jsonify({'status': 'success', 'message': 'Project updated and LLM updated successfully!'})

            # Handle Delete Action
            elif data['action'] == 'delete':
                row_index = data.get('rowIndex')

                if row_index is None:
                    return jsonify({'status': 'error', 'message': 'Invalid delete data.'}), 400

                # Drop the row from DataFrame
                row_index = int(row_index)
                df = df.drop(row_index).reset_index(drop=True)

                # Save updated data to CSV
                df[['project title', 'description', 'video', 'tagline', 'techTags']].to_csv(csv_file, index=False)

                 # Update LLM with updated data
                query_gemini_llm("") 

                return jsonify({'status': 'success', 'message': 'Project deleted and LLM updated successfully!'})

            else:
                return jsonify({'status': 'error', 'message': 'Invalid action.'}), 400

        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500

    # Handle GET request - render HTML template with DataFrame data
    data =  df.to_dict(orient='records')
    return render_template('add_data_dashboard.html', data=data)


# This route processes starter/personal data queries only. It is only triggered
# when the frontend explicitly calls the '/process-starter-question' endpoint.
@app.route('/process-starter-question', methods=['POST'])
def process_starter_question_route():
    user_query = request.json.get('message', '').strip()
 
     # Log the query
    log_query("/process-starter-question", user_query)
    try:
        answer = process_starter_question(user_query)
        # Construct a simple JSON response.
        response_data = {
            "Project Title": "",
            "Description": answer,
            "Video": "",
            # "Image": [] 
        }
        return jsonify(response_data)
    except Exception as e:
        print(f"Starter question error: {e}")
        return jsonify({"error": "An error occurred while processing your starter query."}), 500
    
 
# Starter question function 
def process_starter_question_route():
    user_query = request.json.get('message', '').strip()
 
     # Log the query
    log_query("/process-starter-question", user_query)
    try:
        answer = process_starter_question(user_query)
        # Construct a simple JSON response.
        response_data = {
            "Project Title": "",
            "Description": answer,
            "Video": "",
            # "Image": [] 
        }
        return jsonify(response_data)
    except Exception as e:
        print(f"Starter question error: {e}")
        return jsonify({"error": "An error occurred while processing your starter query."}), 500
    
 
# Starter question function 
def process_starter_question(user_query):
 
    prompt = (
        "Below is the data about my profile, including my introduction, skills, project experience, and more. \n"
        "You have to use the following data to answer any query related to my portfolio. When a user asks about me or my work, "
        "respond as if you ARE Anaiza Tariq speaking directly to the user - not as an AI describing Anaiza.\n\n"
        "IMPORTANT TONE AND STYLE GUIDELINES:\n"
        "- Maintain a professional, articulate tone throughout all responses\n"
        "- Use first person ('I' statements) throughout the response\n"
        "- Share experiences and perspectives as if speaking from personal experience\n"
        "- Express passion for technology through precise, substantive statements rather than emotional expressions and use easiest wording not too much jargons.\n"
        "- AVOID casual interjections like 'oh!', 'wow!', 'huh!', or excessive exclamation marks\n"
        "- AVOID overly informal language or expressions that would be inappropriate in a professional setting\n" 
        "- Never use phrases like 'That's a great question!' or other filler statements\n"
        "- Present information in a clear, direct manner while maintaining warmth through substance, not emotional phrases\n"
        "- Speak as a confident professional make your selection of word clear and easy. \n"
        "- Never refer to yourself as an AI or assistant - you ARE Anaiza Tariq\n\n"
        "Data About Me (Anaiza):\n\n"
       """ABOUT Anaiza:
I am Anaiza Tariq, an AI Engineer. I help businesses find the gaps in their processes and identify exactly where AI can give them relief and a competitive advantage. I work remotely and collaborate with clients and teams globally. I build AI-powered systems end-to-end — from model integration and backend development all the way to full web application delivery.
 
Anaiza's CORE AREAS OF EXPERTISE:
I specialize in Machine Learning, Deep Learning, and Generative AI. My main focus areas are: building RAG (Retrieval-Augmented Generation) pipelines, designing Agentic AI systems that can reason and act autonomously, and backend development to ship these systems into real production environments — not just prototypes.
 
Anaiza's TECH STACK:
Python is my core language. For AI/ML I use PyTorch, Transformers, and Hugging Face. I integrate OpenAI and DeepSeek APIs into production applications. For GenAI systems I build RAG pipelines with embeddings and vector retrieval, and design multi-step agent workflows. Backend: FastAPI and Flask. Frontend: HTML, CSS, Bootstrap, JavaScript. Databases: PostgreSQL (Supabase) and SQLite. I also use Whisper for speech-to-text and ReportLab for automated PDF generation.
 
WHAT Anaiza HAS BUILT:
- Custom AI chatbots trained on domain-specific data
- RAG-based systems for grounded, factual knowledge retrieval
- AI-powered web apps integrating LLMs into real user workflows
- Voice-enabled applications (speech → LLM → output)
- AI Invoice Generator: voice input → Whisper transcription → LLM data extraction → editable + final PDF via ReportLab
- Data-driven dashboards with CRUD operations (Flask)
- Real estate AI system (in progress): chat-based lead interaction and engagement
 
Anaiza's CURRENT FOCUS:
Building agentic AI systems for real-world business use cases, and developing a real estate AI system with chat-based user interaction. I also spend significant time doing business gap analysis — studying how a business operates, identifying where manual processes slow them down, and designing AI systems specifically for those gaps.
 
Anaiza's APPROACH:
I start by understanding the business, not the technology. The most important question is always: where will AI actually make a difference here? Then I design and build a system around that answer — practical, reliable, and built for real use, not just demos.
 
Anaiza's VISION:
I believe AI should solve real problems, not just showcase technology. Every system I build is an opportunity to close the gap between what AI can do and what a business actually needs.
"""
        "Based on the above personal information about me (Anaiza), please answer the following question as if I (Anaiza) am speaking directly to the person.\n\n"
        "RESPONSE STYLE RULES:\n"
        "- Answer ONLY what the user actually asked — do not volunteer extra sections or unrelated info\n"
        "- Match the depth to the question: a simple question gets a short natural answer, a detailed question gets a fuller one\n"
        "- When listing skills or tools, include all relevant ones but keep descriptions brief per item\n"
        "- A visitor should feel like they are in a real conversation, not reading a portfolio page\n"
        "- If the question is a greeting, respond with one warm, natural sentence only\n"
        "- Use simple, easy wording. No unnecessary jargon.\n\n"
        f"{user_query}\n"
    )
 
    # Call the Gemini LLM with this prompt.
    model = genai.GenerativeModel('gemini-2.5-flash')
    response = model.generate_content(prompt)
    content = response.candidates[0].content.parts[0].text
 
    # Clean any markdown formatting.
    content = re.sub(r"```|```json", "", content).strip() 
    return content
 
 
# This route handles project queries only using the CSV dataset.
# It is invoked when the frontend calls the '/generate-response' endpoint.
@app.route('/generate-response', methods=['POST'])
def generate_response():
    user_query = request.json.get('message', '').strip()  
    chat_history = request.json.get('history', '').strip()
 
     # Log the query
    log_query("/generate-response", user_query)  
    try:
        # prompt to maintain conversation chain for llm
        conversational_chain = f"Conversation history: \n{chat_history}\n\n User's new query \n{user_query}\n\n"
        
        result = query_gemini_llm(conversational_chain)
        # print("Parsed Result:", result)
        response_data = {
            "Project Title": result.get("Project Title", ""),
            "Description": result.get("Description", ""),
            "Video": result.get("Video", "").strip(),
            # "Image": [f"/static/images/{img.strip()}" for img in result.get("Images", []) if img.strip()]
        }
        # print("Response JSON:", response_data)
        return jsonify(response_data)
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "An error occurred while processing your query."}), 500
 
 
# function to query the Gemini LLM with CSV data and the user query.
# and this function can also checks if the query is about personal/portfolio data.
def query_gemini_llm(user_query):
 
    personal_data = (
        "ABOUT ANAIZA:\n"
        "I am Anaiza Tariq, an AI Engineer. I help businesses find the gaps in their processes and identify exactly where AI can give them relief and a competitive advantage. "
        "I work remotely and collaborate with clients and teams globally. "
        "I build AI-powered systems end-to-end — from model integration and backend development to full web application delivery.\n\n"
 
        "Anaiza's CORE AREAS OF EXPERTISE:\n"
        "My work spans several interconnected areas. I specialize in Machine Learning and Deep Learning for building predictive and intelligent systems. "
        "Generative AI is a major focus — I work with large language models, design RAG (Retrieval-Augmented Generation) pipelines, and apply prompt engineering to make LLMs behave precisely as needed. "
        "I also build Agentic AI systems, where the AI can reason, plan, and take actions autonomously to complete complex tasks. "
        "Beyond model work, I develop the full backend of AI applications so these systems actually run in production, not just in notebooks.\n\n"
 
        "Anaiza's TECH STACK:\n"
        "Python is my core language. For AI/ML I use PyTorch, Transformers, and Hugging Face. "
        "I integrate OpenAI and DeepSeek APIs into production applications. "
        "For GenAI systems I build RAG pipelines with embeddings and vector retrieval, and design multi-step agent workflows. "
        "Backend: FastAPI and Flask. Frontend: HTML, CSS, Bootstrap, JavaScript. Databases: PostgreSQL (Supabase) and SQLite. "
        "I also use Whisper for speech-to-text and ReportLab for automated PDF generation. "
        "My unique edge is Business Gap Analysis — identifying exactly where AI can automate manual workflows and designing agentic systems to solve them.\n\n"
 
        "WHAT Anaiza HAS BUILT:\n"
        "I have built a range of AI-powered systems across different domains:\n"
        "- Custom AI chatbots trained on domain-specific data that respond naturally and accurately within their area\n"
        "- RAG-based systems that retrieve from structured knowledge sources to give grounded, factual answers\n"
        "- AI-powered web applications that bring LLM capabilities into real user-facing workflows\n"
        "- Voice-enabled applications that take speech input, process it through an LLM, and return intelligent output\n"
        "- An AI Invoice Generator: users speak their invoice details, the system converts speech to text using Whisper, "
        "extracts and organizes the data using an LLM, and generates both an editable and a final PDF invoice using ReportLab\n"
        "- Data-driven dashboards with full CRUD operations built on Flask\n"
        "- A real estate AI system (currently in development) that engages leads through natural chat-based interaction\n\n"
 
        "Anaiza's CURRENT FOCUS:\n"
        "Right now I am focused on two things. First, building agentic AI systems for real-world business use cases — "
        "systems that can reason and act, not just respond. Second, I am working on a real estate AI system designed around "
        "chat-based user interaction and intelligent lead engagement. Alongside project work, I spend significant time analyzing businesses, "
        "identifying the specific gaps where AI can add value, and designing systems tailored to those gaps. "
        "This kind of AI strategy and system design work is something I do well and find genuinely meaningful.\n\n"
 
        "Anaiza's APPROACH:\n"
        "I approach every problem by understanding the business context first before touching any code. "
        "I believe the most important step is identifying exactly where AI will make a real difference, not just applying it broadly. "
        "I combine analytical thinking with practical engineering — my goal is always a system that works reliably in the real world, not just in theory.\n\n"
 
        "Anaiza's VISION:\n"
        "I am committed to continuous learning and staying current with how fast this field moves. "
        "I believe AI should serve people in ways that are practical and accessible. "
        "Every system I build is an opportunity to close the gap between what AI can do and what businesses and users actually need.\n\n"
 
        "HOW Anaiza COMMUNICATES:\n"
        "When responding to questions about myself, I speak in first person, with a conversational, authentic tone. "
        "I share personal perspectives and experiences rather than generic descriptions. "
        "I am professional but direct, and I communicate as if having a real conversation with the person asking. "
        "I always use simple, clear wording — no unnecessary jargon."
    )
 
    # Otherwise, proceed with searching the projects dataset.
    projects_data = df[['project title', 'description']].to_json(orient='records')
    prompt = (
        "You are representing the portfolio of Anaiza Tariq. Just act as Anaiza, so when anyone asks a query to you it would be about Anaiza, but the person getting details is not Anaiza — that person is someone else. So be wise, professional, welcoming and ensure what the query is about and how you will act as Anaiza with a person that is not Anaiza. Do not keep saying 'I am Anaiza, I am this and that' — be on the topic.\n\n"
        "You have access to two types of data:\n\n"
        "1. Personal Profile Data:\n" + personal_data + "\n"
        "2. Projects Data:\n" 
        "The following is a dataset (in JSON format) containing details about various projects:\n"
        f"{projects_data}\n\n"
        "You also have a conversation history that helps maintain context. Analyze the user's query below, along with the conversational chain, and provide an answer accordingly:\n\n"
        f"User query and conversation chain:\n{user_query}\n\n"
        "Please examine the user's question below and decide which data source is most appropriate to answer it. "
        "If the question is about my background, profile, or personal information, answer using the Personal Profile Data. "
        "If someone says 'who am I' or a person's query is about knowing who they themselves are, that query is not about Anaiza — make sure you understand the context of the query very well. "
        "When answering, speak as if you ARE me (Anaiza) — use first person and present information as if I'm personally sharing my professional experience.\n\n"
        
        "When you answer personal questions, leave \"Project Title\" empty and only fill in \"Description\" with a professional response in my voice. "
        "If the question is about my projects, answer using the Projects Data. "
        
        "IMPORTANT TONE AND STYLE GUIDELINES FOR PERSONAL RESPONSES:\n"
        "- Maintain a professional, articulate tone throughout all responses\n"
        "- Use first person ('I' statements) consistently\n"
        "- Express passion for technology through precise, substantive statements\n"
        "- AVOID casual interjections like 'oh!', 'wow!', 'huh!', or excessive exclamation marks\n"
        "- AVOID phrases like 'That's a great question!' or other filler statements\n"
        "- AVOID overly informal language or expressions that would be inappropriate in a professional setting\n"
        "- Present information clearly and directly while maintaining warmth through substance, not emotional phrases\n"
        "- Speak as a confident professional would when representing themselves to potential business partners\n"
        "- Include specific examples or relevant professional anecdotes where appropriate\n"
        "- Never refer to yourself as an AI or assistant - you ARE Anaiza Tariq\n"
        "- Never start with 'hi' or 'hello there' unless directly responding to a greeting\n"
        "- Keep responses clear and focused on directly answering the question asked\n"
        "RESPONSE STYLE RULES FOR PERSONAL QUESTIONS:\n"
        "- Answer ONLY what the user actually asked — do not volunteer extra sections or unrelated info\n"
        "- Match the depth to the question: a simple question gets a short natural answer, a detailed question gets a fuller one\n"
        "- When listing skills or tools, include all relevant ones but keep descriptions brief per item\n"
        "- A visitor should feel like they are in a real conversation, not reading a portfolio page\n"
        "- If it is a greeting, reply with one natural, friendly sentence only\n\n"
 
        "When user query is about a project, follow the below prompt: "
        "Now just tell about project details, do not be like Anaiza. "
        "There is a dataset where all my projects are listed. Your task is to provide detailed and well-defined information about the project that the user asks about. "
        "First carefully understand the user query — either give a specific project to the user or give just a brief description from all. "
        "When you give details to the user, make sure you provide all the information that is saved in the project's description in the dataset. There is no word limit, so tell about the project in detail. "
        "You are strictly bound to provide content relevant to the user's query. "
        "If the user's query contains a greeting (for example, 'hi', 'hello', or 'hey'), "
        "disregard any project matching and respond with a warm and friendly greeting. "
        "If the user query is about knowing my projects — for example if someone says 'tell me about YouTube Title Generator and AI Health Mate' (or any other multi-project query) — give them just a short description of each. When answering about two or more projects at a time, keep each description short. Make a clear distinction between different projects. "
        "For all cases, return the response as valid JSON with the following keys: "
        "\"Project Title\", \"Description\". "
        "If the query is a greeting, leave \"Project Title\" empty and only fill in \"Description\" with a friendly greeting message. "
        "If the query is about a project, refer to the dataset to provide detailed project information by including all information stored in the project's description. "
        "If no project matches the query, leave \"Project Title\" empty and only fill in \"Description\" with a polite message indicating no matching project found. "
        "There is no word limit, so be as detailed as required. "
        "Care about what the user needs — either they want details of a project or may want to know the stack used in projects, so organize your response accordingly. "
        "Follow this format to organize content: "
        "- IMPORTANT: Your response MUST include properly formatted <h3> tags for all section headings."
        "- ALWAYS include a separate <h3>Tech Stack</h3> section listing the technologies used in the project."
        "- Structure the project description with clear <h3> headings like '<h3>Overview</h3>', '<h3>Features</h3>', '<h3>Implementation</h3>'."
        "- Start with a brief overview about what the project does."
        "- Use bullet points for listing features (<ul><li>Feature 1</li></ul>)."
        "- Use numbered steps for processes (<ol><li>Step 1</li></ol>)."
        "- Highlight key points with <h5> tags."
        "- Keep paragraphs short (3-4 sentences maximum)."
        "- Present content in a structured, easy-to-scan format."
        "- Use a conversational, engaging tone."
        "- Ensure all HTML tags are properly closed and formatted."
        "- All headings MUST be wrapped in <h3> tags, NOT as plain text or markdown."
        "- The description should have at least 3 distinct sections with proper <h3> headings."
        "Analyze the user's query carefully and provide a complete response in JSON format. Make sure that the response **MUST** be in **valid JSON format** without any markdown formatting.\n\n"
        f"User query: {user_query}\n\n"
        f"Data: {projects_data}\n"
    )

    model = genai.GenerativeModel('gemini-2.5-flash')
    response = model.generate_content(prompt)
    content = response.candidates[0].content.parts[0].text
 
    # print("LLM Response:", content)
 
    # Remove markdown formatting.
    content = re.sub(r"```json|```|^- ", "", content).strip()
    
    # print("Cleaned Content to be parsed:", content)
    result = parse_llm_response(content)
    return result
 


# Function to parse the LLM response.
def parse_llm_response(content):
    try:
        result = json.loads(content)
        # Hardcode empty "Project Title" if it's null or not provided.
        result["Project Title"] = (result.get("Project Title") or "").strip()
        # Standardize DataFrame column names
        # df.columns = df.columns.str.strip().str.lower()
        
        # Attempt to match the project title with our dataset.
        project_row = df[df['project title'].str.strip() == result["Project Title"].strip()]
        if project_row.empty:
            result["Video"] = ""
            # images
            # result["Images"] = []
            return result
        else:
            project = project_row.iloc[0]
            result["Video"] = project.get('video', '').strip() if 'video' in df.columns and pd.notna(project['video']) else ""
            # images
            # result["Images"] = project.get('image', '').split(';') if 'image' in df.columns and pd.notna(project['image']) else []
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        print("Parsing error:", e)
        # images code is commented
        # return {"Project Title": "", "Description": "I'm sorry, but I couldn't find any project matching your query.", "Video": "", "Images": []}
        return {"Project Title": "", "Description": "I'm sorry, but I couldn't find any project matching your query.", "Video": ""}
    except Exception as e:
        print("Unexpected error:", e)
        return {"Project Title": "", "Description": "I'm sorry, but something went wrong while processing your query.", "Video": ""}
    
    return result


# Home page route.
@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

# images path
# @app.route('/static/images/<path:filename>')
# def serve_images(filename):
#     return send_from_directory('static/images', filename)

# Get projects list.
@app.route('/get-projects')
def get_projects():
    try:
        df_projects = pd.read_csv('projects.csv', encoding='utf-8-sig')

        # Drop empty columns caused by trailing commas
        df_projects = df_projects.dropna(axis=1, how='all')

        # Ensure column names are stripped of spaces
        df_projects.columns = df_projects.columns.str.strip()

        # Convert techTags to an array
        if 'techTags' in df_projects.columns:
            df_projects['techTags'] = df_projects['techTags'].astype(str).apply(lambda x: x.split(',') if x else [])

        # Convert to JSON
        projects = df_projects.to_dict(orient='records')
        return jsonify(projects)
    except Exception as e:
        print("Error in /get-projects:", str(e))  # Debugging
        return jsonify({"error": str(e)}), 500


# Submit Contact (email transfer)
@app.route('/submit-contact', methods=['POST'])
def submit_contact():
    data = request.get_json()
    name = data.get('name', '')
    email = data.get('email', '')
    subject = data.get('subject', 'No Subject')  
    message = data.get('message', '')

    if not name or not email or not message:
        return jsonify({"error": "Name, email, and message are required."}), 400

    # Email content
    email_subject = f"New Contact Form Submission: {subject}"
    email_body = f"""
    You have received a new message from your portfolio contact form.\n\n
    Name: {name}\n
    Email: {email}\n
    Subject: {subject}\n
    Message:\n{message}\n\n
    Timestamp: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    """

    try:
        # Create the email
        msg = MIMEMultipart()
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = EMAIL_ADDRESS  
        msg['Subject'] = email_subject
        msg.attach(MIMEText(email_body, 'plain'))

        # Connect to Gmail SMTP server and send the email
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()  # Secure the connection
            server.login(EMAIL_ADDRESS, APP_PASSWORD) 
            server.send_message(msg) 

        return jsonify({"success": True, "message": "Thank you for your message! I will respond shortly."})

    except Exception as e:
        return jsonify({"error": f"An error occurred while sending the email: {str(e)}"}), 500


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8000))  # Koyeb provides PORT dynamically
    app.run(host="0.0.0.0", port=port)
    # app.run(debug=True)


