import json
import requests
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils.timezone import now
from django.core.exceptions import ObjectDoesNotExist
from .models import JobEntry, Interview  # Ensure these models exist
import uuid
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from dotenv import load_dotenv
import os
import google.generativeai as genai
import speech_recognition as sr
from .models import JobEntry, InterviewResponse, Interview
from django.views.decorators.csrf import csrf_exempt
import json
import requests
from django.core.exceptions import ObjectDoesNotExist
# Load Gemini API key from settings
GEMINI_API_KEY = "AIzaSyBa6y10WFEQu2SDoLACcHKo86tzfhNetaQ"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-pro-002:generateContent"

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == "POST":
        email = request.POST.get('email')
        password = request.POST.get('password')

        try:
            user = User.objects.get(email=email)
            user = authenticate(request, username=user.username, password=password)
        except User.DoesNotExist:
            user = None

        if user:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid email or password")
    
    return render(request, 'login.html')

def register_view(request):
    if request.method == "POST":
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if password != confirm_password:
            messages.error(request, "Passwords do not match")
            return redirect('register')

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email is already registered")
            return redirect('register')

        user = User.objects.create_user(username=email, email=email, password=password)
        messages.success(request, "Registration successful! Please log in.")
        return redirect('login')

    return render(request, 'register.html')

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == "POST":
        email = request.POST.get('email')
        password = request.POST.get('password')

        try:
            user = User.objects.get(email=email)
            user = authenticate(request, username=user.username, password=password)
        except User.DoesNotExist:
            user = None

        if user:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid email or password")
    
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    return redirect('login')

from django.shortcuts import render

# def result_page(request):
#     # Get evaluation data from session
#     evaluation_data = request.session.get("evaluation_data", {})

#     context = {
#         "evaluation": evaluation_data.get("evaluation", "No evaluation available."),
#         "strengths": evaluation_data.get("strengths", "No strengths detected."),
#         "improvement": evaluation_data.get("improvement", "No improvement suggestions."),
#         "score": evaluation_data.get("score", "N/A"),
#     }

#     return render(request, "result.html", context)
def result_view(request):
    # ✅ Debugging: Print session keys
    print("Available Session Keys:", list(request.session.keys()))

    # ✅ Retrieve session data safely
    evaluation_data = request.session.get("evaluation_data", {
        "evaluation": "No data received",
        "strengths": "No data received",
        "improvement": "No data received",
        "score": "No data received",
    })

    return render(request, "result.html", evaluation_data)







@login_required
def dashboard_view(request):
    """Fetch user's past interviews & display on the dashboard."""
    past_interviews = Interview.objects.filter(user=request.user).order_by('-created_at')
    return render(request, "dashboard.html", {"past_interviews": past_interviews})

def interview_view(request):
    return render(request, 'interview.html')


@login_required
def add_job_entry(request):
    if request.method == "POST":
        role = request.POST.get("role")
        description = request.POST.get("description")
        experience = request.POST.get("experience")

        if not (role and description and experience):
            return JsonResponse({"error": "All fields are required!"}, status=400)

        job_entry = JobEntry.objects.create(
            user=request.user,
            role=role.strip(),  # Trim spaces
            description=description.strip(),
            experience=int(experience)
        )

        return JsonResponse({"message": "Job entry added successfully", "id": job_entry.id})

    return JsonResponse({"error": "Invalid request"}, status=400)


import logging

logger = logging.getLogger(__name__)

@login_required
def speech_to_text(request):
    """Convert user's speech response to text."""
    recognizer = sr.Recognizer()
    mic = sr.Microphone(device_index=None)
    
    try:
        with mic as source:
            logger.info("Adjusting for ambient noise...")
            recognizer.adjust_for_ambient_noise(source, duration=2)
            logger.info("Listening...")
            audio = recognizer.listen(source)
            logger.info("Audio captured.")

        logger.info("Recognizing speech...")
        text = recognizer.recognize_google(audio)
        logger.info(f"Recognized text: {text}")
        return JsonResponse({"text": text})
    except sr.UnknownValueError:
        logger.error("Could not understand the audio.")
        return JsonResponse({"error": "Could not understand the audio."})
    except sr.RequestError as e:
        logger.error(f"Speech recognition service error: {e}")
        return JsonResponse({"error": "Speech recognition service error."})

