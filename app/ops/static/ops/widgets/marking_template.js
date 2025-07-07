let widgetName;

const markingTemplateTestOnClick = target => {
    django.jQuery(function($) {
        $('.marking-template-input').val('');
        $('#markingTemplateResult').val('');

        widgetName = $(target).parent().parent().find('input').attr('name');

        const input = document.querySelector(`input[name="${widgetName}"]`);
        const markingTemplate = input.value;

        if(!markingTemplate) {
            alert("Шаблон в поле отсутствует");
            return
        }

        const widget = $(target).parent().parent().parent().find('.modal');
        widget.attr('id', 'modal');

        MicroModal.show('modal');
    })
}

function markingTemplateCheckFormOnChange(e) {
    e.preventDefault();

    django.jQuery(function($) {
        const value = $('.marking-template-input').val();

        if(!value) {
            alert("Введите параметры");
            return;
        }

        let json_parsed;

        try {
            jsonParsed = JSON.parse(value);
        } catch(e) {
            alert("Произошла ошибка при парсинге JSON-параметров");
            return;
        }

        const input = document.querySelector(`input[name="${widgetName}"]`);
        const markingTemplate = input.value;

        axios.post('/api/marking_template/compile/', {
            "marking_template": markingTemplate,
            "parameters": jsonParsed,
        }).then(response => {
            $('#markingTemplateResult').val(response.data.result);
        }).catch(error => {
            console.log(error);
            alert("Произошла ошибка");
        });
    });
}

document.addEventListener("DOMContentLoaded", function(event) {
    MicroModal.init();
    django.jQuery(function($) {
        $('#markingTemplateCheckForm').submit(markingTemplateCheckFormOnChange);
    });
});