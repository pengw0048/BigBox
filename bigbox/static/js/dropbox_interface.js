function ci_init(data, done){
    db_token = "Bearer " + data.token;
    console.log("dropbox init success");
    done();
}
function ci_chunk_size(file_size){
    return 1*1024*1024;
}
function ci_start(uploader, done){
    $.ajax({
        url: 'https://content.dropboxapi.com/2/files/upload_session/start',
        method: 'POST',
        dataType: 'json',
        contentType: 'text/plain; charset=dropbox-cors-hack',
        headers: {
            "Authorization": db_token
        },
        xhrFields: {
            withCredentials: false
        },
        success: function(data) {
            uploader.session_id = data.session_id;
            done();
        },
        error: function(jqXHR, textStatus, errorThrown) {
            uploader.fail(textStatus + ': ' + errorThrown);
        }
    });
}
function ci_prepare_chunk(uploader, chunk){
    uploader.upload_request.open('POST', 'https://content.dropboxapi.com/2/files/upload_session/append_v2', true);
    uploader.upload_request.setRequestHeader('Content-Type', 'application/octet-stream');
    uploader.upload_request.setRequestHeader('Dropbox-API-Arg', JSON.stringify({
        'cursor': {
            'session_id': uploader.session_id,
            'offset': uploader.range_start
        }
    }));
    uploader.upload_request.setRequestHeader('Authorization', db_token);
}
function ci_finish(uploader, done){
    $.ajax({
        url: 'https://content.dropboxapi.com/2/files/upload_session/finish',
        method: 'POST',
        dataType: 'json',
        contentType: 'text/plain; charset=dropbox-cors-hack',
        headers: {
            "Authorization": db_token,
            'Dropbox-API-Arg': JSON.stringify({
                'cursor': {
                    'session_id': uploader.session_id,
                    'offset': uploader.file_size
                },
                'commit': {
                    'path': uploader.path + '/' + uploader.file_name,
                    'mode': 'overwrite'
                }
            })
        },
        xhrFields: {
            withCredentials: false
        },
        success: function(data) {
            done();
        },
        error: function(jqXHR, textStatus, errorThrown) {
            uploader.fail(textStatus + ': ' + errorThrown);
        }
    });
}
