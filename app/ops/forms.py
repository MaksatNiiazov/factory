from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Field

from ops.choices import EstimatedState
from ops.models import DetailType, ProjectItem, Project, TemporaryComposition

from deprecated import deprecated

from dal import autocomplete

User = get_user_model()


class LoginForm(forms.Form):
    username = forms.CharField(required=True, label=_('Логин'))
    password = forms.CharField(required=True, widget=forms.PasswordInput(), label=_('Пароль'))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            Field('username'),
            Field('password'),
            Submit('submit', _('Вход')),
        )


class RegisterForm(forms.Form):
    last_name = forms.CharField(required=True, label=_('Фамилия'))
    first_name = forms.CharField(required=True, label=_('Имя'))
    email = forms.EmailField(required=True, label=_('Электронная почта'))
    password1 = forms.CharField(required=True, widget=forms.PasswordInput(), label=_('Пароль'))
    password2 = forms.CharField(required=True, widget=forms.PasswordInput(), label=_('Подтверждение пароля'))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            Field('last_name'),
            Field('first_name'),
            Field('email'),
            Field('password1'),
            Field('password2'),
            Submit('submit', _('Регистрация')),
        )

    def clean_email(self):
        data = self.cleaned_data
        email = data['email']

        if User.objects.filter(email=email).exists():
            raise ValidationError(_('Пользователь с таким почтовым адресом уже существует'))

        return email

    def clean(self):
        data = self.cleaned_data
        password1 = data.get('password1')
        password2 = data.get('password2')

        if password1 and password2 and password1 != password2:
            raise ValidationError({'password1': _('Пароли не совпадают')})

    def save(self, commit=True):
        data = self.cleaned_data

        user = User(
            last_name=data['last_name'],
            first_name=data['first_name'],
            email=data['email'],
        )
        user.set_password(data['password1'])

        if commit:
            user.save()

        return user


class CalculateLoadForm(forms.Form):
    standard_series = forms.BooleanField(required=False, initial=True, label=_('W-серия'))
    l_series = forms.BooleanField(required=False, label=_('L-серия'))
    load_minus = forms.FloatField(required=True, label=_('Нагрузка (-)'))
    movement_plus = forms.FloatField(required=False, label=_('Перемещение (+)'))
    movement_minus = forms.FloatField(required=False, label=_('Перемещение (-)'))
    minimum_spring_travel = forms.FloatField(required=True, initial=5, label=_('Минимальный запас ход'))

    def clean(self):
        movement_plus = self.cleaned_data.get('movement_plus')
        movement_minus = self.cleaned_data.get('movement_minus')

        if movement_plus is not None and movement_minus is not None:
            raise ValidationError({'movement_plus': _('Нельзя указать оба перемещения')})

        if movement_plus is None and movement_minus is None:
            raise ValidationError({'movement_plus': _('Необходимо выбрать один из перемещении')})

        standardSeries = self.cleaned_data.get('standard_series')
        lSeries = self.cleaned_data.get('l_series')

        if not standardSeries and not lSeries:
            raise ValidationError({'l_series': _('Укажите хотя бы одну из серии')})


class SpringChoiceForm(forms.Form):
    load_plus_x = forms.FloatField(min_value=0, required=False, initial=0)
    load_plus_y = forms.FloatField(min_value=0, required=False, initial=0)
    load_plus_z = forms.FloatField(min_value=0, required=False, initial=0)
    load_minus_x = forms.FloatField(min_value=0, required=False, initial=0)
    load_minus_y = forms.FloatField(min_value=0, required=False, initial=0)
    load_minus_z = forms.FloatField(min_value=0, required=False, initial=0)
    additional_load_x = forms.FloatField(min_value=0, required=False, initial=0)
    additional_load_y = forms.FloatField(min_value=0, required=False, initial=0)
    additional_load_z = forms.FloatField(min_value=0, required=False, initial=0)
    test_load_z = forms.FloatField(min_value=0, required=False, initial=0)
    move_plus_z = forms.FloatField(min_value=0, required=False, initial=0)
    move_minus_z = forms.FloatField(min_value=0, required=False, initial=0)
    estimated_state = forms.ChoiceField(choices=EstimatedState.choices, initial=EstimatedState.COLD_LOAD)

    def clean(self):
        cleaned_data = super().clean()
        fields = [
            'load_plus_x', 'load_plus_y', 'load_plus_z', 'load_minus_x', 'load_minus_y', 'load_minus_z',
            'additional_load_x', 'additional_load_y', 'additional_load_z', 'test_load_z', 'move_plus_z', 'move_minus_z',
        ]
        for field in fields:
            cleaned_data[field] = cleaned_data.get(field) or 0

        return cleaned_data


@deprecated(reason='Скоро будет удален')
class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['number']  # 'contragent'


class ProjectItemForm(forms.ModelForm):
    standard = ((1, _('РФ')), (2, _('EN')), (3, _('Нестандартный')))
    dn_standard = forms.ChoiceField(label=_('Стандарт'), choices=standard)
    product_type = forms.ModelChoiceField(label='Тип изделия',
                                          queryset=DetailType.objects.filter(category=DetailType.PRODUCT),
                                          widget=autocomplete.ModelSelect2(url='product_type_autocomplete'))
    spring_block_name = forms.CharField(label=_('Подобранное изделие'), max_length=100, required=False)

    class Meta:
        model = ProjectItem
        fields = ['question_list', 'customer_marking', 'count',
                  'load_plus_x', 'load_plus_y', 'load_plus_z',
                  'load_minus_x', 'load_minus_y', 'load_minus_z',
                  'additional_load_x', 'additional_load_y', 'additional_load_z',
                  'test_load_x', 'test_load_y', 'test_load_z',
                  'move_plus_x', 'move_plus_y', 'move_plus_z',
                  'move_minus_x', 'move_minus_y', 'move_minus_z',
                  'estimated_state', 'ambient_temperature', 'nominal_diameter', 'outer_diameter_special',
                  'insulation_thickness', 'span', 'clamp_material', 'chain_height',
                  'tmp_spring', 'position_number', 'comment'
                  ]
        widgets = {
            'nominal_diameter': autocomplete.ModelSelect2(url='dn_autocomplete', forward=['dn_standard']),
            'clamp_material': autocomplete.ModelSelect2(
                url='clamp_material_autocomplete', forward=['ambient_temperature']
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            if self.instance.outer_diameter_special:
                self.fields['dn_standard'].initial = 3
            else:
                self.fields['dn_standard'].initial = self.instance.nominal_diameter.option
            self.fields['product_type'].initial = self.instance.original_item.type
            if getattr(self.instance, 'tmp_spring'):
                self.fields['spring_block_name'].initial = self.instance.tmp_spring.get("spring_type")
        else:
            self.fields['outer_diameter_special'].disabled = True

    def clean(self):
        # Так как состав пока временный, то проверять есть ли пружина в составе не получится
        cd = super().clean()
        product_type = cd.get('product_type')
        span = cd.get('span')

        if product_type and product_type.branch_qty == DetailType.BranchQty.TWO and not span:
            raise ValidationError({'span': _('Укажите расстояние между опорами')})


class TmpCompositionForm(forms.ModelForm):
    class Meta:
        model = TemporaryComposition
        fields = ['tmp_child', 'position', 'material', 'count']
