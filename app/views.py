import json
import requests
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils.timezone import now
from django.core.exceptions import ObjectDoesNotExist
from .firebase_config import db
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

def result_page(request):
    # Get evaluation data from session
    evaluation_data = request.session.get("evaluation_data", {})

    context = {
        "evaluation": evaluation_data.get("evaluation", "No evaluation available."),
        "strengths": evaluation_data.get("strengths", "No strengths detected."),
        "improvement": evaluation_data.get("improvement", "No improvement suggestions."),
        "score": evaluation_data.get("score", "N/A"),
    }

    return render(request, "result.html", context)




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

# 🔹 Initialize Gemini AI with your API key
genai.configure(api_key=GEMINI_API_KEY)
@csrf_exempt

def evaluate_interview(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            print("Received JSON:", data)

            # Ensure 'answers' exists and filter out invalid entries
            answers = [a for a in data.get("answers", []) if a and isinstance(a, dict) and "answer" in a and a["answer"].strip()]

            if not answers:
                return JsonResponse({"error": "No valid answer provided."}, status=400)

            # Extract the most recent valid answer
            last_answer = answers[-1]["answer"]
            print("Evaluating:", last_answer)

            model = genai.GenerativeModel("gemini-1.5-pro-latest")

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

            # Parse Gemini's response safely
            evaluation_data = parse_gemini_response(raw_text)

            # ✅ Store evaluation results in the session
            request.session["evaluation_data"] = evaluation_data

            # ✅ Redirect to the result page
            return redirect("/result/")

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


@login_required
def get_past_interviews(request):
    """Fetch user's past interviews and allow retakes."""
    interviews = Interview.objects.filter(user=request.user).order_by("-created_at")
    return JsonResponse({
    "previous_interviews": [
        {"id": i.id, "job_title": i.position, "score": i.final_score}  # ✅ Use 'position' instead of 'job_title'
        for i in interviews
    ]
})


@login_required
def retake_interview(request, interview_id):
    """Allows users to retake a past interview."""
    interview = Interview.objects.get(id=interview_id)
    request.session["interview_id"] = interview.id
    request.session["interview_questions"] = interview.questions
    return redirect("interview")

# from django.http import JsonResponse

# import json
# import requests
# import logging
# from django.http import JsonResponse
# from django.views.decorators.csrf import csrf_exempt

# logger = logging.getLogger(__name__)

# @csrf_exempt
# def evaluate_answer(request):
#     if request.method == "POST":
#         try:
#             raw_body = request.body.decode("utf-8")  # Decode request body
#             logger.info(f"Raw Request Body: {raw_body}")  # Log raw request data
            
#             data = json.loads(raw_body)  # Parse JSON safely
#             user_answer = data.get("answer", "").strip()

#             if not user_answer:
#                 logger.warning("Missing 'answer' in request data")
#                 return JsonResponse({"error": "No answer provided"}, status=400)

#             # Construct Gemini API Prompt
#             prompt = {
#                 "contents": [{
#                     "parts": [{
#                         "text": f"Evaluate this answer: {user_answer}. Provide a score (out of 10) and short feedback."
#                     }]
#                 }]
#             }

#             response = requests.post(GEMINI_API_URL, json=prompt, params={"key": GEMINI_API_KEY}, timeout=10)

#             if response.status_code != 200:
#                 logger.error(f"Gemini API error: {response.status_code} - {response.text}")
#                 return JsonResponse({"error": "Failed to evaluate answer"}, status=500)

#             # Extract API Response Safely
#             try:
#                 response_data = response.json()
#                 evaluation_text = (
#                     response_data.get("candidates", [{}])[0]
#                     .get("content", {})
#                     .get("parts", [{}])[0]
#                     .get("text", "No feedback available.")
#                 )
#             except (json.JSONDecodeError, KeyError, IndexError):
#                 logger.error("Invalid response format from Gemini API")
#                 evaluation_text = "Error in processing evaluation."

#             return JsonResponse({"evaluation": evaluation_text})

#         except json.JSONDecodeError:
#             logger.error("Invalid JSON format received")
#             return JsonResponse({"error": "Invalid JSON data"}, status=400)
#         except requests.exceptions.Timeout:
#             logger.error("Request to Gemini API timed out")
#             return JsonResponse({"error": "Request timed out"}, status=500)
#         except requests.exceptions.RequestException as e:
#             logger.error(f"Request to Gemini API failed: {e}")
#             return JsonResponse({"error": "API request failed"}, status=500)
#         except Exception as e:
#             logger.error(f"Unexpected error: {e}")
#             return JsonResponse({"error": "Internal server error"}, status=500)

#     return JsonResponse({"error": "Invalid request method"}, status=405)
