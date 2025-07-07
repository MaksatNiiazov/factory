import base64
import json
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.contrib.auth import login, authenticate, logout
from django.forms.models import inlineformset_factory
from django.shortcuts import render, redirect, get_object_or_404
from django.http import (
    HttpResponseNotFound, HttpResponse, HttpResponseBadRequest, HttpResponseRedirect, JsonResponse, HttpRequest,
)
from django.views.generic import ListView
from django.urls import reverse

from constance import config
from dal import autocomplete

from catalog.models import PipeDiameter, LoadGroup, Material
from ops.choices import ProjectStatus, LoadUnit, MoveUnit, TemperatureUnit

from ops.forms import (
    CalculateLoadForm, LoginForm, RegisterForm, ProjectForm, ProjectItemForm, TmpCompositionForm, SpringChoiceForm,
)
from ops.import_project import import_project_from_file
from ops.models import Project, ProjectItem, Item, Variant, DetailType, TemporaryComposition
from ops.loads.utils import get_suitable_loads
from ops.sketch.pdf import render_sketch_pdf
from ops.utils import render_sketch

logger = logging.getLogger(__name__)


def login_page(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)

        if form.is_valid():
            data = form.cleaned_data

            user = authenticate(username=data['username'], password=data['password'])

            if user:
                login(request, user)
                return redirect('index')
    else:
        form = LoginForm()

    context = {
        'form': form,
    }

    return render(request, 'ops/login.html', context=context)


def logout_page(request):
    logout(request)
    return redirect('index')


def register_page(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)

        if form.is_valid():
            user = form.save()
            return redirect('index')
    else:
        form = RegisterForm()

    context = {
        'form': form,
    }

    return render(request, 'ops/register.html', context=context)


def index(request):
    context = {}

    if request.method.lower() == 'post':
        form = CalculateLoadForm(request.POST)

        if form.is_valid():
            load_minus = form.cleaned_data['load_minus']
            movement_plus = form.cleaned_data.get('movement_plus') if form.cleaned_data.get('movement_plus') else 0
            movement_minus = form.cleaned_data.get('movement_minus') if form.cleaned_data.get('movement_minus') else 0
            minimum_spring_travel = form.cleaned_data['minimum_spring_travel']
            standard_series = form.cleaned_data.get('standard_series')
            l_series = form.cleaned_data.get('l_series')

            context['loads'] = []
            context['best_load'] = None

            if standard_series:
                from ops.loads.standard_series import (
                    MAX_SIZE as MAX_SIZE_STANDARD, LOADS as LOADS_STANDARD,
                    SPRING_STIFFNESS_LIST as SPRING_STIFFNESS_LIST_STANDARD,
                )

                best_load, loads_standard = get_suitable_loads(
                    'standard_series', MAX_SIZE_STANDARD, load_minus, movement_plus, movement_minus,
                    minimum_spring_travel, best_suitable_load=context['best_load'],
                )
                context['loads'].extend(loads_standard)
                context['best_load'] = best_load

            if l_series:
                from ops.loads.l_series import (
                    MAX_SIZE as MAX_SIZE_L, LOADS as LOADS_L, SPRING_STIFFNESS_LIST as SPRING_STIFFNESS_LIST_L,
                )

                best_load, loads_l_series = get_suitable_loads(
                    'l_series', MAX_SIZE_L, load_minus, movement_plus, movement_minus, minimum_spring_travel,
                    best_suitable_load=context['best_load'],
                )
                context['loads'].extend(loads_l_series)
                context['best_load'] = best_load

            # TODO: Решение временное, пока api не будет (Только в демонстративных целях)
            context['json_loads'] = json.dumps(context['loads'])
    else:
        form = CalculateLoadForm()

    context['form'] = form

    return render(request, 'ops/index.html', context=context)


# Перечень проектов
class ProjectList(ListView):
    model = Project


