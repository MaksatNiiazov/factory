// Код darkbarker из crm

(function( $ ){

// XXX в статью?
//	function autorenumtable(table) {
//		//1) в строках .addtablerow-num написаны номера существующих строк (сгенерированных на сервере, например)
//		//2) все строки с .addtablerow-autonum перенумеруются относительно последнего числа из п.1 (или 1, если тех нету).
//		var lastnum = 0;
//		table.find('tr').each(function () {
//            var tr = $(this);
//            //console.log(tr);
//            var td_num = tr.find('td.addtablerow-num');
//            var td_autonum = tr.find('td.addtablerow-autonum');
//			if(td_num.length){
//				lastnum = parseInt(td_num.text());
//				console.log("lastnum="+lastnum);
//			}
//			if(td_autonum.length && !tr.hasClass('addtablerow-default-tr')){
//				lastnum = lastnum + 1;
//				td_autonum.text(lastnum);
//				console.log("lastnum:="+lastnum);
//			}
//        });
//	}

	function addrow(table, settings, formset_name) {
		var settings_target_tr_find	= settings.target_tr_find;
		var settings_after_add_tr_callback = settings.after_add_tr;
		
		var lastrow = table.find(settings_target_tr_find);
		var emptyrow = table.find('.addtablerow-default-tr').clone(true);
		//console.log(lastrow);
		//console.log(emptyrow);
		emptyrow.removeClass( "addtablerow-default-tr" );
		var totalFormsInput = $('#id_'+formset_name+'-TOTAL_FORMS');
		var form_idx = parseInt(totalFormsInput.val());
		var new_tr = $( emptyrow.wrap('<div></div>').parent().html().replace(/__prefix__/g, form_idx) );
		lastrow.after( new_tr );
		totalFormsInput.val(form_idx + 1);
		settings_after_add_tr_callback(new_tr, form_idx);
		// кнопочка удаления
		{
			var lastrow = table.find(settings_target_tr_find);
			var lastrow_class = 'addtablerow-table-row-'+form_idx;
			// ставим пометку чтобы удалить (можно просто удалять родительский tr)
			lastrow.addClass(lastrow_class);
			// биндим на нужную строку клик удаляющий
			lastrow.find(".addtablerow-remove-row").bind( 'click', function(){
				$("."+lastrow_class).remove();
			});
		}
	}

    $.fn.addtablerow = function (options, formset_name) {
    	
    	var settings = $.extend({
            'target_tr_find' : 'tr:last',  // выражение поиска, которым ищется нужный tr после которого будет добавлено новое tr
            'after_add_tr': function(tr_el, form_idx){}  // метод, который вызывается после добавления tr в нужное место (надо переопределить, например, если target_tr_find непростой или добавить что-то надо для зависимых строк)
    	}, options);
    	
        this.each(function () {
            var el = $(this);
			addrow(el, settings, formset_name);
        });
        return this;
    };
})( jQuery );