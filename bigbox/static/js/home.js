var uploaders = [];
var CHUNK_REMARK = "split_chunk ";
var MAX_UP_THREADS = 3;
var is_big_file = false;
var locale = window.navigator.userLanguage || window.navigator.language;
if (locale) moment.locale(locale);
$(document).on("click", ".upload-to-cloud", function (e) {
    e.preventDefault();
    is_big_file = false;
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
}).on("click", "#upload-to-all", function(e){
    e.preventDefault();
    is_big_file = true;
    $("#upload-to").text("Big files");
    $("#upload-form").show();
    $("#upload-loader").hide();
    $("#upload-dialog").modal();
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
        $('#file-input').prop('disabled', false).val('').prop('multiple', !is_big_file);
        $('#upload-add').removeClass('disabled');
        $('#upload-start').prop('disabled', true);
        $('#upload-clear').prop('disabled', true);
        $('#file-list').empty();
    }).on('hidden.bs.modal', function () {
        $('#master-progress-container').hide();
        loadFolder();
    });
    $('#file-input').on('change', function (e) {
        e.preventDefault();
        if (is_big_file) {
            var file = e.target.files;
            $('#file-list').append('<tr><td><div class="name">' + file[0].name + '</div></td><td style="width:100%">'
                + '<div class="progress active"><div class="progress-bar progress-bar-info" style="width:0"><span>'
                + formatBytes(file[0].size) + '</span></div></div></td>'
                + '</tr>');
            $('#file-input').prop('disabled', true);
            $('#upload-add').addClass('disabled');
            uploaders.push(new BigUploader(file[0], $('.progress-bar').last(), acc, cloudclass));
        } else {
            var files = e.target.files, file;
            for (var i = 0; i < files.length; i++) {
                file = files[i];
                $('#file-list').append('<tr><td><div class="name">' + file.name + '</div></td><td style="width:100%">'
                    + '<div class="progress active"><div class="progress-bar progress-bar-info" style="width:0"><span>'
                    + formatBytes(file.size) + '</span></div></div></td>'
                    + '</tr>');
                uploaders.push(new ChunkedUploader(file, $('.progress-bar').last()));
            }
        }
        $('#file-input').val('');
        $('#upload-start').prop('disabled', uploaders.length === 0);
        $('#upload-clear').prop('disabled', uploaders.length === 0);
    });
    $('#upload-form').on('submit', function (e) {
        e.preventDefault();
        $('#file-input').prop('disabled', true);
        $('#upload-add').addClass('disabled');
        $('#upload-start').prop('disabled', true);
        $('#upload-clear').prop('disabled', true);
        if (is_big_file) {
            uploaders[0].start();// start big file uploader
        } else {
            $.each(uploaders, function (i, uploader) {
                uploader.wait();
            });
            checkUpQueue();
            $('#master-progress-container').show();
            e.preventDefault();
        }
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
    $('.split_chunk').on('submit', function(e) {
        var file_id = $('.split_chunk').get('id');
        var file_name = $('.split_chunk').get('file_name');
        downloadBigFile(file_name);
    });
    $("[name='show-in-cloud']").on('change', function () {
        loadFolder();
    });
});

function downloadBigFile(file_name) {
   // go through all the cloud accounts and get content from each of them

}

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
        htmlContent += ('"></i> &nbsp;');


        if (self.name.substring(0, 11) == "split_chunk") {
            htmlContent += ('<form' + ' method="post" ' + ' class="split_chunk" ' + '&id="' + self.id +'" file_name="'
             + self.name + '" "target="_blank">' + '~~~');// if submit, then do something
            htmlContent += (self.name + '</form><span class="pull-right">');
        } else {
            htmlContent += ('<a href="');
            if (self.is_folder) {
                htmlContent += ('#" class="folder-link">');
            } else {
                htmlContent += ('/get-down?pk=' + self.acc + '&id=' + self.id + '" target="_blank">');
            }
            htmlContent += (self.name + '</a><span class="pull-right">');
        }
        // if the file is the splitted file, then have to get split chunk from each folder
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

