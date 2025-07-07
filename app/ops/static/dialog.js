// Это ДИМИН код из crm


// код элемента-ожидалки
var WAIT_ELEMENT = '<div class="wait">Загрузка…</div>';

//-----------------------------------------------------------------------------
// общий механизм диалогов
// рендерит по get урл formUrl, потом шлёт post на этот же урл
// при получении ответа "ok" вызывает колбек закрытия, при любом другом перезаполняет диалог
// внимание: для этого в содержимом должна быть html-форма
// для авторежима:
// ищутся кнопки и переносятся в диалог:
// <button type="submit" class="btn btn-primary">Сохранить</button>
// dialogclass введен для добавления класса в modal-dialog TODO удалить, когда обновимся до бутстрап 4 или 5 (можно будет исп. только size)
//-----------------------------------------------------------------------------
function ajaxDialogRun(options) {

	var options = $.extend({
        'title': 'Диалог',
        'formUrl': 'param-formUrl-not-provided',
		'submitLabel': 'Отправить',
		'submitButtonsAuto': false,
		'succesCall': function(dialog){alert('param succesCall not provided');},
		'afterFillCall': null,
		'adddata': {},
		'size': null,
		'dialogclass': null,
	}, options);

	// нажатие на кнопку диалога обработка
	function button_press(dialog, button_name) {
      	// отправка формы
		dialog.find("form").ajaxSubmit({
			type: 'POST',
			url: options.formUrl,
			data: $.extend({"_dialog_submit_name": button_name}, options.adddata),
			beforeSubmit: function showRequest(formData, jqForm, _options) {
				//dialog.find('.dialog_submit_button').button('loading');
				dialog.find('.dialog_submit_button').prop('disabled', true);
				//dialog.find('.dialog_submit_button').html("..."+options.submitLabel);
			},
			success: function(responseText, statusText, xhr, $form) {
				if( responseText=="ok" ) {
					options.succesCall(dialog);
				} else {
					if(options.submitButtonsAuto) {
						var [responseText, buttons] = found_and_cut_button(responseText);
						button_set(dialog, buttons);
					}
					// обновляем форму (там и ошибки будут)
					dialog.find(".modal-body").html(responseText);
					if(options.afterFillCall) {
						options.afterFillCall(dialog);
					}
				}
			},
			complete: function(){
				//dialog.find('.dialog_submit_button').button('reset');
				dialog.find('.dialog_submit_button').prop('disabled', false);
				//dialog.find('.dialog_submit_button').text(options.submitLabel);
			},
	   	});
	}

	// пустой диалог
	var dialog = bootbox.dialog({
		title: options.title,
		message: WAIT_ELEMENT,
		onEscape: true,
		size: options.size,
		buttons: {
			button1: {
	      		label: "Кнопка 1",
	      		className: "btn-default dialog_submit_button",
	      		callback: function(e) {
					var button_name = e.target.name;
					button_press(dialog, button_name);
					return false;
	      		},
		    },
			button2: {
	      		label: "Кнопка 2",
	      		className: "btn-default dialog_submit_button",
	      		callback: function(e) {
					var button_name = e.target.name;
					button_press(dialog, button_name);
					return false;
	      		},
		    },
			button3: {
	      		label: "Кнопка 3",
	      		className: "btn-primary dialog_submit_button",
	      		callback: function(e) {
					var button_name = e.target.name;
					button_press(dialog, button_name);
					return false;
	      		},
		    },
	  	},
	});

	// {title, name, class}
	function button_set(dialog, buttons) {
		// все прячем
		dialog.find(".modal-footer .dialog_submit_button").hide();
		// все перебираем
		buttons.forEach(function(value, index){
			var btn = dialog.find(".modal-footer .dialog_submit_button:nth-child("+(index+1)+")");
			btn.html(value.title);
			btn.attr("class", "dialog_submit_button "+value.class);
			btn.attr("name", value.name);
			btn.show();
		});
	}

	// находит в данных кнопки и возвращает [data обрезанную, массив для button_set];
	// <button type="submit" class="{class}" name="{name}">{title}</button>
	function found_and_cut_button(data) {
		var html = $("<div>"+data+"</div>");
		var found_submits = [];
		html.find("button[type='submit']").each(function(i, v){
			var v = $(v);
			found_submits.push({title: v.text(), name: v.attr("name"), class: v.attr("class")});
			v.remove();
		});
		return [html, found_submits]
	}

	// убираем все кнопки для авторежима сразу
	// а для обычного - оставляем одну кнопку просто
	if(options.submitButtonsAuto) {
		button_set(dialog, []);
	} else {
		button_set(dialog, [{title: options.submitLabel, name: "main", class: "btn btn-primary"}]);
	}

	// запрос и заполнение диалога формой
	$.ajax({
		type: 'GET',
		url: options.formUrl,
		data: options.adddata,
		dataType: 'html',
		success: function(data){
			if(options.submitButtonsAuto) {
				var [data, buttons] = found_and_cut_button(data);
				button_set(dialog, buttons);
			}
			dialog.find(".modal-body").html(data);
            // Добавим
			if (options.dialogclass) {
			    dialog.find(".modal-dialog").addClass(options.dialogclass);
			}
			if(options.afterFillCall) {
				options.afterFillCall(dialog);
			}
		},
		error: function(){
			data = '<div class="alert alert-danger">Ошибка запроса формы, см. справа подробности</div>';
			dialog.find(".modal-body").html(data);
		},
	});
}