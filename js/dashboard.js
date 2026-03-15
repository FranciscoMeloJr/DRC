window.onload = function() {
    const uploadBtn = document.getElementById('upload-btn');
    const rulesBtn = document.getElementById('rules-btn');
    const rulesSection = document.getElementById('rules-section');
    const fileInput = document.getElementById('file-input');
    const dropZone = document.getElementById('drop-zone');
    const dashboard = document.getElementById('dashboard');
    const clusterList = document.getElementById('cluster-list');
    const rawDisplay = document.getElementById('raw-display');

    // About Modal Logic
    const modal = document.getElementById("aboutModal");
    const btn = document.getElementById("aboutBtn");
    const span = document.getElementsByClassName("close")[0];

    //Rules list
    const rulesModal = document.getElementById("rulesModal");
    const viewRulesBtn = document.getElementById("viewRulesBtn");
    const closeRules = document.getElementById("closeRules");
    const rulesContent = document.getElementById("rulesContent");

    viewRulesBtn.onclick = async () => {
        rulesModal.style.display = "block";
        try {
            const response = await fetch('/api/rules');
            const data = await response.json();
            // Displays the JSON rules prettified
            rulesContent.textContent = JSON.stringify(data, null, 4);
        } catch (err) {
            rulesContent.textContent = "Error loading rules from bridge.";
        }
    };

    closeRules.onclick = () => rulesModal.style.display = "none";

    btn.onclick = () => modal.style.display = "block";
    span.onclick = () => modal.style.display = "none";
    window.onclick = (e) => { if (e.target == modal) modal.style.display = "none"; }

    // --- 1. View Rules Toggle ---
    rulesBtn.onclick = () => {
        const isHidden = rulesSection.style.display === 'none';
        rulesSection.style.display = isHidden ? 'block' : 'none';
        rulesBtn.innerText = isHidden ? 'HIDE RULES' : 'VIEW RULES';
        if (isHidden) rulesSection.scrollIntoView({ behavior: 'smooth' });
    };

    // --- 2. Interaction Handlers ---
    uploadBtn.onclick = (e) => { e.stopPropagation(); fileInput.click(); };
    dropZone.onclick = () => fileInput.click();
    fileInput.onchange = (e) => { if (e.target.files[0]) handleFile(e.target.files[0]); };

    dropZone.ondragover = (e) => { e.preventDefault(); dropZone.style.borderColor = "#e60000"; };
    dropZone.ondragleave = () => { dropZone.style.borderColor = "#4e4e6a"; };
    dropZone.ondrop = (e) => {
        e.preventDefault();
        dropZone.style.borderColor = "#4e4e6a";
        if (e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0]);
    };

    // --- 3. The API Call (Binary Stream) ---
    async function handleFile(file) {
        rulesSection.style.display = 'none'; // Hide rules when analyzing
        rulesBtn.innerText = 'VIEW RULES';

        try {
            const response = await fetch('/analyze', {
                method: 'POST',
                body: file, // Send binary directly to bypass Python Multipart ScannerError
                headers: { 'Content-Type': 'application/yaml' }
            });

            if (!response.ok) throw new Error("Server Error");


            const data = await response.json();
            renderDashboard(data);
        } catch (err) {
            console.error("DRC Error:", err);
            alert("Analysis failed. Ensure bridge_server.py is running.");
        }
    }

    // --- 4. UI Rendering (Summary Top, Raw Bottom) ---
    function renderDashboard(data) {
        dashboard.style.display = 'block';
        clusterList.innerHTML = '';

        // TOP: Summary Notice Cards
        if (data.results && Array.isArray(data.results)) {
            data.results.forEach(res => {
                if (res.findings && Array.isArray(res.findings)) {
                    res.findings.forEach(f => {
                        const card = document.createElement('div');
                        card.className = 'card';


                        const dot = document.createElement('div');
                        dot.className = 'dot';
                        // Set Red dot for Critical/Risks
                        if (f.crit === 'CRITICAL' || f.ref.toLowerCase().includes('risk')) {
                            dot.style.background = '#e60000';
                        } else {
                            dot.style.background = '#ff8c00'; // Orange for others
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

        // BOTTOM: Raw Detailed Output
        rawDisplay.textContent = JSON.stringify(data, null, 2);


        dashboard.scrollIntoView({ behavior: 'smooth' });
    }
};