# Проект
def project_page(request, pid, pji_id=None):
    try:
        if pid == 'new':
            project = Project(owner=request.user, status=ProjectStatus.DRAFT, load_unit=LoadUnit.KN,
                              move_unit=MoveUnit.MM, temperature_unit=TemperatureUnit.CELSIUS)
        else:
            project = Project.objects.get(pk=int(pid))
    except Project.DoesNotExist:
        return HttpResponseNotFound(f'project with id = {pid} is not found')
    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
    else:
        form = ProjectForm(instance=project)

    if project.id:
        object_list = ProjectItem.objects.filter(project=project).order_by('id')
        last_pji = object_list.last().id if object_list else None
        if pji_id:
            last_pji = int(pji_id)
    else:
        object_list = ProjectItem.objects.none()
        last_pji = None

    return render(request, 'ops/project_page.html', {'project_form': form, 'project': project,
                                                     'object_list': object_list, 'last_pji': last_pji})


# Позиция проекта
def projectitem(request, pid, pji_id):
    project = Project.objects.get(pk=int(pid))
    if pji_id == 'new':
        next_position = project.items.count() + 1
        pji = ProjectItem(project=project, position_number=next_position, comment=config.COMMON_COMMENT)
    else:
        try:
            pji = ProjectItem.objects.get(pk=int(pji_id))
        except ProjectItem.DoesNotExist:
            return HttpResponseNotFound(f'projectitem with id = {pid} is not found')
    if request.method == "POST":
        form = ProjectItemForm(data=request.POST, instance=pji)
        if form.is_valid():
            product_type = form.cleaned_data.get('product_type')
            # TODO тут, конечно, надо айдишники получать для load_group и spring_chosen, но пока так будет
            variant = Variant.objects.filter(
                deleted_at=None,
                detail_type=product_type.id).first()  # Для продукции пока он будет один, если больше, то выбирать на этапе формы
            marking = form.cleaned_data.get('customer_marking')
            tmp_spring = form.cleaned_data.get('tmp_spring')
            load_group = LoadGroup.objects.get(lgv=tmp_spring.get('load_group_lgv'))
            material = form.cleaned_data.get('clamp_material')
            branch_qty = form.cleaned_data.get('branch_qty')
            span = form.cleaned_data.get('span')

            # TODO: Проверить на ошибку
            # parameters = {"height": form.cleaned_data.get('chain_height')}
            # if branch_qty == DetailType.BranchQty.TWO:
            #     parameters.update({'span': span})

            # TODO: Найти лучший способ
            parameters = {
                "load_group": load_group.id,
            }

            item, created = Item.objects.get_or_create(
                type=product_type, variant=variant, inner_id=None,
                name=tmp_spring.get('spring_name'),
                marking=marking, comment=None, load_group=load_group,
                weight=None, material=material, author=request.user,
                parameters=parameters,
            )
            if created:
                TemporaryComposition.objects.add_tmp_composition(item)
            #  Чтобы тут сохранить пришлось пока сделать original_item c null=True.
            obj = form.save(commit=False)
            obj.original_item = item
            obj.save()
            return HttpResponseRedirect(reverse('project_page_with_pji', args=[project.pk, pji.id]))
        return render(request, 'ops/form_field_errors.html', {'errors': form.errors, 'form': form})
    else:
        form = ProjectItemForm(instance=pji)
    return render(request, 'ops/projectitem_form.html', {'form': form, 'project': project, 'pji_id': pji_id})


# Временный состав изделий
def tmp_composition(request, pji_id):
    try:
        pji = ProjectItem.objects.get(pk=int(pji_id))
        item = pji.original_item
    except ProjectItem.DoesNotExist:
        return HttpResponseNotFound(f'projectitem with id = {pji_id} is not found')
    if not item:
        return HttpResponseNotFound(f'Item product for projectitem with  id = {pji_id} is not found')
    tmp_formset = inlineformset_factory(Item, TemporaryComposition, extra=0, form=TmpCompositionForm)
    composition = TemporaryComposition.objects.filter(tmp_parent=item).order_by('position')
    if request.method == "POST":
        formset = tmp_formset(data=request.POST, instance=item)
        if formset.is_valid():
            formset.save()
            return HttpResponseRedirect(reverse('project_page_with_pji', args=[pji.project.pk, pji.id]))
        return render(request, 'ops/formset_errors.html', {'errors': formset.errors})
    else:
        formset = tmp_formset(instance=item, queryset=composition)
    return render(request, 'ops/tmp_composition.html', {'formset': formset, 'pji': pji})