@login_required
def start_interview_api(request):
    """Start a new interview session with questions from Gemini API."""
    if request.method == "POST":
        try:
            # Parse JSON data
            data = json.loads(request.body)
            print("🔍 Received Request Data:", data)
            role = data.get('role')
            description = data.get('description')
            experience = data.get('experience')

            print("📌 Role:", role)
            print("📌 Description:", description)
            print("📌 Experience:", experience)

            if not all([role, description, experience]):
                return JsonResponse({"error": "All fields are required"}, status=400)

            # Save JobEntry
            job_entry = JobEntry.objects.create(
                user=request.user,
                role=role,
                description=description,
                experience=int(experience)
            )

            # Prepare request for Gemini API
            prompt = {
                "contents": [{
                    "parts": [{
                        "text": (
                            f"Generate 5 concise and professional interview questions for a {role} "
                            f"with {experience} years of experience. "
                            f"Focus on key skills and responsibilities from this job description: {description}. "
                            f"Keep each question under 20 words."
                        )
                    }]
                }]
            }

            response = requests.post(GEMINI_API_URL, json=prompt, params={"key": GEMINI_API_KEY})
            if response.status_code != 200:
                return JsonResponse({"error": "Failed to fetch questions from Gemini API"}, status=500)

            # Extract questions from API response
            response_data = response.json()
            candidates = response_data.get("candidates", [{}])
            if not candidates:
                return JsonResponse({"error": "Invalid API response"}, status=500)

            raw_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            all_lines = raw_text.split("\n")

            questions = [
                line.strip().split(":", 1)[-1].strip()
                for line in all_lines if line.strip()
            ]
            questions = list(filter(None, questions))[:5]  # Limit to 5 questions

            # Create interview entry
            interview = Interview.objects.create(
                user=request.user,
                position=role,
                description=description,
                experience=int(experience),
                questions=questions if questions else None,
                status='in_progress'
            )

            # Store in session
            request.session["interview_id"] = interview.id
            request.session["interview_questions"] = questions or []
            request.session["user_answers"] = []
            request.session["role"] = role
            request.session["description"] = description
            request.session["experience"] = experience
            request.session.modified = True  # Ensure session updates

            print("🔍 Session Data Stored:", request.session.get("role"), request.session.get("description"))
            
            return JsonResponse({"questions": questions})

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON data"}, status=400)
        except requests.exceptions.RequestException as e:
            return JsonResponse({"error": f"API request failed: {str(e)}"}, status=500)
        except Exception as e:
            return JsonResponse({"error": f"An unexpected error occurred: {str(e)}"}, status=500)

    elif request.method == "GET":
        """Fetch ongoing interview questions if any exist."""
        try:
            questions = request.session.get("interview_questions")

            if not questions:
                latest_interview = Interview.objects.filter(
                    user=request.user, 
                    status='in_progress'
                ).order_by('-created_at').first()

                if latest_interview and latest_interview.questions:
                    questions = latest_interview.questions
                    request.session["interview_questions"] = questions
                    request.session["interview_id"] = latest_interview.id
                    request.session["role"] = latest_interview.position
                    request.session["description"] = latest_interview.description
                    request.session["experience"] = latest_interview.experience
                    request.session.modified = True
                else:
                    return JsonResponse({"error": "No active interview found"}, status=404)

            return JsonResponse({"questions": questions})
        except ObjectDoesNotExist:
            return JsonResponse({"error": "Interview not found"}, status=404)
        except Exception as e:
            return JsonResponse({"error": f"An unexpected error occurred: {str(e)}"}, status=500)

    return JsonResponse({"error": "Method not allowed"}, status=405)


