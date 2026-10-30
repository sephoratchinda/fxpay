from django.contrib import admin
from .models import AIRecommendation, ExposurePosition, ForwardContract, Transaction

for m in (Transaction, ExposurePosition, ForwardContract, AIRecommendation):
    admin.site.register(m)