# Подбор пружинных опор переменного усилия
def spring_choice(request):
    if request.method == "POST" and request.POST["_dialog_submit_name"] == "save":
        return HttpResponse('ok')
    else:
        context = {}

        form = SpringChoiceForm(request.GET)

        if not form.is_valid():
            return HttpResponseBadRequest(form.errors)

        minimum_spring_travel = 5  # TODO: Константа, может с фронта?

        # TODO Тут некрасиво, но этого не будет, когда будем айдишник передавать и сохранять поэтапно:
        load_plus_x = form.cleaned_data['load_plus_x']
        load_plus_y = form.cleaned_data['load_plus_y']
        load_plus_z = form.cleaned_data['load_plus_z']

        load_minus_x = form.cleaned_data['load_minus_x']
        load_minus_y = form.cleaned_data['load_minus_y']
        load_minus_z = form.cleaned_data['load_minus_z']

        additional_load_x = form.cleaned_data['additional_load_x']
        additional_load_y = form.cleaned_data['additional_load_y']
        additional_load_z = form.cleaned_data['additional_load_z']

        if additional_load_z:
            load_minus_z += additional_load_z

        test_load_z = form.cleaned_data['test_load_z']
        move_plus_z = form.cleaned_data['move_plus_z']
        move_minus_z = form.cleaned_data['move_minus_z']

        estimated_state = form.cleaned_data['estimated_state']

        product_type = int(request.GET.get('product_type'))
        pt_obj = DetailType.objects.get(pk=product_type)

        if pt_obj.branch_qty and pt_obj.branch_qty == DetailType.BranchQty.TWO:
            load_minus_z = load_minus_z / 2
        context['pt_name'] = pt_obj.designation

        from ops.loads.standard_series import (
            MAX_SIZE as MAX_SIZE_STANDARD, LOADS as LOADS_STANDARD,
            SPRING_STIFFNESS_LIST as SPRING_STIFFNESS_LIST_STANDARD,
        )
        from ops.loads.l_series import (
            MAX_SIZE as MAX_SIZE_L, LOADS as LOADS_L,
            SPRING_STIFFNESS_LIST as SPRING_STIFFNESS_LIST_L,
        )

        context['loads'] = []
        context['best_load'] = None

        best_load, loads_standard = get_suitable_loads(
            'standard_series', MAX_SIZE_STANDARD, load_minus_z, move_plus_z, move_minus_z,
            minimum_spring_travel, estimated_state=estimated_state, best_suitable_load=context['best_load'],
        )
        context['loads'].extend(loads_standard)
        context['best_load'] = best_load

        best_load, loads_l = get_suitable_loads(
            'l_series', MAX_SIZE_L, load_minus_z, move_plus_z, move_minus_z, minimum_spring_travel,
            estimated_state=estimated_state, best_suitable_load=context['best_load'],
        )
        context['loads'].extend(loads_l)
        context['best_load'] = best_load

        context['json_loads'] = json.dumps(context['loads'])
        return render(request, 'ops/spring_choice.html', context=context)


# Фактический размер диаметра трубы
def dn_size_diameter(request):
    dn_id = request.GET.get('dn_id')
    if dn_id and dn_id.isdigit():
        try:
            pipe = PipeDiameter.objects.get(pk=int(dn_id))
            return HttpResponse(pipe.size)
        except PipeDiameter.DoesNotExist:
            return HttpResponseNotFound(f'pipediameter with id = {dn_id} is not found')
    return HttpResponseBadRequest('Что-то пошло не так')


# Автокомплит диаметров с зависимостью от выбранного стандарта (RF/EN)
class DnAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        # Don't forget to filter out results depending on the visitor !
        if not self.request.user.is_authenticated:
            return PipeDiameter.objects.none()
        qs = PipeDiameter.objects.all()
        dn_standard = self.forwarded.get("dn_standard", None)
        if dn_standard:
            qs = qs.filter(standard=dn_standard)
        if self.q:
            qs = qs.filter(dn__dn__icontains=self.q)
        return qs


