from django.urls import path

from .views.auth import (
    BrandedLoginView,
    BrandedLogoutView,
    BrandedPasswordResetCompleteView,
    BrandedPasswordResetConfirmView,
    BrandedPasswordResetDoneView,
    BrandedPasswordResetView,
)

urlpatterns = [
    path("login/", BrandedLoginView.as_view(), name="account_login"),
    path("logout/", BrandedLogoutView.as_view(), name="account_logout"),
    path("password/reset/", BrandedPasswordResetView.as_view(), name="account_reset_password"),
    path("password/reset/done/", BrandedPasswordResetDoneView.as_view(), name="account_reset_password_done"),
    path(
        "password/reset/key/<uidb64>/<token>/",
        BrandedPasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "password/reset/key/done/",
        BrandedPasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),
]
