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

# Load environment variables
load_dotenv()

# Configure Gemini API
GEMINI_API_KEY = "AIzaSyBa6y10WFEQu2SDoLACcHKo86tzfhNetaQ"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-pro-002:generateContent"

# ------------------------ AUTHENTICATION VIEWS ------------------------

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

@login_required
def dashboard_view(request):
    return render(request, 'dashboard.html')

def logout_view(request):
    logout(request)
    return redirect('login')

from django.shortcuts import render

def interview_view(request):
    return render(request, 'interview.html')


# ------------------ JOB INPUT & QUESTION GENERATION ------------------

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

@login_required
def start_interview_api(request):
    if request.method == "POST":
        try:
            # Parse and validate JSON data
            data = json.loads(request.body)
            role = data.get('role')
            description = data.get('description')
            experience = data.get('experience')

            if not all([role, description, experience]):
                return JsonResponse({"error": "All fields are required"}, status=400)

            # Save JobEntry
            job_entry = JobEntry.objects.create(
                user=request.user,
                role=role,
                description=description,
                experience=int(experience)
            )

            # Prepare Gemini API request
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

            # Safely extract response
            response_data = response.json()
            candidates = response_data.get("candidates", [{}])
            if not candidates:
                return JsonResponse({"error": "Invalid API response"}, status=500)

            raw_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            all_lines = raw_text.split("\n")

            # Clean and filter questions
            questions = [
                line.strip().split(":", 1)[-1].strip()
                for line in all_lines if line.strip()
            ]
            questions = list(filter(None, questions))[:5]

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

            return JsonResponse({"questions": questions})

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON data"}, status=400)
        except requests.exceptions.RequestException as e:
            return JsonResponse({"error": f"API request failed: {str(e)}"}, status=500)
        except Exception as e:
            return JsonResponse({"error": f"An unexpected error occurred: {str(e)}"}, status=500)

    elif request.method == "GET":
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
                else:
                    return JsonResponse({"error": "No active interview found"}, status=404)

            return JsonResponse({"questions": questions})
        except ObjectDoesNotExist:
            return JsonResponse({"error": "Interview not found"}, status=404)
        except Exception as e:
            return JsonResponse({"error": f"An unexpected error occurred: {str(e)}"}, status=500)

    return JsonResponse({"error": "Method not allowed"}, status=405)

# ------------------ SPEECH TO TEXT ------------------
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
# ------------------ SAVE USER'S ANSWERS ------------------
@login_required
def submit_answer(request):
    """Save each answer to session."""
    question = request.GET.get("question", "")
    answer = request.GET.get("answer", "")
    
    if not question or not answer:
        logger.error("Missing question or answer.")
        return JsonResponse({"error": "Missing question or answer."}, status=400)
    
    user_answers = request.session.get("user_answers", [])
    user_answers.append({"question": question, "answer": answer})
    request.session["user_answers"] = user_answers  # Update session
    
    logger.info(f"Answer saved: {answer} for question: {question}")
    return JsonResponse({"message": "Answer saved successfully."})
# ------------------ ANSWER EVALUATION ------------------
import json
import requests
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger(__name__)

@csrf_exempt
def evaluate_answer(request):
    if request.method == "POST":
        try:
            raw_body = request.body.decode("utf-8")  # Decode request body
            logger.info(f"Raw Request Body: {raw_body}")  # Log raw request data
            
            data = json.loads(raw_body)  # Parse JSON safely
            user_answer = data.get("answer", "").strip()

            if not user_answer:
                logger.warning("Missing 'answer' in request data")
                return JsonResponse({"error": "No answer provided"}, status=400)

            # Construct Gemini API Prompt
            prompt = {
                "contents": [{
                    "parts": [{
                        "text": f"Evaluate this answer: {user_answer}. Provide a score (out of 10) and short feedback."
                    }]
                }]
            }

            response = requests.post(GEMINI_API_URL, json=prompt, params={"key": GEMINI_API_KEY}, timeout=10)

            if response.status_code != 200:
                logger.error(f"Gemini API error: {response.status_code} - {response.text}")
                return JsonResponse({"error": "Failed to evaluate answer"}, status=500)

            # Extract API Response Safely
            try:
                response_data = response.json()
                evaluation_text = (
                    response_data.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text", "No feedback available.")
                )
            except (json.JSONDecodeError, KeyError, IndexError):
                logger.error("Invalid response format from Gemini API")
                evaluation_text = "Error in processing evaluation."

            return JsonResponse({"evaluation": evaluation_text})

        except json.JSONDecodeError:
            logger.error("Invalid JSON format received")
            return JsonResponse({"error": "Invalid JSON data"}, status=400)
        except requests.exceptions.Timeout:
            logger.error("Request to Gemini API timed out")
            return JsonResponse({"error": "Request timed out"}, status=500)
        except requests.exceptions.RequestException as e:
            logger.error(f"Request to Gemini API failed: {e}")
            return JsonResponse({"error": "API request failed"}, status=500)
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return JsonResponse({"error": "Internal server error"}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=405)

    
# ------------------ FINAL INTERVIEW EVALUATION ------------------

@login_required
def evaluate_interview(request):
    """Evaluate all recorded answers at the end of the interview."""
    user_answers = request.session.get("user_answers", [])

    if not user_answers:
        return JsonResponse({"error": "No answers found. Please complete the interview first."}, status=400)

    model = genai.GenerativeModel("gemini-pro")
    feedback_list = []

    for item in user_answers:
        question, answer = item.get("question", "").strip(), item.get("answer", "").strip()

        if not question or not answer:
            logger.warning(f"Skipping empty question or answer: {item}")
            continue  # Skip empty responses

        prompt = f"Evaluate this answer: {answer} for the question: {question}. Provide a score (out of 10) and short feedback."

        try:
            response = model.generate_content(prompt)
            feedback_text = response.text if response else "No feedback available."
        except Exception as e:
            logger.error(f"Error generating feedback: {e}")
            feedback_text = "Evaluation failed due to an error."

        feedback_list.append({
            "question": question,
            "answer": answer,
            "feedback": feedback_text,
        })

    # Save interview responses in the database
    interview = InterviewResponse.objects.create(user=request.user, responses=feedback_list)
    
    return JsonResponse({"evaluation": feedback_list, "interview_id": interview.id})