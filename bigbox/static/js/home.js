var uploaders = [];
$(document).on("click", ".upload-to-cloud", function () {
    var self = $(this);
    var pk = self.data("pk");
    var dname = self.text();
    var classname = self.data("classname");
    var path = self.data("path");
    $("#upload-form").hide().data("path", path);
    $("#upload-loader").show();
    $.ajax({
        url: "/get-up-creds",
        data: {"pk": pk},
        method: "GET",
        dataType: "json",
        success: function (data) {
            $.getScript("/static/js/" + classname + ".js", function () {
                ci_init(data, path, pk, function(){
                    $("#upload-form").show();
                    $("#upload-loader").hide();
                });
            });
        }
    });
    $("#upload-to").text(dname);
    $("#upload-dialog").modal();
});
// transmit values of files and dir_list to front end
$(document).ready(function() {
    // call server for dir_list
    var self = $(this);
    var path = self.data("path");
    if (!path.startsWith('/')) {
        path = '/' + path;
    }
    $.ajax({
        url: "/get-list",
        data: {"path": path},
        method: "GET",
        dataType: "json",
        success: generateDirList
    });
    console.log("success")
    // call server for files
    $.ajax({
        url: "/get-files",
        data: {"path": path},
        method: "GET",
        dataType: "json",
        success: generateFiles
    });

    $('#upload-dialog').on('show.bs.modal', function (e) {
        uploaders = [];
        $('#file-input').prop('disabled', false).val('');
        $('#upload-add').removeClass('disabled');
        $('#upload-start').prop('disabled', true);
        $('#upload-clear').prop('disabled', true);
        $('#file-list').empty();
    }).on('hidden.bs.modal', function (e) {
        location.reload(true);
    });
    $('#file-input').on('change', function(e){
        var files = e.target.files, file;
        for (var i = 0; i < files.length; i++) {
            file = files[i];
            $('#file-list').append('<tr><td><div class="name">'+file.name+'</div></td><td style="width:100%">'
                + '<div class="progress active"><div class="progress-bar progress-bar-info" style="width:0"><span>'
                + file.size.formatBytes() + '</span></div></div></td>'
                + '</tr>');
            uploaders.push(new ChunkedUploader(file, $('.progress-bar').last()));
        }
        $('#file-input').val('');
        $('#upload-start').prop('disabled', uploaders.length == 0);
        $('#upload-clear').prop('disabled', uploaders.length == 0);
    });
    $('#upload-form').on('submit', function (e) {
        $('#file-input').prop('disabled', true);
        $('#upload-add').addClass('disabled');
        $('#upload-start').prop('disabled', true);
        $('#upload-clear').prop('disabled', true);
        $.each(uploaders, function(i, uploader) {
            uploader.start();
        });
        e.preventDefault();
    });
    $('#upload-clear').on('click', function () {
        $('#upload-start').prop('disabled', true);
        $('#upload-clear').prop('disabled', true);
        $('#file-list').empty();
        uploaders = [];
    });
});

function generateDirList(items) {
    $(items).each(function() {
        var url = "{% url 'list' item.url=-1 %}".replace('-1', item.url);
        $("#dir_list_show").append (
            '<li class="breadcrumb-item">' + '<a href=' + url + "></a></li>"
        );
    });
}

