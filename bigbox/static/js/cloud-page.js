$(document).ready(function() {
    $('.color-picker').each(function () {
        $(this).colorpicker('setValue', $(this).css('color'));
    }).on('hidePicker', function () {
        me = $(this);
        color = me.data('colorpicker').color.toHex();
        pk = me.data('pk');
        $.ajax({
            url: '/clouds/color',
            type: "POST",
            data: {'pk': pk, 'value': color},
            dataType: "json"
        })
    }).on('changeColor', function () {
        color = $(this).data('colorpicker').color.toHex();
        $(this).css('color', color);
        pk = $(this).data('pk');
        $('#acloud-' + pk).css('border-left-color', color);
    });
});