# Автокомплит материала в зависимости от Температуры среды
class ClampMaterialAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Material.objects.none()
        qs = Material.objects.all()

        ambient_temperature = self.forwarded.get('ambient_temperature', None)

        if ambient_temperature:
            qs = qs.filter(
                Q(min_temp__isnull=True, max_temp__isnull=True) |
                Q(min_temp__isnull=True, max_temp__gte=ambient_temperature) |
                Q(max_temp__isnull=True, min_temp__lte=ambient_temperature) |
                Q(min_temp__lte=ambient_temperature, max_temp__gte=ambient_temperature)
            )
        if self.q:
            qs = qs.filter(name__icontains=self.q)
        return qs


# Автокомплит изделий! из DetailType в зависимости от того, какой вид (одинарный / двойной ) выбран
class DetailTypeAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        # Don't forget to filter out results depending on the visitor !
        if not self.request.user.is_authenticated:
            return DetailType.objects.none()
        qs = DetailType.objects.filter(category=DetailType.PRODUCT)
        if self.q:
            qs = qs.filter(designation__icontains=self.q)
        return qs


# Формирование эскиза на бэке
def get_sketch(request, pid):
    pji = ProjectItem.objects.get(pk=int(pid))

    try:
        string_svg, filename = render_sketch(request, pji)
        string_svg = string_svg.decode()
    except Exception as exc:
        raise exc

    return JsonResponse({"string_svg": string_svg, "filename": filename})


def get_sketch_pdf(request, project_item_id):
    project_item = ProjectItem.objects.get(pk=project_item_id)

    try:
        output, filename = render_sketch_pdf(project_item, request.user)
    except Exception as exc:
        raise exc

    return JsonResponse({'output': base64.b64encode(output).decode('utf-8'), 'filename': filename})


def download_sketch_pdf(request, project_item_id):
    project_item = ProjectItem.objects.get(pk=project_item_id)

    try:
        output, filename = render_sketch_pdf(project_item, request.user)
    except Exception as exc:
        raise exc

    # Создаём HTTP-ответ для возврата PDF
    response = HttpResponse(output, content_type='application/pdf')

    return response


def copy_pji(request, pji_id):
    try:
        pji = ProjectItem.objects.get(pk=int(pji_id))
    except ProjectItem.DoesNotExist:
        return HttpResponseNotFound(f'projectitem with id = {pji_id} is not found')
    new = pji
    new.id = None
    # TODO тут есть проблема: если удалить третью позицию из 4х, потом падает из-за
    #  unique_together(project и position_number) Может, перетереть? Уточнить
    new.position_number = pji.project.items.count() + 1
    new.save()
    return HttpResponseRedirect(reverse('project_page_with_pji', args=[pji.project.pk, new.id]))


def delete_pji(request, pji_id):
    try:
        pji = ProjectItem.objects.get(pk=int(pji_id))
    except ProjectItem.DoesNotExist:
        return HttpResponseNotFound(f'projectitem with id = {pji_id} is not found')
    project = pji.project
    pji.delete()
    object_list = ProjectItem.objects.filter(project=project).order_by('id')
    if object_list:
        last_pji = object_list.last().id
        return HttpResponseRedirect(reverse('project_page_with_pji', args=[project.pk, last_pji]))
    return HttpResponseRedirect(reverse('project_page', args=[project.pk]))


@login_required
def import_project(request: HttpRequest, project_id: int) -> HttpResponse:
    """
    Импорт данных в проект с загруженного файла. Принимает xlsx-файл и обновляет проект.
    """
    project = get_object_or_404(Project, pk=project_id)

    if request.method == 'POST':
        if 'import_file' not in request.FILES:
            messages.error(request, 'Файл не найден. Загрузите xlsx-файл.')
            return redirect(reverse('project_page', args=(project.id,)))

        import_file = request.FILES['import_file']

        try:
            with transaction.atomic():
                import_project_from_file(project, import_file, request.user)
        except Exception as exc:
            logger.exception("Exception when importing project from file")
            messages.error(request, 'Произошла ошибка: ' + str(exc))
            return redirect(reverse('project_page', args=(project.id,)))

        return redirect(reverse('project_page', args=(project.id,)))