from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

@csrf_exempt
def submit_answer(request):
    """Store answers temporarily until the interview ends."""
    if request.method == "POST":
        data = json.loads(request.body.decode("utf-8"))
        question = data.get("question")
        answer = data.get("answer")

        if not question or not answer:
            return JsonResponse({"error": "Invalid data"}, status=400)

        # Store in session (temporary storage)
        user_answers = request.session.get("user_answers", [])
        user_answers.append({"question": question, "answer": answer})
        request.session["user_answers"] = user_answers  # ✅ Save session data

        return JsonResponse({"message": "Answer stored successfully!"})

    return JsonResponse({"error": "Invalid request method"}, status=405)

import google.generativeai as genai
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import firebase_admin
from firebase_admin import credentials, firestore
import re

# 🔹 Define your API key


# 🔹 Initialize Gemini AI
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-pro-latest")
import firebase_admin
from firebase_admin import credentials, firestore

# Check if Firebase is already initialized
if not firebase_admin._apps:
    print("Initializing Firebase...")
    cred = credentials.Certificate("V:\Mock interview\serviceaccountkey.json")  # Correct path to your JSON key
    firebase_admin.initialize_app(cred)
else:
    print("Firebase is already initialized.")

# Now try connecting to Firestore
db = firestore.client()

# Check if Firestore is working
print("Firestore connected successfully!")
docs = db.collection("interviews").get()

for doc in docs:
    print(doc.id, doc.to_dict())

# Fetch documents from 'interviews' collection
docs = db.collection("interviews").get()

for doc in docs:
    print(doc.id, doc.to_dict())



import json
from django.http import JsonResponse
from django.shortcuts import redirect
import firebase_admin
from firebase_admin import firestore
@csrf_exempt
def evaluate_interview(request):
    if request.method == "POST":
        try:
            # ✅ Parse JSON input
            data = json.loads(request.body)
            print("Received JSON:", data)

            role = data.get("role")
            description = data.get("description")

            print("Role Received:", role)  # Debugging
            print("Description Received:", description)  # Debugging

            # Convert empty values to None
            role = None if not role or role.strip() == "" else role
            description = None if not description or description.strip() == "" else description



            answers = [a for a in data.get("answers", []) if a and isinstance(a, dict) and "answer" in a and a["answer"].strip()]
            if not answers:
                return JsonResponse({"error": "No valid answer provided."}, status=400)

            last_answer = answers[-1]["answer"]
            print("Evaluating:", last_answer)

            # ✅ Generate evaluation using Gemini AI
            prompt = f"""
            You are an AI-based interview evaluator. Analyze the response carefully.

            **Candidate's Answer:** {last_answer}

            Provide a JSON response in this format:
            {{
                "evaluation": "Overall assessment",
                "strengths": "Key strengths",
                "improvement": "Areas to improve",
                "score": "Numerical rating (e.g., 8/10)"
            }}
            """
            response = model.generate_content(prompt)

            if not response or not hasattr(response, "text"):
                return JsonResponse({"error": "Invalid response from Gemini AI."}, status=500)

            raw_text = response.text.strip()
            print("Raw Gemini Response:", raw_text)

            # ✅ Extract evaluation details
            evaluation_data = parse_gemini_response(raw_text)
            score = evaluation_data.get("score", "N/A")

            # ✅ Store evaluation results in Firestore with correct role & description
            interview_data = {
                "role": role,  
                "description": description,  
                "score": score,
                "timestamp": firestore.SERVER_TIMESTAMP
            }

            # Debugging: Print what will be stored in Firestore
            print("Firestore Data to Store:", interview_data)

            # Remove None values before storing
            interview_data = {k: v for k, v in interview_data.items() if v is not None}

            interview_ref = db.collection("interviews").add(interview_data)


            
            # ✅ Store evaluation in Django session (including role & description)
            request.session["evaluation_data"] = {
                "role": role,  # Store role in session
                "description": description,  # Store description in session
                "evaluation": evaluation_data.get("evaluation", "No data"),
                "strengths": evaluation_data.get("strengths", "No data"),
                "improvement": evaluation_data.get("improvement", "No data"),
                "score": evaluation_data.get("score", "No data"),
            }
            request.session.modified = True  # Ensure session is updated
            print("✅ Storing Evaluation Data in Session:")
            print(request.session["evaluation_data"])


            return JsonResponse({
                "success": True,
                "message": "Evaluation completed!",
                "evaluation": evaluation_data,
                "interview_id": interview_ref[1].id  # Correct way to get the document ID
            }, status=200)

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON format."}, status=400)
        except Exception as e:
            print("Error:", str(e))
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method."}, status=405)

