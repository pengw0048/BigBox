var uploaders = [];
var MAX_UP_THREADS = 3;
var locale = window.navigator.userLanguage || window.navigator.language;
if (locale) moment.locale(locale);
$(document).on("click", ".upload-to-cloud", function (e) {
    e.preventDefault();
    var self = $(this);
    var pk = self.data("pk");
    var dname = self.text();
    var classname = self.data("classname");
    $("#upload-loader").show();
    $("#upload-to").text(dname);
    $.ajax({
        url: "/get-up-creds",
        data: {"pk": pk},
        method: "GET",
        dataType: "json",
        success: function (data) {
            $.getScript("/static/js/" + classname + ".js", function () {
                ci_init(data, path, pk, function () {
                    $("#upload-form").show();
                    $("#upload-loader").hide();
                });
            });
        }
    });
    $("#upload-dialog").modal();
}).on("click", ".folder-link", function (e) {
    e.preventDefault();
    var folder = $(this).text();
    path += folder + "/";
    window.history.pushState(path, null, "/home" + path);
    loadFolder();
}).on("click", ".folder-link-full", function (e) {
    e.preventDefault();
    path = $(this).data('path');
    window.history.pushState(path, null, "/home" + path);
    loadFolder();
}).on("click", "tr", function (e) {
    var clicked = e.target.nodeName.toLowerCase();
    if (clicked !== "td") return;
    $(this).find("input").click();
});
window.onpopstate = function(event) {
    path = event.state;
    loadFolder();
};
function loadFolder() {
    generateDirList(path);
    $("#file_list_show").children().not("#file-list-loader").remove();
    $('#file-list-loader').show();
    var pks = [];
    $("[name='show-in-cloud']:checked").each(function (i, self) {
        pks.push($(self).val());
    });
    $.ajax({
        url: "/get-files" + path,
        method: "GET",
        data: {'pks': pks},
        traditional: true,
        dataType: "json",
        success: generateFiles,
        complete: function () {
            $('#file-list-loader').hide();
            updateLeftPanel();
        }
    });
}
$(document).ready(function () {
    history.replaceState(path, null, "/home"+path);
    $('#select-all').change(function () {
        var checked = $(this).prop("checked");
        $("[name='select-file']").prop("checked", checked);
        updateLeftPanel();
    });
    $('#master-progress-container').hide();
    loadFolder();
    $('#new-folder-dialog').on('hide.bs.modal', function () {
        $('#folder-name-input').val('');
        loadFolder();
    });
    $('#rename-dialog').on('show.bs.modal', function () {
        var old_name = $("[name='select-file']:checked").first().parents('tr').find('a').text();
        $('#rename-input').val(old_name);
    }).on('hide.bs.modal', function () {
        $('#rename-input').val('');
        loadFolder();
    });
    $('#upload-dialog').on('show.bs.modal', function () {
        uploaders = [];
        $('#file-input').prop('disabled', false).val('');
        $('#upload-add').removeClass('disabled');
        $('#upload-start').prop('disabled', true);
        $('#upload-clear').prop('disabled', true);
        $('#file-list').empty();
    }).on('hidden.bs.modal', function () {
        $('#master-progress-container').hide();
        loadFolder();
    });
    $('#file-input').on('change', function (e) {
        var files = e.target.files, file;
        for (var i = 0; i < files.length; i++) {
            file = files[i];
            $('#file-list').append('<tr><td><div class="name">' + file.name + '</div></td><td style="width:100%">'
                + '<div class="progress active"><div class="progress-bar progress-bar-info" style="width:0"><span>'
                + formatBytes(file.size) + '</span></div></div></td>'
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
            data: {'pk': pks, 'path': path, 'name': $('#folder-name-input').val()},
            traditional: true,
            complete: function () {
                $('#new-folder-dialog').modal('hide');
                $('#create-folder-button').prop('disabled', false).children('span').addClass('hidden');
            }
        });
    });
    $('#rename-form').on('submit', function (e) {
        $('#rename-form-button').prop('disabled', true).children('span').removeClass('hidden');
        e.preventDefault();
        var arr = [];
        $("[name='select-file']:checked").each(function (i, self) {
            $($(self).data('id')).each(function (j, me) {
                arr.push(me);
            })
        });
        $.ajax({
            url: "/rename",
            method: "POST",
            dataType: "json",
            data: {"data": JSON.stringify(arr), "to": $('#rename-input').val()},
            complete: function () {
                $('#rename-dialog').modal('hide');
                $('#rename-form-button').prop('disabled', false).children('span').addClass('hidden');
            }
        });
    });
    $('#upload-clear').on('click', function () {
        $('#upload-start').prop('disabled', true);
        $('#upload-clear').prop('disabled', true);
        $('#file-list').empty();
        uploaders = [];
    });
    $('#delete-button').on('click', function (e) {
        $('#delete-button').prop('disabled', true).children('span').removeClass('hidden');
        $('#rename-button').prop('disabled', true);
        e.preventDefault();
        var arr = [];
        $("[name='select-file']:checked").each(function (i, self) {
            $($(self).data('id')).each(function (j, me) {
                arr.push(me);
            })
        });
        $.ajax({
            url: "/delete",
            method: "POST",
            dataType: "json",
            data: {"data": JSON.stringify(arr)},
            complete: function () {
                $('#delete-button').prop('disabled', false).children('span').addClass('hidden');
                $('#rename-button').prop('disabled', false);
                loadFolder();
            }
        });
    });
    $("[name='show-in-cloud']").on('change', function () {
        loadFolder();
    });
});

