var uploaders = [];
var MAX_UP_THREADS = 3;
var locale = window.navigator.userLanguage || window.navigator.language;
if (locale) moment.locale(locale);
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
                ci_init(data, $('#new-folder-dialog').data("path"), pk, function () {
                    $("#upload-form").show();
                    $("#upload-loader").hide();
                });
            });
        }
    });
    $("#upload-to").text(dname);
    $("#upload-dialog").modal();
}).on("click", ".folder-link", function() {
    var path = $('#new-folder-dialog').data("path");
    var folder = $(this).text();
    $('#new-folder-dialog').data("path", path + folder + "/");
    loadFolder();
}).on("click", ".folder-link-full", function() {
    $('#new-folder-dialog').data("path", $(this).data('path'));
    loadFolder();
});
function loadFolder() {
    var path = $('#new-folder-dialog').data("path");
    if (!path.startsWith('/')) {
        path = '/' + path;
    }
    $.ajax({
        url: "/get-list" + path,
        method: "GET",
        dataType: "json",
        success: generateDirList
    });
    $("#file_list_show").children().slice(1).remove();
    $('#file-list-loader').removeClass('hidden');
    // call server for files
    $.ajax({
        url: "/get-files" + path,
        method: "GET",
        dataType: "json",
        success: generateFiles,
        complete: function () {
            $('#file-list-loader').addClass('hidden');
        }
    });
}
// transmit values of files and dir_list to front end
$(document).ready(function () {
    $('#master-progress-container').hide();
    // call server for dir_list
    loadFolder();
    $('#upload-dialog').on('show.bs.modal', function () {
        uploaders = [];
        $('#file-input').prop('disabled', false).val('');
        $('#upload-add').removeClass('disabled');
        $('#upload-start').prop('disabled', true);
        $('#upload-clear').prop('disabled', true);
        $('#file-list').empty();
    }).on('hidden.bs.modal', function () {
        location.reload(true);
    });
    $('#file-input').on('change', function (e) {
        var files = e.target.files, file;
        for (var i = 0; i < files.length; i++) {
            file = files[i];
            $('#file-list').append('<tr><td><div class="name">' + file.name + '</div></td><td style="width:100%">'
                + '<div class="progress active"><div class="progress-bar progress-bar-info" style="width:0"><span>'
                + file.size.formatBytes() + '</span></div></div></td>'
                + '</tr>');
            uploaders.push(new ChunkedUploader(file, $('.progress-bar').last()));
        }
        $('#file-input').val('');
        $('#upload-start').prop('disabled', uploaders.length === 0);
        $('#upload-clear').prop('disabled', uploaders.length === 0);
    });
    $('#upload-form').on('submit', function (e) {
        $('#file-input').prop('disabled', true);
        $('#upload-add').addClass('disabled');
        $('#upload-start').prop('disabled', true);
        $('#upload-clear').prop('disabled', true);
        $.each(uploaders, function (i, uploader) {
            uploader.wait();
        });
        checkUpQueue();
        $('#master-progress-container').show();
        e.preventDefault();
    });
    $('#new-folder-form').on('submit', function (e) {
        $('#create-folder-button').prop('disabled', true).children('span').removeClass('hidden');
        e.preventDefault();
        var pks = [];
        $.each($('.create-folder-pk'), function (i, input) {
            if ($(input).prop('checked')) pks.push($(input).val());
        });
        $.ajax({
            url: "/create-folder",
            method: "POST",
            dataType: "json",
            data: {'pk': pks, 'path': $('#new-folder-dialog').data('path'), 'name': $('#folder-name-input').val()},
            traditional: true,
            complete: function () {
                location.reload(true);
            }
        })
    });
    $('#upload-clear').on('click', function () {
        $('#upload-start').prop('disabled', true);
        $('#upload-clear').prop('disabled', true);
        $('#file-list').empty();
        uploaders = [];
    });
});

function generateDirList(items) {
    $("#dir_list_show").children().slice(1).remove();
    var path = '/';
    $(items).each(function (i, item) {
        path += item.name + '/';
        $("#dir_list_show").append(
            '<li class="breadcrumb-item">' + '<a href="#" class="folder-link-full" data-path="'+path+'">' + item.name + "</a></li>"
        );
    });
}

