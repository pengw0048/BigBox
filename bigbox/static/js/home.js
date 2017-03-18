var uploaders = [];
$(document).on("click", ".upload-to-cloud", function () {
    var self = $(this);
    var pk = self.data("pk");
    var dname = self.text();
    var classname = self.data("classname");
    $.ajax({
        url: "get-up-creds",
        data: {"pk": pk},
        method: "GET",
        dataType: "json",
        success: function (data) {
            $.getScript("static/js/" + classname + ".js", function () {
                ci_init(data);
            });
        }
    });
    $("#upload-to").text(dname);
    $("#upload-dialog").modal();
});
$(document).ready(function() {
    var upload_form = $('#upload-form'),
        file_input = $('#file-input'),
        file_list = $('#file-list');
    $('#upload-dialog').on('show.bs.modal', function (e) {
        uploaders = [];
        file_list.empty();
    });
    file_input.on('change', onFilesSelected);
    upload_form.on('submit', onFormSubmit);
    function onFilesSelected(e) {
        var files = e.target.files, file;
        for (var i = 0; i < files.length; i++) {
            file = files[i];
            uploaders.push(new ChunkedUploader(file));
            file_list.append('<tr><td><p class="name">'+file.name+'</p></td><td style="width:100%"><p class="size">'+file.size.formatBytes()+'</p>'
                + '<div class="progress progress-striped active"><div class="progress-bar progress-bar-success" style="width:0"></div></div></td>'
                + '<td style="white-space:nowrap"><button class="btn btn-primary start"><i class="glyphicon glyphicon-upload"></i><span>Start</span></button>'
                + '<button class="btn btn-warning cancel"><i class="glyphicon glyphicon-ban-circle"></i><span>Cancel</span></button></td></tr>');
        }
    }
    function onFormSubmit(e) {
        $.each(uploaders, function(i, uploader) {
            uploader.start();
        });
        e.preventDefault();
    }
});
function ChunkedUploader(file) {
    if (!this instanceof ChunkedUploader) {
        return new ChunkedUploader(file, options);
    }
    this.file = file;
    this.file_size = this.file.size;
    this.file_name = this.file.name;
    this.chunk_size = ci_chunk_size(this.file_size);
    this.range_start = 0;
    this.range_end = this.chunk_size;
    if ('mozSlice' in this.file) this.slice_method = 'mozSlice';
    else if ('webkitSlice' in this.file) this.slice_method = 'webkitSlice';
    else this.slice_method = 'slice';
    this.upload_request = new XMLHttpRequest();
    this.upload_request.onload = this._onChunkComplete.bind(this);
}
ChunkedUploader.prototype = {
    _upload: function(self) {
        var chunk;
        if (self.range_end > self.file_size) {
            self.range_end = self.file_size;
        }
        chunk = self.file[self.slice_method](self.range_start, self.range_end);
        ci_prepare_chunk(self, chunk);
        self.upload_request.send(chunk);
    },
    _onChunkComplete: function() {
        if (this.range_end === this.file_size) {
            this._onUploadComplete();
            return;
        }
        this.range_start = this.range_end;
        this.range_end = this.range_start + this.chunk_size;
        this._upload(this);
    },
    _onUploadComplete: function() {
        ci_finish(this, this._onDone);
    },
    _onDone: function(self) {
        console.log(self.file_name+" done");
    },
    start: function() {
        ci_start(this, this._upload);
    }
};