function generateFiles(items) {
    $(items).each(function() {
        var self = $(this);
        var htmlContent = '<tr><td class="text-xs-left" data-sort-value="'
        if (slef.is_folder) {
            htmlContent.append("d");
        } else {
            htmlContent.append("f");
        }
        htmlContent.append("{{" + self.name + '|lower}}">' + '<i class="fa fa-fw');
        if (self.is_folder) {
            htmlContent.append("fa-folder");
        } else {
            htmlContent.append("fa-file-o");
        }
        htmlContent.append("></i> &nbsp;<a href=");
        if (self.is_folder) {
            htmlContent.append("{% url 'list' path %}{{" + self.name + "}}");
        } else {
            htmlContent.append("{% url 'get-download' %}?pk={{" + self.acc.pk + "}}&id={{" + self.id + '}}" target="_blank"');
        }
        htmlContent.append('<span class="pull-right">');
        for (var c in self.clouds) {
            htmlContent.append('<i class="color-icon" style="background-color: {{' + self.color + '}}"></i>');
        }
        htmlContent.append("</span></td>");
        if (self.is_folder) {
            htmlContent.append('<td class="text-xs-left" data-sort-value="-1">-</td>' +
                                '<td class="text-xs-left" data-sort-value="-1">-</td>');
        } else {
            htmlContent.append('<td class="text-xs-left" data-sort-value="{{' + self.size + '}}">{{' +
                           self.size + "|filesizeformat }}</td>" + '<td class="text-xs-left" data-sort-value="{{'
                           + self.time + "|date:'U'" +  '}}"' + ">{{'" + self.time + "|naturaltime }}</td>");
        }
        htmlContent.append("</tr>");

        $("#file_list_show").append(htmlContent);
    });
}

function ChunkedUploader(file, progress_bar) {
    if (!this instanceof ChunkedUploader) {
        return new ChunkedUploader(file, options);
    }
    this.file = file;
    this.progress_bar = progress_bar;
    this.file_size = this.file.size;
    this.file_name = this.file.name;
    this.path = $("#upload-form").data("path");
    this.chunk_size = ci_chunk_size(this.file_size);
    this.range_start = 0;
    this.range_end = this.chunk_size;
    if ('mozSlice' in this.file) this.slice_method = 'mozSlice';
    else if ('webkitSlice' in this.file) this.slice_method = 'webkitSlice';
    else this.slice_method = 'slice';
    this.upload_request = new XMLHttpRequest();
    this.upload_request.addEventListener("load", this._onChunkComplete.bind(this), false);
    this.upload_request.addEventListener("progress", this._onProgress.bind(this), false);
    this.upload_request.addEventListener("error", this._onError.bind(this), false);
}
ChunkedUploader.prototype = {
    _upload: function() {
        var chunk;
        if (this.range_end > this.file_size) {
            this.range_end = this.file_size;
        }
        chunk = this.file[this.slice_method](this.range_start, this.range_end);
        ci_prepare_chunk(this, chunk);
        this.upload_request.send(chunk);
    },
    _onProgress: function(evt) {
        var real_total = evt.loaded + this.range_start;
        this._updateProgressBar(real_total);
    },
    _updateProgressBar: function(total) {
        this.progress_bar.css('width', (this.file_size == 0 ? 100 : total * 100.0 / this.file_size) + '%');
        this.progress_bar.children('span').text(total.formatBytes() + '/' + this.file_size.formatBytes());
        if (total * 100.0 / this.file_size >= 50.0)
            this.progress_bar.children('span').css('color', 'white').css('text-shadow', '1px 1px black');
    },
    _onChunkComplete: function() {
        if (this.range_end === this.file_size) {
            this._onUploadComplete();
            return;
        }
        this._updateProgressBar(this.range_end);
        this.range_start = this.range_end;
        this.range_end = this.range_start + this.chunk_size;
        this._upload();
    },
    _onUploadComplete: function() {
        ci_finish(this, this._onDone.bind(this));
    },
    _onError: function() {
        if (this.ignore_failure) {
            this._updateProgressBar(this.range_end);
            this._onChunkComplete();
            return;
        }
        this.fail('Error during upload');
    },
    _onDone: function() {
        this.progress_bar.css('width', '100%');
        this.progress_bar.removeClass('progress-bar-info');
        this.progress_bar.addClass('progress-bar-success');
        this.progress_bar.children('span').text('Done!').css('color', 'white').css('text-shadow', '1px 1px black');
    },
    start: function() {
        ci_start(this, this._upload.bind(this));
    },
    fail: function(text) {
        this.progress_bar.css('width', '0');
        this.progress_bar.children('span').text(text).css('color', 'red').css('text-shadow', '1px 1px white');
    }
};