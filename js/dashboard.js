window.onload = function() {
    console.log("DRC Advisor v2.2 Initializing... System Nominal.");

    // ==========================================
    // 1. DOM ELEMENT MAPPING
    // ==========================================
    const uploadBtn = document.getElementById('upload-btn');
    const fileInput = document.getElementById('file-input');
    const dropZone = document.getElementById('drop-zone');
    const dashboard = document.getElementById('dashboard');
    const clusterList = document.getElementById('cluster-list');
    
    // Header Elements
    const aboutBtn = document.getElementById('aboutBtn');
    const sourceGitBtn = document.getElementById('sourceGitBtn');

    // Utility Dock Elements (v2.2)
    const onlineToggle = document.getElementById('onlineToggle');
    const toggleText = document.getElementById('toggleText');
    const profileSelect = document.getElementById('profileSelect');
    const viewRulesBtn = document.getElementById('viewRulesBtn');
    const ruleExampleBtn = document.getElementById('ruleExampleBtn');
    const kcsListBtn = document.getElementById('kcsListBtn');
    const exportBtn = document.getElementById('exportBtn');

    // Modals
    const aboutModal = document.getElementById('aboutModal');
    const rulesModal = document.getElementById('rulesModal');
    const exampleModal = document.getElementById('exampleModal');

    // Close Buttons (Using specific IDs for v2.2 stability)
    const closeAbout = document.getElementById('closeAbout');
    const closeRules = document.getElementById('closeRules');
    const closeExample = document.getElementById('closeExample');

    // ==========================================
    // 2. STATE MANAGEMENT
    // ==========================================
    let currentProfile = 'generic';
    let isOnlineMode = false;

    // ==========================================
    // 3. MODAL LOGIC (FIXED)
    // ==========================================
    // Fix 1: About logic explicitly targeting the aboutModal ID
    if (aboutBtn) {
        aboutBtn.onclick = function() {
            console.log("Opening About Modal...");
            if (aboutModal) aboutModal.style.display = "block";
        }
    }

    if (viewRulesBtn) {
        viewRulesBtn.onclick = function() {
            if (rulesModal) {
                rulesModal.style.display = "block";
                fetchRules();
            }
        }
    }

    // Fix 2: YAML Rules Example on the floating menu (Bottom)
    if (ruleExampleBtn) {
        ruleExampleBtn.onclick = function() {
            console.log("Opening Rule Example Modal...");
            if (exampleModal) exampleModal.style.display = "block";
        }
    }

    if (closeAbout) {
        closeAbout.onclick = function() {
            aboutModal.style.display = "none";
        }
    }

    if (closeRules) {
        closeRules.onclick = function() {
            rulesModal.style.display = "none";
        }
    }

    if (closeExample) {
        closeExample.onclick = function() {
            exampleModal.style.display = "none";
        }
    }

    window.onclick = function(event) {
        if (event.target == aboutModal) aboutModal.style.display = "none";
        if (event.target == rulesModal) rulesModal.style.display = "none";
        if (event.target == exampleModal) exampleModal.style.display = "none";
    }

    // ==========================================
    // 4. DOCK CONTROLS (UI WORKING)
    // ==========================================
    if (onlineToggle) {
        onlineToggle.onchange = function() {
            isOnlineMode = this.checked;
            if (toggleText) {
                toggleText.innerText = isOnlineMode ? "ONLINE" : "OFFLINE";
                toggleText.style.color = isOnlineMode ? "#ee0000" : "#333";
            }
        }
    }

    if (profileSelect) {
        profileSelect.onchange = function() {
            currentProfile = this.value;
            console.log("Active Profile:", currentProfile);
        }
    }

    if (kcsListBtn) {
        kcsListBtn.onclick = function() {
            window.open('https://access.redhat.com/solutions', '_blank');
        }
    }

    // ==========================================
    // 5. DRAG AND DROP HANDLERS
    // ==========================================
    if (dropZone) {
        dropZone.addEventListener('dragover', function(e) {
            e.preventDefault();
            e.stopPropagation();
            dropZone.style.background = '#d9d9d9';
            dropZone.style.borderColor = '#ee0000';
        });

        dropZone.addEventListener('dragleave', function(e) {
            e.preventDefault();
            e.stopPropagation();
            dropZone.style.background = '#b3b3b3';
            dropZone.style.borderColor = '#666';
        });

        dropZone.addEventListener('drop', function(e) {
            e.preventDefault();
            e.stopPropagation();
            dropZone.style.background = '#b3b3b3';
            dropZone.style.borderColor = '#666';
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                handleFile(files[0]);
            }
        });
    }

    // ==========================================
    // 6. FILE ANALYSIS CORE (FIXED)
    // ==========================================
    // Fix 3: Select YAML button now triggers analysis
    if (uploadBtn && fileInput) {
        uploadBtn.onclick = function() {
            fileInput.click();
        }
        fileInput.onchange = function(e) {
            if (e.target.files.length > 0) {
                console.log("Analyzing file via manual upload...");
                handleFile(e.target.files[0]);
            }
        }
    }

    async function handleFile(file) {
        if (!file) return;

        dashboard.style.display = 'block';
        clusterList.innerHTML = '<div class="loading-box"><p>Analyzing binary stream...</p></div>';

        const formData = new FormData();
        formData.append('file', file);
        
        try {
            const response = await fetch('/api/analyze', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-DRC-Profile': currentProfile,
                    'X-DRC-Online': isOnlineMode
                }
            });

            const data = await response.json();
            renderDashboard(data);

        } catch (error) {
            console.error("Analysis Failed:", error);
            clusterList.innerHTML = '<div class="card critical"><h3>Analysis Failed</h3><p>' + error.message + '</p></div>';
        }
    }

    // ==========================================
    // 7. DASHBOARD RENDERING (VERBOSE)
    // ==========================================
    function renderDashboard(data) {
        while (clusterList.firstChild) {
            clusterList.removeChild(clusterList.firstChild);
        }

        if (!data.findings || data.findings.length === 0) {
            const emptyCard = document.createElement('div');
            emptyCard.className = 'card notice';
            emptyCard.innerHTML = '<h3>No Issues Found</h3><p>Configuration is compliant.</p>';
            clusterList.appendChild(emptyCard);
            return;
        }

        for (let i = 0; i < data.findings.length; i++) {
            const finding = data.findings[i];
            const card = document.createElement('div');
            const severity = finding.severity.toLowerCase();
            card.className = 'card ' + severity;

            const header = document.createElement('div');
            header.className = 'card-header';
            header.innerHTML = '<h3>' + finding.name + '</h3>';

            const body = document.createElement('div');
            body.className = 'card-body';
            body.innerHTML = '<p>' + finding.message + '</p>';

            if (finding.kcs_url) {
                const kcsLink = document.createElement('a');
                kcsLink.href = finding.kcs_url;
                kcsLink.target = '_blank';
                kcsLink.className = 'kcs-link';
                kcsLink.innerText = 'View KCS Solution';
                body.appendChild(document.createElement('hr'));
                body.appendChild(kcsLink);
            }

            card.appendChild(header);
            card.appendChild(body);
            clusterList.appendChild(card);
        }
    }

    // ==========================================
    // 8. UTILITIES (EXPORT / RULES)
    // ==========================================
    async function fetchRules() {
        const rulesContent = document.getElementById('rulesContent');
        if (rulesContent) {
            rulesContent.innerText = "Fetching rules...";
            try {
                const res = await fetch('/api/rules');
                const data = await res.json();
                rulesContent.innerText = JSON.stringify(data, null, 4);
            } catch (e) {
                rulesContent.innerText = "Error loading rules.";
            }
        }
    }

    if (exportBtn) {
        exportBtn.onclick = function() {
            const content = clusterList.innerText;
            if (content.length < 5) return alert("Nothing to export.");
            const blob = new Blob([content], { type: 'text/plain' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = 'DRC_Report.txt';
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        }
    }
}