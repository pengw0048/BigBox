$(document).ready(function () {
    $('.editable-text').editable();
    $('.color-picker').each(function () {
        $(this).colorpicker('setValue', $(this).children().first().css('background-color'));
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
        $(this).children().first().css('background-color', color);
        pk = $(this).data('pk');
        $('#acloud-' + pk).css('border-left-color', color);
    });
    $('.cloud-remove-link').on('click', function () {
        $('#remove-cloud').data('pk', $(this).data('pk'));
        $('#remove-cloud-button').text('Remove ' + $(this).data('name'));
    });
    $('#remove-cloud-button').on('click', function () {
        window.location.href = '/clouds/remove?pk=' + $('#remove-cloud').data('pk');
    });
    $('.progress-bar').each(function (i, self) {
        $.ajax({
            url: '/clouds/space',
            type: "GET",
            data: {'pk': $(self).data('pk')},
            dataType: "json",
            success: function (data) {
                if ('error' in data) {
                    $(self).children('span').first().text('Error: ' + data.error);
                } else {
                    $(self).children('span').first().text(formatBytes(data.used) + '/' + (data.total === -1 ? '--' : formatBytes(data.total)));
                    if (data.total !== -1) {
                        var value = 100.0 * data.used / data.total;
                        $(self).css('width', value + '%');
                        if (value > 50) $(self).css('color', 'white').css('text-shadow', '1px 1px black');
                    }
                }
            }
        });
    });
});
