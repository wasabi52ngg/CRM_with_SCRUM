from django.contrib.auth import logout, get_user_model, login as auth_login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect
from django.contrib.auth.views import LoginView, PasswordChangeView, PasswordChangeDoneView
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.views import View
from django.views.generic import CreateView, UpdateView
from .forms import (
    RegisterUserForm,
    LoginUserForm,
    ProfileUserForm,
    UserPasswordChangeForm,
    CompanyRegisterForm,
    CompanyUserRegisterForm,
)
from .models import User


class LoginUser(LoginView):
    """Представление для входа"""
    form_class = LoginUserForm
    template_name = 'accounts/login.html'
    extra_context = {'title': 'Авторизация'}

    def get_success_url(self):
        return reverse_lazy('crm:dashboard')


def logout_user(request):
    """Выход из системы"""
    logout(request)
    return HttpResponseRedirect(reverse('crm:landing'))


class RegisterUser(CreateView):
    """Регистрация обычного пользователя (клиента и т.п.)"""

    form_class = RegisterUserForm
    template_name = 'accounts/register.html'
    extra_context = {'title': 'Регистрация'}
    success_url = reverse_lazy('accounts:login')


class CompanyRegisterView(CreateView):
    """
    Регистрация компании и первого владельца.
    Это основной вход для IT‑компаний, которые будут вести проекты в системе.
    """

    form_class = CompanyRegisterForm
    template_name = 'accounts/register_company.html'
    extra_context = {'title': 'Регистрация компании'}
    success_url = reverse_lazy('accounts:login')


class CompanyUserRegisterView(CreateView):
    """
    Регистрация сотрудника в уже существующей компании по секретному коду.
    """

    form_class = CompanyUserRegisterForm
    template_name = 'accounts/register_company_user.html'
    extra_context = {'title': 'Регистрация сотрудника компании'}
    success_url = reverse_lazy('accounts:login')


class ProfileUserView(LoginRequiredMixin, UpdateView):
    """Представление для просмотра и редактирования профиля"""
    model = get_user_model()
    form_class = ProfileUserForm
    template_name = 'accounts/profile.html'
    extra_context = {'title': "Профиль пользователя"}

    def get_success_url(self):
        return reverse_lazy('accounts:profile')

    def get_object(self, queryset=None):
        return self.request.user


class UserPasswordChangeView(PasswordChangeView):
    """Представление для смены пароля"""
    form_class = UserPasswordChangeForm
    success_url = reverse_lazy('accounts:password_change_done')
    template_name = 'accounts/password_change_form.html'
    extra_context = {'title': "Смена пароля"}


class UserPasswordChangeDoneView(PasswordChangeDoneView):
    """Представление после успешной смены пароля"""
    template_name = 'accounts/password_change_done.html'
    extra_context = {'title': 'Успех'}
