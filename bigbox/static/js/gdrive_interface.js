function ci_init(data, path, pk, done) {
    g_pk = pk;
    $.ajax({
        url: '/create-folder',
        method: 'POST',
        data: {'path': path, 'pk': pk, 'name': ''},
        dataType: 'json',
        success: function (data) {
            g_parent = data[pk].id;
            console.log("gdrive init success");
            done();
        },
        error: function (jqXHR, textStatus, errorThrown) {
            console.log(textStatus + ': ' + errorThrown);
        }
    });
}
function ci_chunk_size(file_size) {
    return 1 * 1024 * 1024;
}
function ci_start(uploader, done) {
    uploader.ignore_failure = true;
    $.ajax({
        url: '/get-up-creds',
        method: 'GET',
        data: {'data': JSON.stringify({'parent': g_parent, 'name': uploader.file_name}), 'pk': g_pk},
        dataType: 'json',
        success: function (data) {
            uploader.url = data.url;
            done();
        },
        error: function (jqXHR, textStatus, errorThrown) {
            uploader.fail(textStatus + ': ' + errorThrown);
        }
    });
}
function ci_prepare_chunk(uploader, chunk) {
    uploader.upload_request.open('PUT', uploader.url, true);
    uploader.upload_request.setRequestHeader('Content-Range', 'bytes ' + uploader.range_start + '-'
        + (uploader.range_end - 1) + '/' + uploader.file_size);
}
function ci_finish(uploader, done) {
    done();
}
