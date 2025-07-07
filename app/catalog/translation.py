from modeltranslation.translator import register, TranslationOptions

from catalog.models import Material, CoveringType, Covering


@register(Material)
class MaterialTranslationOptions(TranslationOptions):
    fields = ('name',)

    required_languages = {
        'ru': ('name',)
    }


@register(CoveringType)
class CoveringTypeTranslationOptions(TranslationOptions):
    fields = ('name', 'description')

    required_languages = {
        'ru': ('name',)
    }


@register(Covering)
class CoveringTranslationOptions(TranslationOptions):
    fields = ('name', 'description')

    required_languages = {
        'ru': ('name',)
    }
