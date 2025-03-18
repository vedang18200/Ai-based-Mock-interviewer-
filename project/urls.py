from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # Admin panel
    path('admin/', admin.site.urls),

    # Authentication routes (Django AllAuth for Google login, etc.)
    path('accounts/', include('allauth.urls')),

    # Main app URLs (interview functionality)
    path('', include('app.urls')),

    # Social authentication (only include if using `social_django`)
    path('auth/', include('social_django.urls', namespace='social')),  
]