String.prototype.getBytes = function () {
  var bytes = [];
  for (var i = 0; i < this.length; ++i) {
    bytes.push(this.charCodeAt(i));
  }
  return bytes;
};

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
        if (this.progress_bar != null) {
            updateProgressBar(this.progress_bar, total, this.file_size, formatBytes);
        }
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
        if (this.progress_bar != null) {
            this.progress_bar.children('span').text('Waiting ...');
        }
    },
    start: function () {
        this.state = 2;
        if (this.progress_bar != null) {
            this.progress_bar.children('span').text('Starting ...');
        }
        ci_start(this, this._upload.bind(this));
        this._updateProgressBar(0);
    },
    fail: function (text) {
        this.state = 4;
        if (this.progress_bar != null) {
            this.progress_bar.css('width', '0');
            this.progress_bar.children('span').text(text).css('color', 'red').css('text-shadow', '1px 1px white');
        }
        checkUpQueue();
    }
};


function BigUploader(file, progress_bar, acc, cloudclass) {

    if (!this instanceof BigUploader) {
        return new BigUploader(file, options);
    }
    this.file = file;
    this.progress_bar = progress_bar;
    this.file_size = 0; // represent total file size in the request to drive
    this.ori_file_size = this.file.size;
    this.file_name = CHUNK_REMARK + this.file.name;
    this.state = 0;
    this.path = path;

    this.chunk_size = 0;
    this.range_start = 0;
    this.range_end = this.chunk_size;
    this.cloud_info = acc;
    this.cloud_num = acc.length;
    this.finished_cloud = 0;
    this.cloudclass = cloudclass;
    this.up_range_start = 0;
    this.up_range_end = this.chunk_size;
    this.range_diff = 0;

    this.one_cloud_up_size = Math.ceil(this.ori_file_size / this.cloud_num);
    this.up_record = {};
    if ('mozSlice' in this.file) this.slice_method = 'mozSlice';
    else if ('webkitSlice' in this.file) this.slice_method = 'webkitSlice';
    else this.slice_method = 'slice';
    this.upload_request = new XMLHttpRequest();
    this.upload_request.addEventListener("load", this._onChunkComplete.bind(this), false);
    this.upload_request.addEventListener("progress", this._onProgress.bind(this), false);
    this.upload_request.addEventListener("error", this._onError.bind(this), false);
}

function getNextCloudCreds(pk, classname, done) {
    $.ajax({
        url: "/get-up-creds",
        data: {"pk": pk},
        method: "GET",
        dataType: "json",
        success: function (data) {
            $.getScript("/static/js/" + classname + ".js", function () {
                ci_init(data, "/", pk, function () {
                    done();
                });
            });
        }
    });
}

