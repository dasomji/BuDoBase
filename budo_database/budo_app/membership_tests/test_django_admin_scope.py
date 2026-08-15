from unittest.mock import Mock

from django.contrib import admin
from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase

from budo_app.admin import NotizenAdmin
from budo_app.models import Notizen


class TurnusEntryAdminScopeTests(TestCase):
    def test_superuser_without_selection_can_use_global_admin_operations(self):
        user = User.objects.create_superuser(
            "global-admin", "admin@example.test", "secret",
        )
        request = RequestFactory().get("/admin/budo_app/notizen/")
        request.user = user
        operation = Mock(return_value="allowed")
        model_admin = NotizenAdmin(Notizen, admin.site)

        result = model_admin._authorized_admin_operation(request, operation)

        self.assertEqual(result, "allowed")
        operation.assert_called_once_with(request)
        self.assertTrue(model_admin.has_module_permission(request))
