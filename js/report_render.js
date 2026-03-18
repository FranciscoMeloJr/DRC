window.onload = function() {
    // 1. Grab the data left by the index page
    const rawData = localStorage.getItem('drc_latest_report');
    if (!rawData) {
        document.body.innerHTML = "<h1>No data found. Please run analysis again.</h1>";
        return;
    }

    const data = JSON.parse(rawData);

    // 2. Render the Histogram
    renderHistogram(data.metadata.summary);

    // 3. Render the Cards
    const clusterList = document.getElementById('cluster-list');
    const sourceData = data.results || [];

    sourceData.forEach(res => {
        res.findings.forEach(f => {
            const card = document.createElement('div');
            card.className = `card severity-${f.crit.toLowerCase()}`;
            card.innerHTML = `
                <div class="dot"></div>
                <div class="card-text">
                    <strong>${res.name.toUpperCase()}:</strong> ${f.ref}
                </div>`;
            clusterList.appendChild(card);
        });
    });
};

function renderHistogram(summary) {
    const container = document.getElementById('drc-histogram');
    const levels = ["CRITICAL", "ERROR", "WARNING", "NOTICE"];
    const maxCount = Math.max(...Object.values(summary), 1);

    container.innerHTML = levels.map(lvl => {
        const count = summary[lvl] || 0;
        const height = (count / maxCount) * 100;
        return `
            <div class="hist-column">
                <span class="hist-count">${count}</span>
                <div class="hist-bar ${lvl.toLowerCase()}" style="height: ${height}px"></div>
                <span class="hist-label">${lvl}</span>
            </div>`;
    }).join('');
}