BigUploader.prototype = {
    _upload: function () {

        this.range_start = this.up_range_start - this.range_diff;// drive requires the byte start from 0, range_start, range_end is the fake data for each drive
        this.range_end = this.up_range_end - this.range_diff;

        var chunk = this.file[this.slice_method](this.up_range_start, this.up_range_end);
        ci_prepare_chunk(this, chunk);
        this.upload_request.send(chunk);
    },
    _onProgress: function (evt) {
        var real_total = evt.loaded + this.up_range_start;
        this._updateProgressBar(real_total);
    },
    _updateProgressBar: function (total) {
        updateProgressBar(this.progress_bar, total, this.ori_file_size, formatBytes);
    },
    _onChunkComplete: function () {
        if (this.up_range_end >= this.ori_file_size || this.up_range_end >= (this.finished_cloud + 1 ) * this.one_cloud_up_size) {
            this._onUploadComplete();
            return;
        }
        this._updateProgressBar(this.up_range_end);
        this.up_range_start = this.up_range_end;
        this.up_range_end = Math.min((this.finished_cloud + 1 ) * this.one_cloud_up_size, Math.min(this.up_range_start + this.chunk_size, this.ori_file_size));
        this._upload();
    },
    _onUploadComplete: function () {
        // complete all the uploads for one cloud
        // count whether reaching the last cloud
        this.up_record[this.cloud_info[this.finished_cloud]] = [this.up_range_start, this.up_range_end];
        ci_finish(this, this._onDone.bind(this));
        this.finished_cloud += 1;
        this.file_size = Math.min(this.one_cloud_up_size, this.ori_file_size - this.finished_cloud * this.one_cloud_up_size);
        if (this.finished_cloud < this.cloud_num && this.up_range_end < this.ori_file_size ) {
            getNextCloudCreds(this.cloud_info[this.finished_cloud], this.cloudclass[this.finished_cloud],
                function() {
                    this.chunk_size = ci_chunk_size(this.file_size);
                    ci_start(this, function() {
                        this.up_range_start = this.up_range_end;
                        this.up_range_end = Math.min((this.finished_cloud + 1) * this.one_cloud_up_size, Math.min(this.up_range_start + this.chunk_size, this.ori_file_size));
                        this.range_diff = this.up_range_start;
                        this._upload();
                    }.bind(this));
                }.bind(this));
        } else {
            // write upload record to file
            // connection has been closed, should reopen it again
            // reopen the last cloud
            var meta_cloud_idx = this.finished_cloud - 1;
            getNextCloudCreds(this.cloud_info[meta_cloud_idx], this.cloudclass[meta_cloud_idx],
                function() {
                    this.chunk_size = ci_chunk_size(this.file_size);
                    ci_start(this, function() {
                        var jsonse = JSON.stringify(uploaders[0].up_record);
                        var meta_file = new Blob([jsonse], {type: "application/json"});
                        //var tmp = JSON.stringify(uploaders[0].up_record);
                        //var meta_file = tmp.getBytes("UTF-8");
                        meta_uploader = new MetaUploader(meta_file, uploaders[0].file_name);
                        meta_uploader.start();
                    });
                });
        }
    },
    _onError: function () {
        if (this.ignore_failure) {
            this._updateProgressBar(this.up_range_end);
            this._onChunkComplete();
            return;
        }
        this.fail('Error during upload');
    },
    _onDone: function () {
        this.state = 3;
        updateProgressBar(this.progress_bar, 1, 1);
    },
    wait: function () {
        this.state = 1;
        this.progress_bar.children('span').text('Waiting ...');
    },
    start: function () {
        this.file_size = Math.min(this.one_cloud_up_size, this.ori_file_size - this.finished_cloud * this.one_cloud_up_size);
        getNextCloudCreds(this.cloud_info[0], this.cloudclass[0], function(){
        this.chunk_size = ci_chunk_size(this.file_size);
        this.state = 2;
        ci_start(this, this._upload.bind(this));
        this._updateProgressBar(0);
        }.bind(this));
    },
    fail: function (text) {
        this.state = 4;
        this.progress_bar.css('width', '0');
        this.progress_bar.children('span').text(text).css('color', 'red').css('text-shadow', '1px 1px white');
    }
};


function MetaUploader(file, name) {

    if (!this instanceof MetaUploader) {
        return new MetaUploader(file, options);
    }
    this.file = file;
    this.progress_bar = null;
    this.file_size = this.file.size;
    this.file_name = "meta data " + name;
    this.state = 0;
    this.path = "/";
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

MetaUploader.prototype = {
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
    },
    _onChunkComplete: function () {
        if (this.range_end === this.file_size) {
            this._onUploadComplete();
            return;
        }
        this.range_start = this.range_end;
        this.range_end = this.range_start + this.chunk_size;
        this._upload();
    },
    _onUploadComplete: function () {
        ci_finish(this, this._onDone.bind(this));
    },
    _onError: function () {
        if (this.ignore_failure) {
            this._onChunkComplete();
            return;
        }
        this.fail('Error during upload');
    },
    _onDone: function () {
        this.state = 3;
        checkUpQueue();
    },
    wait: function () {
        this.state = 1;
        if (this.progress_bar != null) {
            this.progress_bar.children('span').text('Waiting ...');
        }
    },
    start: function () {
        this.state = 2;
        if (this.progress_bar != null) {
            this.progress_bar.children('span').text('Starting ...');
        }
        ci_start(this, this._upload.bind(this));
    },
    fail: function (text) {
        this.state = 4;
        if (this.progress_bar != null) {
            this.progress_bar.css('width', '0');
            this.progress_bar.children('span').text(text).css('color', 'red').css('text-shadow', '1px 1px white');
        }
        checkUpQueue();
    }
};