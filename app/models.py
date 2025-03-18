from django.db import models
from django.contrib.auth.models import User
from django.contrib.postgres.fields import ArrayField  # For storing lists
from django.db import models
from django.contrib.auth.models import User

from django.db import models
from django.contrib.auth.models import User

class Interview(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="interviews")
    position = models.CharField(max_length=255)
    description = models.TextField()
    experience = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    final_score = models.FloatField(null=True, blank=True)
    questions = models.JSONField(blank=True, null=True)  # ✅ Fix: Replaced ArrayField with JSONField
    answers = models.JSONField(blank=True, null=True)  # ✅ Fix: Replaced ArrayField with JSONField
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    def __str__(self):
        return f"{self.position} - {self.user.username}"


class JobEntry(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=255)
    description = models.TextField()
    experience = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.role} - {self.user.username}"

class InterviewResponse(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="interview_responses")
    responses = models.JSONField()  # Store answers and feedback as JSON
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Interview Response - {self.user.username} ({self.created_at})"