from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from . import views as v

urlpatterns = [
    path("health/", v.health),
    path("auth/register/", v.register),
    path("auth/login/", TokenObtainPairView.as_view()),
    path("auth/refresh/", TokenRefreshView.as_view()),
    path("auth/me/", v.me),
    path("meta/", v.meta),
    path("demo/seed/", v.seed_demo),
    # Module 1
    path("payments/simulate/", v.payment_simulate),
    path("payments/", v.payments_view),
    path("payments/<int:pk>/advance/", v.payment_advance),
    # Module 2
    path("fx/scenarios/", v.fx_scenarios),
    path("fx/pnl/", v.fx_pnl),
    path("fx/exposures/", v.exposures),
    path("fx/exposures/<int:pk>/", v.exposure_detail),
    path("fx/exposure-summary/", v.exposure_summary),
    path("fx/forward/", v.forward_sim),
    path("fx/forwards/", v.forwards),
    path("fx/hedge/", v.hedge),
    # Module 3
    path("optimizer/compare/", v.optimizer),
    # Module 4
    path("dashboard/", v.dashboard),
    # Module 5
    path("ai/recommend/", v.ai_recommend),
    path("ai/history/", v.ai_history),
    path("ai/models/", v.ai_models),
]
