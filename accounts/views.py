from django.contrib.auth import logout, get_user_model, login as auth_login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect
from django.contrib.auth.views import LoginView, PasswordChangeView, PasswordChangeDoneView
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.views import View
from django.views.generic import CreateView, UpdateView, TemplateView
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
        # Если есть параметр next, используем его
        next_url = self.request.GET.get('next')
        if next_url:
            return next_url
        return reverse_lazy('crm:dashboard')


def logout_user(request):
    """Выход из системы"""
    logout(request)
    return HttpResponseRedirect(reverse('crm:landing'))


class RegisterUser(CreateView):
    """Регистрация сотрудника компании (с кодом компании) или обычного пользователя"""

    form_class = RegisterUserForm
    template_name = 'accounts/register.html'
    extra_context = {'title': 'Регистрация сотрудника'}

    def get_success_url(self):
        # Если был указан код компании, показываем сообщение о подтверждении
        if hasattr(self, 'company_code_used') and self.company_code_used:
            return reverse_lazy('accounts:register_success')
        # Если есть параметр next, логиним пользователя и редиректим туда
        next_url = self.request.GET.get('next')
        if next_url:
            # Автоматически логиним пользователя после регистрации
            from django.contrib.auth import login
            login(self.request, self.object)
            return next_url
        return reverse_lazy('accounts:login')

    def form_valid(self, form):
        company_code = form.cleaned_data.get('company_code', '').strip()
        self.company_code_used = bool(company_code)
        return super().form_valid(form)


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

    def form_valid(self, form):
        messages.success(self.request, "Профиль сохранён.")
        return super().form_valid(form)


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


class RegisterSuccessView(TemplateView):
    """Страница успешной регистрации с ожиданием подтверждения"""
    template_name = 'accounts/register_success.html'
    extra_context = {'title': 'Регистрация успешна'}