function generateDirList(fullpath) {
    var items = fullpath.split("/");
    $("#dir_list_show").children().slice(1).remove();
    var apath = '/';
    $(items).each(function (i, item) {
        if (item === '') return;
        apath += item + '/';
        $("#dir_list_show").append(
            '<li class="breadcrumb-item">' + '<a href="#" class="folder-link-full" data-path="' + apath + '">' + item + "</a></li>"
        );
    });
}

function generateFiles(items) {
    $(items).each(function (i, self) {
        var htmlContent = '<tr><td class="checkbox-col"><div class="checkbox checkbox-default"><input type="checkbox" name="select-file"><label></label></div></td><td class="text-xs-left" data-sort-value="';
        if (self.is_folder) {
            htmlContent += ("d");
        } else {
            htmlContent += ("f");
        }
        htmlContent += (self.name.toLowerCase() + '">' + '<i class="fa fa-fw');
        if (self.is_folder) {
            htmlContent += (" fa-folder");
        } else {
            htmlContent += (" fa-file-o");
        }
        htmlContent += ('"></i> &nbsp;<a href="');
        if (self.is_folder) {
            htmlContent += ('#" class="folder-link">');
        } else {
            htmlContent += ('/get-down?pk=' + self.acc + '&id=' + self.id + '" target="_blank">');
        }
        htmlContent += (self.name + '</a><span class="pull-right">');
        for (var j = 0; j < self.colors.length; j++) {
            htmlContent += (' <i class="color-icon" style="background-color: ' + self.colors[j] + '"></i>');
        }
        htmlContent += ("</span></td>");
        if (self.is_folder) {
            htmlContent += ('<td class="text-xs-left" data-sort-value="-1">-</td>' +
            '<td class="text-xs-left" data-sort-value="-1">-</td>');
        } else {
            htmlContent += ('<td class="text-xs-left" data-sort-value="' + self.size + '">' +
            formatBytes(self.size) + "</td>" + '<td class="text-xs-left" data-sort-value="'
            + new Date(self.time).getTime() + '">' + moment(self.time).format('lll') + "</td>");
        }
        htmlContent += ("</tr>");
        var tr = $(htmlContent);
        if (self.is_folder) tr.find('input').data('id', self.id);
        else {
            var o = {};
            o[self.acc] = self.id;
            tr.find('input').data('id', [o]);
        }
        $("#file_list_show").append(tr);
    });
    $("#th-name").stupidsort('asc');
    $("[name='select-file']").change(updateLeftPanel);
}

function updateLeftPanel () {
    var numsel = $("[name='select-file']:checked").length;
    $('#select-all').prop("checked", (numsel === $("[name='select-file']").length));
    if (numsel === 0) {
        $('#files-op-panel').hide();
    } else {
        $('#num-selecting-files').text(numsel);
        if (numsel === 1) {
            $('#rename-button').show();
        } else {
            $('#rename-button').hide();
        }
        $('#files-op-panel').show();
    }
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
    this.path = path;
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
