var csrftoken = Cookies.get('csrftoken');
function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}
$.ajaxSetup({
    xhrFields: {
        withCredentials: true
    },
    beforeSend: function (xhr, settings) {
        if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        }
    },
    cache: true
});
function formatBytes (bytes) {
    bytes = Number(bytes);
    var units = ['B', 'KB', 'MB', 'GB', 'TB'],
        i;

    for (i = 0; bytes >= 1024 && i < 4; i++) {
        bytes /= 1024;
    }
    return bytes.toFixed(2) + units[i];
}
Number.prototype.formatBytes = function() {
    formatBytes(this);
};
var regexName = /^[^\\\/?%*:|"<>]{1,100}$/;
$('.name-input').on('change', function () {
    if ($(this).val().match(regexName)) {
        $(this).siblings('.errmsg').addClass('hidden');
        $(this).parent().removeClass('has-error');
    } else {
        $(this).siblings('.errmsg').removeClass('hidden');
        $(this).parent().addClass('has-error');
    }
});