function generateFiles(items) {
    $(items).each(function (i, self) {
        var htmlContent = '<tr><td class="text-xs-left" data-sort-value="';
        if (self.is_folder) {
            htmlContent+=("d");
        } else {
            htmlContent+=("f");
        }
        htmlContent+=(self.name.toLowerCase() + '">' + '<i class="fa fa-fw');
        if (self.is_folder) {
            htmlContent+=(" fa-folder");
        } else {
            htmlContent+=(" fa-file-o");
        }
        htmlContent+=('"></i> &nbsp;<a href="');
        if (self.is_folder) {
            htmlContent+=('#" class="folder-link">');
        } else {
            htmlContent+=('/get-down?pk=' + self.acc + '&id=' + self.id + '" target="_blank">');
        }
        htmlContent+=(self.name + '</a><span class="pull-right">');
        for (var c in self.clouds) {
            htmlContent+=(' <i class="color-icon" style="background-color: ' + self.clouds[c] + '"></i>');
        }
        htmlContent+=("</span></td>");
        if (self.is_folder) {
            htmlContent+=('<td class="text-xs-left" data-sort-value="-1">-</td>' +
                '<td class="text-xs-left" data-sort-value="-1">-</td>');
        } else {
            htmlContent+=('<td class="text-xs-left" data-sort-value="' + self.size + '">' +
                formatBytes(self.size) + "</td>" + '<td class="text-xs-left" data-sort-value="'
                + new Date(self.time).getTime() + '">' + moment(self.time).format('lll') + "</td>");
        }
        htmlContent+=("</tr>");

        $("#file_list_show").append(htmlContent);
    });
}

function updateProgressBar(obj, completed, total, disp) {
    if (completed * 100.0 / total >= 50.0)
        obj.children('span').css('color', 'white').css('text-shadow', '1px 1px black');
    if (completed === total)
        obj.css('width', '100%').removeClass('progress-bar-info').addClass('progress-bar-success').children('span').text('Done!');
    else
        obj.css('width', completed * 100.0 / total + '%').children('span')
            .text(disp ? disp(completed) + '/' + disp(total) : completed + '/' + total);
}

function checkUpQueue() {
    var count = MAX_UP_THREADS;
    var completed = 0;
    var i;
    for (i = 0; i < uploaders.length; i++) {
        if (uploaders[i].state === 2) count--;
        if (uploaders[i].state > 2) completed++;
    }
    updateProgressBar($('#master-progress'), completed, uploaders.length);
    for (i = 0; i < uploaders.length; i++) {
        if (count === 0) break;
        if (uploaders[i].state === 1) {
            uploaders[i].start();
            count--;
        }
    }
}

function ChunkedUploader(file, progress_bar) {
    if (!this instanceof ChunkedUploader) {
        return new ChunkedUploader(file, options);
    }
    this.file = file;
    this.progress_bar = progress_bar;
    this.file_size = this.file.size;
    this.file_name = this.file.name;
    this.state = 0;
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
    _upload: function () {
        var chunk;
        if (this.range_end > this.file_size) {
            this.range_end = this.file_size;
        }
        chunk = this.file[this.slice_method](this.range_start, this.range_end);
        ci_prepare_chunk(this, chunk);
        this.upload_request.send(chunk);
    },
    _onProgress: function (evt) {
        var real_total = evt.loaded + this.range_start;
        this._updateProgressBar(real_total);
    },
    _updateProgressBar: function (total) {
        updateProgressBar(this.progress_bar, total, this.file_size, formatBytes);
    },
    _onChunkComplete: function () {
        if (this.range_end === this.file_size) {
            this._onUploadComplete();
            return;
        }
        this._updateProgressBar(this.range_end);
        this.range_start = this.range_end;
        this.range_end = this.range_start + this.chunk_size;
        this._upload();
    },
    _onUploadComplete: function () {
        ci_finish(this, this._onDone.bind(this));
    },
    _onError: function () {
        if (this.ignore_failure) {
            this._updateProgressBar(this.range_end);
            this._onChunkComplete();
            return;
        }
        this.fail('Error during upload');
    },
    _onDone: function () {
        this.state = 3;
        updateProgressBar(this.progress_bar, 1, 1);
        checkUpQueue();
    },
    wait: function () {
        this.state = 1;
        this.progress_bar.children('span').text('Waiting ...');
    },
    start: function () {
        this.state = 2;
        this.progress_bar.children('span').text('Starting ...');
        ci_start(this, this._upload.bind(this));
        this._updateProgressBar(0);
    },
    fail: function (text) {
        this.state = 4;
        this.progress_bar.css('width', '0');
        this.progress_bar.children('span').text(text).css('color', 'red').css('text-shadow', '1px 1px white');
        checkUpQueue();
    }
};
