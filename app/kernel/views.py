import json

from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpResponse, JsonResponse
from django.utils.translation import gettext_lazy as _, activate

FRONT_TRANSLATIONS = {
    'title': _('OPS'),
    'hello_world': _('Привет, мир!'),
}


def front_language_json(request, lang):
    """
    Локали для фронта
    """
    language_codes = [lang[0] for lang in settings.LANGUAGES]

    if lang not in language_codes:
        return JsonResponse({"error": "Lang code not found"}, status=400)

    activate(lang)
    translations = json.dumps(FRONT_TRANSLATIONS, cls=DjangoJSONEncoder, ensure_ascii=False)

    response = HttpResponse(translations, content_type='application/json')
    return response
