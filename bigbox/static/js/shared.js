var locale = window.navigator.userLanguage || window.navigator.language;
if (locale) moment.locale(locale);
$(document).on("click", ".folder-link", function (e) {
    e.preventDefault();
    var folder = $(this).text();
    path += folder + "/";
    loadFolder();
}).on("click", ".folder-link-full", function (e) {
    e.preventDefault();
    path = $(this).data('path');
    loadFolder();
});
function loadFolder() {
    generateDirList(path);
    $("#file_list_show").children().not("#file-list-loader").remove();
    $('#file-list-loader').show();
    $.ajax({
        url: "/shared-list/" + sid + path,
        method: "GET",
        dataType: "json",
        success: generateFiles,
        complete: function () {
            $('#file-list-loader').hide();
        }
    });
}
$(document).ready(function () {
    loadFolder();
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
        htmlContent += ('"></i> &nbsp;');


        if (self.name.substring(0, 11) == "split_chunk") {
            htmlContent += ('<div' + ' class="split_chunk" ' + '&id="' + self.id + '" file_name="'
            + self.name + '" "target="_blank">' + '~~~');// if submit, then do something
            htmlContent += (self.name + '</div>');
        } else {
            htmlContent += ('<a href="');
            if (self.is_folder) {
                htmlContent += ('#" class="folder-link">');
            } else {
                htmlContent += ('/get-down?pk=' + self.acc + '&id=' + encodeURIComponent(self.id) + '" target="_blank">');
            }
            htmlContent += (self.name + '</a>');
        }
        htmlContent += ("</td>");
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
}
