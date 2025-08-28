import shortuuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from pybarker.contrib.modelshistory.models import HistoryModelTracker

from pybarker.django.contrib.auth.models import AbstractEmailedUser
from pybarker.django.db.models import ReadableJSONField

from kernel.mixins import SoftDeleteModelMixin


class Organization(SoftDeleteModelMixin, models.Model):
    name = models.CharField(max_length=255, verbose_name=_("Наименование"))
    external_id = models.IntegerField(null=True, blank=True, unique=True, verbose_name=_("Внешний идентификатор (CRM)"))

    inn = models.CharField(max_length=64, null=True, blank=True, verbose_name=_("ИНН"))
    kpp = models.CharField(max_length=64, null=True, blank=True, verbose_name=_("КПП"))
    payment_bank = models.CharField(max_length=128, null=True, blank=True, verbose_name=_("Банк"))
    payment_account = models.CharField(max_length=64, null=True, blank=True, verbose_name=_("Расс. счет"))
    bik = models.CharField(max_length=64, null=True, blank=True, verbose_name=_("БИК"))
    correspondent_account = models.CharField(max_length=64, null=True, blank=True, verbose_name=_("Корр. счет"))

    file = models.FileField(null=True, blank=True, verbose_name=_("Файлы"), help_text=_("Свидетельство о регистрации"))

    historylog = HistoryModelTracker(excluded_fields=("id",), root_model="self", root_id=lambda ins: ins.id)

    class Meta:
        verbose_name = _("Организация")
        verbose_name_plural = _("Организации")
        default_permissions = ()
        permissions = (
            ("view_organization", _("Может просматривать организации")),
            ("add_organization", _("Может добавлять организации")),
            ("change_organization", _("Может изменять организации")),
            ("delete_organization", _("Может удалять организации")),
        )

    def __str__(self):
        return str(self.name)


class User(AbstractEmailedUser):
    INTERNAL_USER = "internal"
    EXTERNAL_USER = "external"

    STATUSES = (
        (INTERNAL_USER, _("Внутренний пользователь")),
        (EXTERNAL_USER, _("Внешний пользователь")),
    )

    organization = models.ForeignKey(
        Organization, on_delete=models.PROTECT, null=True, blank=True,
        related_name="users", verbose_name=_("Организация"),
    )

    middle_name = models.CharField(max_length=150, null=True, blank=True, verbose_name=_("Отчество"))
    status = models.CharField(max_length=255, choices=STATUSES, verbose_name=_("Статус"))

    crm_login = models.CharField(
        max_length=255, null=True, blank=True,
        verbose_name=_("Логин в CRM"), help_text=_("Для внутреннего пользователя"),
    )

    ui_config = ReadableJSONField(null=True, blank=True, verbose_name=_("Конфигурация UI"))

    historylog = HistoryModelTracker(excluded_fields=("id",), root_model="self", root_id=lambda ins: ins.id)

    class Meta(AbstractEmailedUser.Meta):
        ordering = ["email"]
        default_permissions = ()
        permissions = (
            ("view_user", _("Может просматривать пользователей")),
            ("add_user", _("Может добавлять пользователей")),
            ("change_user", _("Может изменять пользователей")),
            ("delete_user", _("Может удалять пользователей")),
        )

    @property
    def display_name(self):
        display_name = " ".join(filter(None, [self.last_name, self.first_name]))

        if display_name:
            return display_name

        return self.email

    @property
    def full_name(self):
        full_name = " ".join(filter(None, [self.last_name, self.first_name, self.middle_name]))

        if full_name:
            return full_name

        return self.email


class ApiToken(SoftDeleteModelMixin, models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="api_tokens", verbose_name=_("Пользователь"))
    token = models.CharField(max_length=32, unique=True, verbose_name=_("Токен"))

    class Meta:
        verbose_name = _("API-токен")
        verbose_name_plural = _("API-токены")
        ordering = ["user"]
        default_permissions = ()
        permissions = (
            ("view_apitoken", _("Может просматривать API-токены пользователей")),
            ("add_apitoken", _("Может добавлять API-токены пользователей")),
            ("change_apitoken", _("Может изменять API-токены пользователей")),
            ("delete_apitoken", _("Может удалять API-токены пользователей")),
        )

    @staticmethod
    def generate_unique_token():
        while True:
            token = shortuuid.uuid()
            if not ApiToken.objects.filter(token=token).exists():
                return token

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = self.generate_unique_token()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user}: {self.token}"