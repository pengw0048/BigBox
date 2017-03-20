function ci_init(data, path, pk, done){
    od_pk = pk;
    od_path = path;
    console.log("onedrive init success");
    done();
}
function ci_chunk_size(file_size){
    return 4*320*1024;
}
function ci_start(uploader, done){
    $.ajax({
        url: '/get-up-creds',
        method: 'GET',
        data: {'data': JSON.stringify({'path': od_path, 'name': uploader.file_name}), 'pk': od_pk},
        dataType: 'json',
        success: function(data) {
            uploader.url = data.url;
            done();
        },
        error: function(jqXHR, textStatus, errorThrown) {
            uploader.fail(textStatus + ': ' + errorThrown);
        }
    });
}
function ci_prepare_chunk(uploader, chunk){
    uploader.upload_request.open('PUT', uploader.url, true);
    uploader.upload_request.setRequestHeader('Content-Range', 'bytes ' + uploader.range_start + '-'
        + (uploader.range_end-1) + '/' + uploader.file_size);
}
function ci_finish(uploader, done){
    done();
}
