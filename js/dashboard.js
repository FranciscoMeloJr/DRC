var dropZone = document.getElementById('drop-zone');
var fileInput = document.getElementById('file-input');
var dashboard = document.getElementById('dashboard');
var statusTag = document.getElementById('status-tag');
var currentData = null; // Store data globally for downloading

if (dropZone) {
    dropZone.onclick = function() { fileInput.click(); };
    dropZone.ondragover = function(e) { e.preventDefault(); };
    dropZone.ondrop = function(e) {
        e.preventDefault();
        if (e.dataTransfer.files.length > 0) { handleFile(e.dataTransfer.files[0]); }
    };
}

function handleFile(file) {
    statusTag.innerText = "PROCESSING...";
    var reader = new FileReader();
    reader.onload = function(e) {
        fetch('./analyze', { method: 'POST', body: e.target.result })
        .then(function(res) { return res.json(); })
        .then(function(data) {
            currentData = data; // Save for the download button
            render(data);
        })
        .catch(function(err) { statusTag.innerText = "BRIDGE ERROR"; });
    };
    reader.readAsText(file);
}

function downloadReport() {
    if (!currentData) { return; }
    var dataStr = JSON.stringify(currentData, null, 2);
    var blob = new Blob([dataStr], { type: "application/json" });
    var url = URL.createObjectURL(blob);
    var link = document.createElement("a");
    link.href = url;
    link.download = "infinispan-drc-report.json";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

function render(data) {
    dropZone.style.display = 'none';
    dashboard.style.display = 'block';
    statusTag.innerText = "SUCCESS";

    // 1. Add Download Button to Status Area (if not already there)
    if (!document.getElementById('dl-btn')) {
        var dlBtn = document.createElement('button');
        dlBtn.id = 'dl-btn';
        dlBtn.innerText = "Download JSON";
        dlBtn.className = "ml-4 bg-green-600 hover:bg-green-700 text-white text-xs px-3 py-1 rounded transition";
        dlBtn.onclick = downloadReport;
        statusTag.parentNode.appendChild(dlBtn);
    }

    // 2. Data Extraction
    var results = data["results"];
    if (!results) { results = []; }

    var summary = {};
    if (data["metadata"]) {
        if (data["metadata"]["summary"]) {
            summary = data["metadata"]["summary"];
        }
    }

    // 3. Render KPIs
    var statsGrid = document.getElementById('stats-grid');
    if (statsGrid) {
        statsGrid.innerHTML = "";
        for (var key in summary) {
            var val = summary[key];
            var card = document.createElement('div');
            card.className = "bg-white p-4 rounded-xl shadow-sm border-t-4 border-blue-600 text-center";
            card.innerHTML = "<div class='text-xs font-bold text-gray-400 uppercase'>" + key + "</div>" +
                             "<div class='text-2xl font-black text-gray-800'>" + val + "</div>";
            statsGrid.appendChild(card);
        }
    }

    // 4. Render Cluster Cards
    var list = document.getElementById('cluster-list');
    if (list) {
        list.innerHTML = "";
        for (var i = 0; i < results.length; i++) {
            var res = results[i];
            var div = document.createElement('div');
            div.className = "bg-white p-6 rounded-xl border shadow-sm mb-6 text-left";


            var clusterName = res["name"];
            if (!clusterName) { clusterName = "Cluster " + i; }


            var title = document.createElement('h3');
            title.className = "font-bold text-blue-800 text-xl border-b pb-2 mb-4";
            title.innerText = clusterName;
            div.appendChild(title);

            var findings = res["findings"];
            if (!findings) { findings = []; }


            var grid = document.createElement('div');
            grid.className = "grid grid-cols-1 md:grid-cols-2 gap-3";


            for (var j = 0; j < findings.length; j++) {
                var f = findings[j];
                var fDiv = document.createElement('div');
                var borderCol = "border-blue-400";
                if (f["crit"] == "CRITICAL") { borderCol = "border-red-500"; }
                fDiv.className = "p-3 bg-gray-50 border-l-4 " + borderCol + " rounded text-xs";
                fDiv.innerText = f["crit"] + ": " + f["ref"];
                grid.appendChild(fDiv);
            }
            div.appendChild(grid);
            list.appendChild(div);
        }
    }

    // 5. THE RAW DATA DUMP
    var debug = document.createElement('pre');
    debug.style.background = "#1a1a1a";
    debug.style.color = "#00ff00";
    debug.style.padding = "20px";
    debug.style.marginTop = "40px";
    debug.style.fontSize = "10px";
    debug.style.borderRadius = "8px";
    debug.innerText = "RAW DATA FROM BRIDGE:\n" + JSON.stringify(data, null, 2);
    dashboard.appendChild(debug);
}