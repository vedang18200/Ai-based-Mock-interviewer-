from django.urls import path
from .views import (
    login_view, register_view, logout_view, dashboard_view, interview_view,
    add_job_entry, start_interview_api, speech_to_text,
    submit_answer, evaluate_interview, get_past_interviews ,result_view
)

urlpatterns = [
    path('', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('logout/', logout_view, name='logout'),
    path('interview/', interview_view, name='interview_page'),

    # Job entry page
    path('add_job_entry/', add_job_entry, name='add_job_entry'),

    # API Endpoints
    path('api/start-interview/', start_interview_api, name='start_interview'),
    path('api/speech-to-text/', speech_to_text, name='speech_to_text'),
    path('api/submit-answer/', submit_answer, name='submit_answer'),
    # path('api/evaluate-answer/', evaluate_answer, name='evaluate_answer'),  # ✅ Add this line
    path('api/evaluate-interview/', evaluate_interview, name='evaluate_interview'),
    path('api/get-past-interviews/', get_past_interviews, name='get_past_interviews'),
    path("result/", result_view, name="result_page"),
]
