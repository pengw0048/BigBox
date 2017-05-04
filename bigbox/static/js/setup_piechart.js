var upload_size_to_each_cloud = [];

function formatBytes(bytes) {
    if(bytes < 1024) return bytes + " Bytes";
    else if(bytes < 1048576) return(bytes / 1024).toFixed(3) + " KB";
    else if(bytes < 1073741824) return(bytes / 1048576).toFixed(3) + " MB";
    else return(bytes / 1073741824).toFixed(3) + " GB";
};

function updateUpCloudSize(piechart, file_size, size) {
    var percentages = piechart.getAllSliceSizePercentages();
    var stored = 0;
    var start = true;
    for (var i = 0; i < percentages.length; i ++) {
        if (i === percentages.length - 1) {
            upload_size_to_each_cloud[i] = file_size - stored;
        } else {
            upload_size_to_each_cloud[i] = Math.ceil(percentages[i].toFixed(0) * file_size / 100);
            stored += upload_size_to_each_cloud[i];
        }
        if (upload_size_to_each_cloud[i] < 0 || (size[i] != -1 &&size[i] - upload_size_to_each_cloud[i] <= 0) ) {
            start = false;
        }
    }
    if (!start) {
       $('#upload-start').prop('disabled', true);
    } else {
        $('#upload-start').prop('disabled', false);
    }
}

function setupPieChart(acc_info, file_size, acc) {
    var dimensions = [];
    var init_proportions = [];
    var colors = [];
    var size = [];

    for (var i = 0; i < acc_info.length; i ++) {
        dimensions.push(acc_info[i].name);
        size.push(acc_info[i].space);
        init_proportions.push(1/acc_info.length);//need to be revised, if one average is bigger than extra size
        colors.push(acc_info[i].color);
    }

    var proportions = dimensions.map(function(d,i) { return {
        label: d,
        proportion: init_proportions[i],
        collapsed: false,
        format: {
            color: colors[i],
            label: d.charAt(0).toUpperCase() + d.slice(1) // capitalise first letter
        }
    }});


    var setup = {
        canvas: document.getElementById('piechart'),
        radius: 0.9,
        collapsing: true,
        proportions: proportions,
        drawSegment: drawColorGraph,
        onchange: onPieChartChange
    };

    var newPie = new DraggablePiechart(setup);

    function drawColorGraph(context, piechart, centerX, centerY, radius, startingAngle, arcSize, format, collapsed) {
        if (collapsed) { return; }

        // Draw coloured segment
        context.save();
        var endingAngle = startingAngle + arcSize;
        context.beginPath();
        context.moveTo(centerX, centerY);
        context.arc(centerX, centerY, radius,
            startingAngle, endingAngle, false);
        context.closePath();

        context.fillStyle = format.color;
        context.fill();
        context.restore();

        // Draw label on top
        context.save();
        context.translate(centerX, centerY);
        context.rotate(startingAngle);

        var fontSize = Math.floor(context.canvas.height / 25);
        var dx = radius - fontSize;
        var dy = centerY / 10;

        context.textAlign = "right";
        context.font = fontSize + "pt Helvetica";
        context.fillText(format.label, dx, dy);
        context.restore();
    };

    function drawSegmentOutlineOnly(context, piechart, centerX, centerY, radius, startingAngle, arcSize, format, collapsed) {

        if (collapsed) { return; }

        // Draw segment
        context.save();
        var endingAngle = startingAngle + arcSize;
        context.beginPath();
        context.moveTo(centerX, centerY);
        context.arc(centerX, centerY, radius, startingAngle, endingAngle, false);
        context.closePath();

        context.fillStyle = '#33111a';
        context.fill();
        context.stroke();
        context.restore();

        // Draw label on top
        context.save();
        context.translate(centerX, centerY);
        context.rotate(startingAngle);

        var fontSize = Math.floor(context.canvas.height / 25);
        var dx = radius - fontSize;
        var dy = centerY / 10;

        context.textAlign = "right";
        context.font = fontSize + "pt Helvetica";
        context.fillText(format.label, dx, dy);
        context.restore();
    }

    function onPieChartChange(piechart) {

        updateUpCloudSize(piechart, file_size, size);

        var table = $('#proportions-table');
        //var percentages = piechart.getAllSliceSizePercentages();

        var labelsRow = $('<tr/>').append(proportions.map(function (v, i) {
            return '<td style="padding-left:1em; padding-right:1em">' + v.format.label + '</td>'
        }));
        var proportionsRow = $('<tr/>').append(proportions.map(function(v,i) {

            var plus = $('<div/>').attr('id', 'plus-' + dimensions[i]).addClass('adjust-button').data({i: i, d: -1}).html('&#43;').mousedown(adjustClick);
            var minus = $('<div/>').attr('id', 'plus-' + dimensions[i]).addClass('adjust-button').data({i: i, d: 1}).html('&#8722;').mousedown(adjustClick);
            var extra = '<li style="list-style-type: none;">' + "remain:";
            if (size[i] != -1) {
                extra += size[i] - upload_size_to_each_cloud[i];
            } else {
                extra += "Inf";
            }
            extra += "</li>";

            return $('<td/>').append('<li style="list-style-type: none;">' + "using:" + formatBytes(upload_size_to_each_cloud[i]) + '</li>')
                .append('<li style="list-style-type: none;">' + "available:" + formatBytes(size[i] - upload_size_to_each_cloud[i]) + '</li>')
            return $('<td/>').append('<li style="list-style-type: none;">' + "use:" + formatBytes(upload_size_to_each_cloud[i]) + '</li>')
            .append(extra)
            .append(plus).append(minus);

        }));

        table.html('').append(proportionsRow).append(labelsRow);
        function adjustClick() {
            var i = $(this).data('i');
            var d = $(this).data('d');

            piechart.moveAngle(i, (d * 0.1));
        }


    }

    /*
     * Generates n proportions with a minimum percentage gap between them
     */
    function generateRandomProportions(n, min) {

        // n random numbers 0 - 1
        var rnd = Array.apply(null, {length: n}).map(function(){ return Math.random(); });

        // sum of numbers
        var rndTotal = rnd.reduce(function(a, v) { return a + v; }, 0);

        // get proportions, then make sure each propoertion is above min
        return validateAndCorrectProportions(rnd.map(function(v) { return v / rndTotal; }), min);


        function validateAndCorrectProportions(proportions, min) {
            var sortedProportions = proportions.sort(function(a,b){return a - b});

            for (var i = 0; i < sortedProportions.length; i += 1) {
                if (sortedProportions[i] < min) {
                    var diff = min - sortedProportions[i];
                    sortedProportions[i] += diff;
                    sortedProportions[sortedProportions.length - 1] -= diff;
                    return validateAndCorrectProportions(sortedProportions, min);
                }
            }

            return sortedProportions;

        }
    }

    /*
     * Array sorting algorithm
     */
    function knuthfisheryates2(arr) {
        var temp, j, i = arr.length;
        while (--i) {
            j = ~~(Math.random() * (i + 1));
            temp = arr[i];
            arr[i] = arr[j];
            arr[j] = temp;
        }

        return arr;
    }
}



