window.onload = function() {
    const uploadBtn = document.getElementById('upload-btn');
    const fileInput = document.getElementById('file-input');
    const dropZone = document.getElementById('drop-zone');
    const dashboard = document.getElementById('dashboard');
    const clusterList = document.getElementById('cluster-list');

    // 1. Setup the Raw Data Display (The Bottom section)
    let rawDisplay = document.getElementById('raw-display');
    if (!rawDisplay) {
        const rawContainer = document.createElement('div');
        rawContainer.style.marginTop = '40px';
        rawContainer.innerHTML = `            <h3 style="color: #94a3b8; font-size: 11px; margin-bottom: 10px; text-transform: uppercase; font-weight: 800;">Raw Data From Bridge:</h3>             <pre id="raw-display" style="background: #0f172a; color: #4ade80; padding: 15px; border-radius: 8px; font-family: monospace; font-size: 12px; overflow-x: auto; border: 1px solid #1e293b; line-height: 1.5;"></pre>        `;
        dashboard.appendChild(rawContainer);
        rawDisplay = document.getElementById('raw-display');
    }

    // 2. Interaction Logic
    uploadBtn.onclick = (e) => { e.stopPropagation(); fileInput.click(); };
    dropZone.onclick = () => fileInput.click();
    fileInput.onchange = (e) => { if (e.target.files[0]) handleFile(e.target.files[0]); };

    dropZone.ondragover = (e) => e.preventDefault();
    dropZone.ondrop = (e) => {
        e.preventDefault();
        if (e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0]);
    };

    // 3. The API Call (Binary Stream to fix the ScannerError)
    async function handleFile(file) {
        try {
            const response = await fetch('/analyze', {
                method: 'POST',
                body: file, // Send binary directly - no FormData wrapper
                headers: { 'Content-Type': 'application/yaml' }
            });
            const data = await response.json();
            renderDashboard(data);
        } catch (err) {
            console.error("Connection failed:", err);
        }
    }

    // 4. UI Rendering (Summary TOP, Raw BOTTOM)
    function renderDashboard(data) {
        dashboard.style.display = 'block';
        clusterList.innerHTML = '';

        // TOP: Summary Cards
        if (data.results && Array.isArray(data.results)) {
            data.results.forEach(res => {
                if (res.findings && Array.isArray(res.findings)) {
                    res.findings.forEach(f => {
                        const card = document.createElement('div');
                        card.className = 'card';


                        const dot = document.createElement('div');
                        dot.className = 'dot';
                        if (f.crit === 'CRITICAL'  || f.ref.includes('risk')) {
                            dot.style.background = '#e60000';
                        }

                        const text = document.createElement('div');
                        text.className = 'card-text';
                        const cleanRef = f.ref.replace('NOTICE: ', '').replace(/_/g, ' ');
                        text.innerHTML = `<strong>${res.name}:</strong> ${cleanRef}`;

                        card.appendChild(dot);
                        card.appendChild(text);
                        clusterList.appendChild(card);
                    });
                }
            });
        }

        // BOTTOM: Raw JSON
        rawDisplay.textContent = JSON.stringify(data, null, 2);
        dashboard.scrollIntoView({ behavior: 'smooth' });
    }
};
