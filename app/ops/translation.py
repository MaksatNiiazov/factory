from modeltranslation.translator import register, TranslationOptions

from ops.models import FieldSet, Attribute


@register(FieldSet)
class FieldSetTranslationOptions(TranslationOptions):
    fields = ('label',)
    required_languages = {
        'ru': ('label',)
    }


@register(Attribute)
class AttributeTranslationOptions(TranslationOptions):
    fields = ('label', 'description')
    required_languages = {
        'ru': ('label',)
    }
