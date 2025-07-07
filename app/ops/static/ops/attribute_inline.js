window.addEventListener("load", function() {
    (function($) {
        $(document).ready(function() {
            function toggleField(target) {
                const selectedChoice = target.val();

                const catalogId = '#' + target.attr('id').replace('-type', '-catalog');

                if (selectedChoice === 'catalog') {
                    $(catalogId).closest('.form-row').show();
                } else {
                    $(catalogId).closest('.form-row').hide();
                }
            }

            function toggleFieldEvent(event) {
                toggleField($(event.target));
            }

            $('.field-type select').each(function() {
                toggleField($(this));
                $(this).on('change', toggleFieldEvent);
            })
        });
    })(django.jQuery);
})