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
    let isOnlineMode = onlineToggle ? onlineToggle.checked : false;

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
                toggleText.innerText = isOnlineMode ? "Strict" : "Standard";
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
    clusterList.innerHTML = '<div class="loading-box"><p style="color:white;">Analyzing binary stream...</p></div>';

    try {
        // 1. Read the file content as text first
        const fileContent = await file.text();

        // 2. Send the RAW text, not FormData
        const response = await fetch('/api/analyze', {
            method: 'POST',
            body: fileContent, // Sending raw YAML/XML content
            headers: {
                'X-DRC-Profile': currentProfile,
                'X-DRC-Eval-Undefined': isOnlineMode.toString(),
                'Content-Type': 'text/plain'
            }
        });

        if (!response.ok) {
            const errText = await response.text();
            throw new Error(`Server Error (${response.status}): ${errText}`);
        }

        const data = await response.json();
        renderDashboard(data);

    } catch (error) {
        console.error("Analysis Failed:", error);
        clusterList.innerHTML = `
            <div class="card critical">
                <h3>Analysis Failed</h3>
                <p>${error.message}</p>
            </div>`;
    }
}

    // ==========================================
    // 7. DASHBOARD RENDERING (VERBOSE)
    // ==========================================
    /**
     * DRC Advisor v2.2 - Final Result Renderer
     * Features: White Pill Cards, Color Logic (Red/Orange/Blue/Green), and Auto-KCS Linking.
     */
    function renderDashboard(data) {
        dashboard.style.display = 'block';
        clusterList.innerHTML = '';

        // Handle both raw array [ {...} ] and wrapped object { results: [...] }
        const sourceData = Array.isArray(data) ? data : (data.results || []);

        // --- A. SUMMARY SECTION ---
        const summaryTitle = document.createElement('h3');
        summaryTitle.className = 'section-title';
        summaryTitle.innerText = "ANALYSIS SUMMARY";
        clusterList.appendChild(summaryTitle);

        sourceData.forEach(res => {
            if (res.findings && Array.isArray(res.findings)) {
                res.findings.forEach(f => {
                    // 1. Create the White Card Container
                    const card = document.createElement('div');
                    card.className = 'card';

                    // 2. Create the Status Dot
                    const dot = document.createElement('div');
                    dot.className = 'dot';
                    
                    // Color Mapping
                    const severity = f.crit ? f.crit.toUpperCase() : 'NOTICE';
                    const refText = f.ref || '';

                    if (severity === 'CRITICAL' || refText.toLowerCase().includes('risk')) {
                        dot.style.background = '#e60000'; // RED
                    } else if (severity === 'IMPORTANT') {
                        dot.style.background = '#ff8c00'; // ORANGE
                    } else if (severity === 'WARNING') {
                        dot.style.background = '#007bff'; // BLUE
                    } else if (severity === 'NOTICE') {
                        dot.style.background = '#28a745'; // GREEN
                    }

                    // 3. Create Text Content with Regex Linker
                    const text = document.createElement('div');
                    text.className = 'card-text';
                    
                    // Formatting: Strip prefixes and underscores
                    let cleanRef = refText.replace('NOTICE: ', '').replace(/_/g, ' ');

                    /**
                     * KCS LINKER:
                     * Matches "KCS" or "KB" followed by a space (optional) and numbers.
                     * Example: "KCS 6991230" -> <a href="...">KCS 6991230</a>
                     */
                    const kcsPattern = /(KCS|KB)\s*(\d+)/gi;
                    const linkedRef = cleanRef.replace(kcsPattern, (match, type, id) => {
                        return `<a href="https://access.redhat.com/solutions/${id}" 
                                   target="_blank" 
                                   title="Open Red Hat Solution ${id}"
                                   style="color: #005fba; text-decoration: underline; font-weight: bold;">
                                   ${match}
                                </a>`;
                    });

                    // Render: CLUSTER-NAME: MESSAGE
                    text.innerHTML = `<strong>${res.name.toUpperCase()}:</strong> ${linkedRef}`;

                    // 4. Final Assembly
                    card.appendChild(dot);
                    card.appendChild(text);
                    clusterList.appendChild(card);
                });
            }
        });

        // --- B. RAW DATA SECTION ---
        const rawTitle = document.createElement('h3');
        rawTitle.className = 'section-title';
        rawTitle.style.marginTop = "40px";
        rawTitle.innerText = "RAW DETAILED DATA";
        clusterList.appendChild(rawTitle);

        const rawBox = document.createElement('pre');
        rawBox.className = 'raw-box'; 
        rawBox.style.background = '#1e1e1e';
        rawBox.style.color = '#00ff00';
        rawBox.style.padding = '15px';
        rawBox.style.borderRadius = '8px';
        rawBox.innerText = JSON.stringify(data, null, 2);
        clusterList.appendChild(rawBox);
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