# 🔹 Improved Helper Function to Parse Gemini Response
def parse_gemini_response(response_text):
    try:
        # Remove possible code block markers (` ```json ... ``` `)
        response_text = response_text.strip().replace("```json", "").replace("```", "").strip()

        # Convert to dictionary
        parsed_json = json.loads(response_text)

        # Extract and validate values
        evaluation = parsed_json.get("evaluation", "Evaluation unavailable")
        strengths = parsed_json.get("strengths", "No strengths detected")
        improvement = parsed_json.get("improvement", "No improvement suggestions")
        score = parsed_json.get("score", "N/A")

        # Ensure score is a valid number format (e.g., "8/10")
        if isinstance(score, (int, float)):  
            score = f"{score}/10"  # Convert to string format
        elif isinstance(score, str) and not score.strip():  
            score = "N/A"  # If score is an empty string, replace with "N/A"

        return {
            "evaluation": evaluation,
            "strengths": strengths,
            "improvement": improvement,
            "score": score  # Ensure valid score format
        }

    except json.JSONDecodeError as e:
        print("Error decoding JSON:", e)
        return {
            "evaluation": "Invalid response format.",
            "strengths": "Error in response parsing.",
            "improvement": "Error in response parsing.",
            "score": "N/A"
        }


import firebase_admin
from firebase_admin import firestore

# Initialize Firestore if not already initialized
if not firebase_admin._apps:
    firebase_admin.initialize_app()

db = firestore.client()

@login_required
def get_past_interviews(request):
    """Fetch user's past interviews and allow retakes, including Firestore scores."""
    interviews = Interview.objects.filter(user=request.user).order_by("-created_at")
    interview_list = []

    for interview in interviews:
        # Fetch score from Firestore
        doc_ref = db.collection("interviews").document(str(interview.id))
        doc = doc_ref.get()
        score = None
        if doc.exists:
            score = doc.to_dict().get("score", "Pending")  # Get score or "Pending" if not found

        interview_list.append({
            "id": interview.id,
            "job_title": interview.position,  # ✅ Use 'position' instead of 'job_title'
            "score": score  # ✅ Fetch from Firestore
        })

    return JsonResponse({"previous_interviews": interview_list})


@login_required
def retake_interview(request, interview_id):
    """Allows users to retake a past interview."""
    interview = Interview.objects.get(id=interview_id)
    request.session["interview_id"] = interview.id
    request.session["interview_questions"] = interview.questions
    return redirect("interview")

from django.http import JsonResponse
import firebase_admin
from firebase_admin import firestore

db = firestore.client()

def delete_interview(request, interview_id):
    if request.method == "DELETE":
        db.collection("interviews").document(interview_id).delete()
        return JsonResponse({"message": "Deleted successfully"}, status=200)
    return JsonResponse({"error": "Invalid request"}, status=400)

@csrf_exempt  # 🔴 Disable CSRF for simplicity (use Solution 1 if needed)
def delete_all_interviews(request):
    if request.method == "DELETE":
        interviews_ref = db.collection("interviews")
        interviews = interviews_ref.stream()

        for interview in interviews:
            interview.reference.delete()

        return JsonResponse({"message": "All interviews deleted successfully"}, status=200)

    return JsonResponse({"error": "Invalid request"}, status=400)