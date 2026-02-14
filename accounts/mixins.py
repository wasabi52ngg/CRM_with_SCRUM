from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin


class ManagerRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False
        # Проверяем через CompanyMembership
        return user.company_memberships.filter(
            is_approved=True
        ).filter(
            is_manager=True
        ).exists() or user.company_memberships.filter(
            is_approved=True
        ).filter(
            is_owner=True
        ).exists()


class DeveloperRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False
        # Проверяем через CompanyMembership
        return user.company_memberships.filter(
            is_approved=True
        ).filter(
            is_developer=True
        ).exists() or user.company_memberships.filter(
            is_approved=True
        ).filter(
            is_owner=True
        ).exists()


class RoleAllowedMixin(LoginRequiredMixin, UserPassesTestMixin):
    allowed_roles = ()

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and user.role in self.allowed_roles


class ClientRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False
        # Клиент - это пользователь с ролью CLIENT, который не является менеджером или разработчиком в компании
        if user.role != user.Role.CLIENT:
            return False
        # Проверяем, что пользователь не является менеджером или разработчиком в компании
        has_company_role = user.company_memberships.filter(
            is_approved=True
        ).filter(
            is_manager=True
        ).exists() or user.company_memberships.filter(
            is_approved=True
        ).filter(
            is_developer=True
        ).exists() or user.company_memberships.filter(
            is_approved=True
        ).filter(
            is_owner=True
        ).exists()
        return not has_company_role


