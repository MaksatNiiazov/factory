$(function () {
	"use strict";

var BreakException = {};

// Выведет ряд с вводом информации по позиции для спецификации
let add_button = document.querySelector('.add-position');
if ( add_button ) {
    add_button.addEventListener('click', function () {
    let hidden_positions = document.querySelectorAll('.pos-visually-hidden');
    let qty = 1
    try {
    hidden_positions.forEach(function(item, i, arr ) {
        item.classList.remove("pos-visually-hidden");
        if (qty % 5 == 0 ) {
            throw BreakException
        }   else (qty ++ )
        });
        } catch (e) {
          if (e !== BreakException) throw e;
        }
    },
    false);
}

// Загрузка svg по клику на button.svg_load_button
let svg = document.querySelector('svg#svg_to_save');

let triggerDownload = (imgURI, fileName) => {

    let a = document.createElement('a')
    a.setAttribute('download', fileName + '.svg')
    a.setAttribute('href', imgURI)
    a.setAttribute('target', '_blank')

    a.click()
};

// Скачивание эскизов позиций проекта в формате svg
async function save () {
    const choices = document.querySelectorAll("input[name='make_file']:checked")

    for (let i = 0; i < choices.length; i++) {

        const response = await fetch('/ru/ops/get_sketch/' + choices[i].id)
        const content = await response.json();
        const svgBlob = new Blob([content.string_svg], {type: 'image/svg+xml;charset=utf-8'});
        const url = URL.createObjectURL(svgBlob);
        const fileName = content.filename;

        triggerDownload(url, fileName);
    }
};

// Event на кнопку для скачивания эскизов в svg
let svg_load_button = document.getElementById("svg-load");
if ( svg_load_button ) {
    svg_load_button.addEventListener('click', save);
};


// Загрузка pdf по клику на button.pdf_load_button
async function getPdf() {
    const choices = document.querySelectorAll("input[name='make_file']:checked")
    const font = await fetch('/static/fonts/OpenSans-Regular-Merged.ttf');
    const arrayBuffer = await font.arrayBuffer();

    let doc = new PDFDocument({compress: true, layout : 'landscape', size: 'A4'});
    doc.registerFont('openSans', arrayBuffer);

    for (let i = 0; i < choices.length; i++) {

        const response = await fetch('/ru/ops/get_sketch/' + choices[i].id)
        const content = await response.json();
        const fileName = content.filename;
        SVGtoPDF(doc, content.string_svg, 0, 0, { fontCallback: () => 'openSans' });
            let stream = doc.pipe(blobStream());
            stream.on('finish', () => {
                let blob = stream.toBlob('application/pdf');
                const link = document.createElement('a');
                link.href = URL.createObjectURL(blob);
                link.download = fileName + ".pdf";
                link.click();
            });
            doc.end();
    }
};

// Загрузка pdf по клику на button.pdf_new_load_button
async function getNewPdf() {
    const choices = document.querySelectorAll('input[name="make_file"]:checked');

    for(let i = 0; i < choices.length; i++) {
        const response = await fetch('/ru/ops/get_sketch_pdf/' + choices[i].id);
        const data = await response.json();

        // Декодируем base64 в Blob
        const binaryString = atob(data.output);
        const binaryLength = binaryString.length;
        const bytes = new Uint8Array(binaryLength);

        for(let j = 0; j < binaryLength; j++) {
            bytes[j] = binaryString.charCodeAt(j);
        }

        const blob = new Blob([bytes], { type: 'application/pdf' });
        const blobUrl = URL.createObjectURL(blob);

        // Создаем скрытую ссылку
        const a = document.createElement('a');
        a.href = blobUrl;
        a.download = data.filename;
        a.style.display = 'none';
        a.target = '_blank'; // Для открытия в новой вкладке

        document.body.appendChild(a);
        a.click() // Автоматически кликаем для скачивания
        document.body.removeChild(a); // Удаляем ссылку после скачивания
    }
}

// Event на кнопку для скачивания эскизов в pdf
let pdf_load_button = document.getElementById("pdf-load");

if ( pdf_load_button ) {
    pdf_load_button.addEventListener("click", getPdf);
};

// Event на кнопку для скачивания новых эскизов в pdf
let pdf_new_load_button = document.getElementById('pdf-new-load');

if (pdf_new_load_button) {
    pdf_new_load_button.addEventListener('click', getNewPdf);
};


// darkbarker`s function from crm
//делаем GET и полученный html-ответ рендерим в указанный элемент
function ajaxGetHtmlToElement(url, data, element, successFunc) {
	if (element.size() != 1)	{
		console.warn('elements not 1', element);
	}
	$.ajax({
		type: 'GET',
		url: url,
		data: data,
		dataType: 'html',
		success: function(data){
			element.html(data);
			if(successFunc) {
				successFunc();
			}
		},
	});
}

// заполнение информации по позиции проекта с ее составом
function show_pji_form (el) {
    let pji_id = el.getAttribute('data-pji-id')
    let pid = el.getAttribute('data-pid-id')
    ajaxGetHtmlToElement(
        '/ru/ops/projectitem/' + pid + '/' + pji_id ,
        {},
        $('#required-project_item'),
        function(){}
    );
    ajaxGetHtmlToElement(
        '/ru/ops/tmp_composition/' + pji_id ,
        {},
        $('#pji_tmp_composition'),
        function(){
            $('#pji_tmp_composition').css('display', '');  // Надо отобразить, так как у сохраненных projectitem есть хотя бы базовый состав
        }
    );
}

// Вывод формы для изменения/просмотра позиций в проекте
let show_pji = document.querySelectorAll('.show-pji');
if (show_pji) {
    for (let i = 0; i < show_pji.length; i++) {
        show_pji[i].addEventListener("click", function() {
            show_pji_form (show_pji[i]);
        });
    }
};

// Вызов информации по последней позиции, чтобы пусто не было, если есть хотя бы одна позиция в проекте
let last_pji = document.getElementById("last");
if ( last_pji ) {
    last_pji.click(show_pji_form (last_pji));
}


// кнопка добавления позиции
const add_pji_button = document.querySelector('.add-pji')
// Отрисовка формы для добавления новой позиции в проекте
if ( add_pji_button ) {
    add_pji_button.addEventListener("click", function() {
        let pid = $(this).closest("[data-pid]").data('pid');
        ajaxGetHtmlToElement(
            '/ru/ops/projectitem/' + pid + '/new',
            {},
             $('#required-project_item'),
            function(){}
        )
        $('#pji_tmp_composition').css('display', 'none');  // Для новых не отображаем
    })
};


// Вызов диалога для подбора пружинного блока. Учитывает уже заполненные данные в таблице projectitema
$( document ).on( "click", ".fit-spring", function() {
    const load_minus_z = $('#id_load_minus_z').val();
    const additional_load_z = $('#id_additional_load_z').val()
    const move_plus_z = $('#id_move_plus_z').val();
    const move_minus_z = $('#id_move_minus_z').val();
    const test_load_z = $('#id_test_load_z').val();
    const product_type = $('#id_product_type').val();
    const estimated_state = $('#id_estimated_state').val();

    if ( !load_minus_z ) {
        bootbox.alert('Введите значение нагрузки Z');
    } else if ( !product_type ) {
        bootbox.alert('Выберите тип продукта');
    } else {
    ajaxDialogRun({
        title: "Подбор пружинного блока",
        formUrl: '/ru/ops/spring_choice/',
        adddata: {
            'load_minus_z': load_minus_z, 'test_load_z': test_load_z,
            'additional_load_z': additional_load_z,
            'move_plus_z': move_plus_z, 'move_minus_z': move_minus_z,
            'product_type': product_type, 'estimated_state': estimated_state,
        },
        size: 'large',
        submitButtonsAuto: true,
        succesCall: function(dialog){
            // TODO Уйдем от этого, когда будем сохранять projectitem поэтапно
            const spring_type = dialog.find('#spring_type').val();
            const loadValue = dialog.find('#loadValue').val();
            const hotLoad = dialog.find('#hotLoad').val();
            const coldLoad = dialog.find('#coldLoad').val();
            const springRate = dialog.find('#springRate').val();
            const loadChange = dialog.find('#loadChange').val();
            const springReserveUp = dialog.find('#springReserveUp').val();
            const springReserveDown = dialog.find('#springReserveDown').val();
            const load_group_lgv = dialog.find('#load_group_lgv').val();
            dialog.modal('hide');  // закрываем
            $("#id_spring_block_name").val(spring_type);
            $("#id_load_group").val(loadValue);
            let spring_data = {"spring_type": spring_type, "block_size": loadValue,
                               "hot_load": hotLoad, "cold_load": coldLoad,
                               "spring_rate": springRate, "load_change": loadChange,
                               "spring_reserve_up": springReserveUp, "spring_reserver_down": springReserveDown,
                               "load_group_lgv": load_group_lgv}
            $("#id_tmp_spring").val(JSON.stringify(spring_data));
        },
    });
    }
});

// Вывод фактического размера трубы рядом с выбором номинального диаметра
$( document ).on( "change", "#id_nominal_diameter", function() {
    let dn_id = $("#id_nominal_diameter").val();
    ajaxGetHtmlToElement(
        '/ru/ops/dn_size_diameter/',
        {'dn_id': dn_id},
        $('#fill-dn-size'),
        function (){}
    )
});


// Задисейблим поля в зависимости от выбранных параметров: dn_standart = 3, значит нестандарт и спец размер для диаметра
$( document ).on( "change", "#id_dn_standard", function() {
    $('#id_nominal_diameter').prop('disabled', this.value === '3');
    $('#id_outer_diameter_special').prop('disabled', this.value !== '3');
}).change();


// Влючение/отключение всех позиций для скачивания эскизов
$( document ).on( "click", ".pick_all", function() {
    const all_choices = document.querySelectorAll("input[name='make_file']");
    for (let i = 0; i < all_choices.length; i++) {
        all_choices[i].checked = this.checked
    }
})


// Конец
});
