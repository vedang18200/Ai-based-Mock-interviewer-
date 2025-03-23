from django.contrib import admin
from django.urls import path, include
from app.views import get_past_interviews  # Import the view function

urlpatterns = [
    # Admin panel
    path('admin/', admin.site.urls),

    # Authentication routes (Django AllAuth for Google login, etc.)
    path('accounts/', include('allauth.urls')),

    # Main app URLs (interview functionality)
    path('', include('app.urls')),

    # Social authentication (only include if using `social_django`)
    path('auth/', include('social_django.urls', namespace='social')),

    # ✅ Correct way to define the API endpoint
    path('api/get_past_interviews/', get_past_interviews, name='get_past_interviews'),
]
