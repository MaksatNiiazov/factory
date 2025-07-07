from django.forms import TextInput


class MarkingTemplateWidget(TextInput):
    template_name = 'ops/widgets/marking_template.html'

    class Media:
        css = {
            'all': ('ops/modal.css', 'ops/widgets/marking_template.css',),
        }
        js = (
            'https://cdnjs.cloudflare.com/ajax/libs/axios/1.5.1/axios.min.js',
            'https://unpkg.com/micromodal/dist/micromodal.min.js',
            'ops/widgets/marking_template.js',
        )
