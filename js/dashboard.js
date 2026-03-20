window.onload = function() {
    console.log("DRC Advisor v2.5 Initializing... System Nominal.");

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

    // v2.3 Toggle View Elements
    const reportViewToggle = document.getElementById('reportViewToggle');
    const viewTypeText = document.getElementById('viewTypeText');

    // Modals
    const aboutModal = document.getElementById('aboutModal');
    const rulesModal = document.getElementById('rulesModal');
    const exampleModal = document.getElementById('exampleModal');

    // Close Buttons
    const closeAbout = document.getElementById('closeAbout');
    const closeRules = document.getElementById('closeRules');
    const closeExample = document.getElementById('closeExample');

    /* --- v2.3 Advisor Bot UI Elements --- */
    const botFab = document.getElementById('drc-bot-fab');
    const botPanel = document.getElementById('drc-bot-panel');
    const botClose = document.getElementById('drc-bot-close');
    const botMessages = document.getElementById('drc-bot-messages');
    const botInput = document.getElementById('drc-bot-input');
    const botSend = document.getElementById('drc-bot-send');
    const botIcon = "/static/bot.png"; 

    // ==========================================
    // 2. STATE MANAGEMENT
    // ==========================================
    let currentProfile = 'generic';
    let isOnlineMode = onlineToggle ? onlineToggle.checked : false;
    let isExternalReport = reportViewToggle ? reportViewToggle.checked : false;

    // ==========================================
    // 3. ADVISOR BOT LOGIC (v2.5 Ninetails)
    // ==========================================
    const toggleBot = () => {
        if (!botPanel) return;
        botPanel.style.display = botPanel.style.display === 'none' ? 'flex' : 'none';
        if (botPanel.style.display === 'flex') botInput.focus();
    };

    if (botFab) botFab.onclick = toggleBot;
    if (botClose) botClose.onclick = () => botPanel.style.display = 'none';

    function appendMessage(sender, text, isCode = false) {
        if (!botMessages) return;
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${sender}`;
        
        let html = isCode ? `<pre><code>${text}</code></pre>` : `<p>${text}</p>`;
        
        if (sender === 'bot') {
            msgDiv.innerHTML = `<img src="${botIcon}" class="msg-icon">${html}`;
        } else {
            msgDiv.innerHTML = html;
        }
        
        botMessages.appendChild(msgDiv);
        botMessages.scrollTop = botMessages.scrollHeight;
    }

    const handleSend = async () => {
        const val = botInput.value.trim();
        if (!val) return;

        // 1. UI: Append User Message and clear input
        appendMessage('user', val);
        botInput.value = '';

        const lowerVal = val.toLowerCase();

        // 2. Command Logic: Synthesis/Drafting
        if (lowerVal.includes('synthesize') || lowerVal.includes('reply') || lowerVal.includes('draft')) {
            
            const analysisData = sessionStorage.getItem('drc_report_data');
            
            if (!analysisData) {
                appendMessage('bot', '⚠️ **Context Missing**: Please perform a cluster analysis first by uploading a YAML/XML file.');
                return;
            }

            // Add a temporary "thinking" message
            appendMessage('bot', 'Connecting to the Engine for synthesis...');
            
            try {
                const res = await fetch('/api/bot-chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        message: val,
                        context: JSON.parse(analysisData) // The key "context" matches your Agent's **kwargs
                    })
                });

                if (!res.ok) throw new Error("Synthesis service unreachable");
                
                const data = await res.json();

                // 3. Handle Environment Error (-1)
                if (data.reply === -1 || data.response === -1) {
                    appendMessage('bot', `
                        <div style="color: #ee0000; border: 1px solid #ee0000; padding: 10px; border-radius: 4px; margin-top: 10px; background: rgba(238,0,0,0.05);">
                            <strong>AI Bridge Offline</strong><br>
                            Environment variables (MODEL_API, etc.) are not set on the server.
                        </div>
                    `);
                    return;
                }

                // 4. Success: Render the AI reply (isCode = true for formatted output)
                const botReply = data.reply || data.response;
                appendMessage('bot', botReply, true); 

            } catch (err) {
                appendMessage('bot', '❌ **Connection Error**: Ensure the Bridge Server is running on port 8090.');
                console.error("Bot Error:", err);
            }
        } 
        // 5. Basic Interactions
        else if (['hi', 'hello', 'hey', 'o/'].includes(lowerVal)) {
            appendMessage('bot', "Hello! o/ I'm the DRC Advisor Bot. I can turn your analysis into a professional customer reply. Try asking me to **'synthesize results'**!");
        }
        // 6. Trivial Fallback
        else {
            appendMessage('bot', "I'm currently focused on result synthesis. Try analyzing a file and then ask me to 'synthesize the findings' for a customer response.");
        }
    };

    if (botSend) botSend.onclick = handleSend;
    if (botInput) {
        botInput.onkeypress = (e) => { 
            if (e.key === 'Enter') handleSend(); 
        };
    }

    // ==========================================
    // 4. MODAL LOGIC (DRC v2.2 Standards)
    // ==========================================
    if (aboutBtn && aboutModal) aboutBtn.onclick = () => aboutModal.style.display = "block";
    if (viewRulesBtn && rulesModal) {
        viewRulesBtn.onclick = () => {
            rulesModal.style.display = "block";
            fetchRules();
        };
    }
    if (ruleExampleBtn && exampleModal) ruleExampleBtn.onclick = () => exampleModal.style.display = "block";
    if (closeAbout) closeAbout.onclick = () => aboutModal.style.display = "none";
    if (closeRules) closeRules.onclick = () => rulesModal.style.display = "none";
    if (closeExample) closeExample.onclick = () => exampleModal.style.display = "none";

    window.onclick = (event) => {
        if (event.target == aboutModal) aboutModal.style.display = "none";
        if (event.target == rulesModal) rulesModal.style.display = "none";
        if (event.target == exampleModal) exampleModal.style.display = "none";
    };

    // ==========================================
    // 5. DOCK CONTROLS
    // ==========================================
    if (onlineToggle) {
        onlineToggle.onchange = function() {
            isOnlineMode = this.checked;
            if (toggleText) {
                toggleText.innerText = isOnlineMode ? "Strict" : "Standard";
                toggleText.style.color = isOnlineMode ? "#ee0000" : "#333";
            }
        };
    }

    if (reportViewToggle) {
        reportViewToggle.onchange = function() {
            isExternalReport = this.checked;
            if (viewTypeText) {
                viewTypeText.innerText = isExternalReport ? "Popup" : "Inline";
                viewTypeText.style.color = isExternalReport ? "#007bff" : "#333";
            }
        };
    }

    // ==========================================
        // 5. DOCK CONTROLS (v2.5 Refined)
        // ==========================================
        if (profileSelect) {
                    profileSelect.onchange = function() {
                        currentProfile = this.value; // 'Review', 'Comparator', 'Simulate'
                        console.log("Mode Switched:", currentProfile);

                        // 1. Grab all UI containers
                        const mainDrop = document.getElementById('drop-zone');
                        const dualDrop = document.getElementById('dual-drop-container');
                        const simContainer = document.getElementById('simulator-container');
                        const dashboard = document.getElementById('dashboard');
                        const clusterList = document.getElementById('cluster-list');

                        // 2. THE CLEAN SWEEP: Hide everything and clear old results
                        if (mainDrop) mainDrop.style.display = 'none';
                        if (dualDrop) dualDrop.style.display = 'none';
                        if (simContainer) simContainer.style.display = 'none';
                        if (dashboard) dashboard.style.display = 'none';
                        if (clusterList) clusterList.innerHTML = "";

                        // 3. THE ROUTER: Turn on the lights for the selected mode
                        if (currentProfile === 'Comparator') {
                            if (dualDrop) dualDrop.style.display = 'flex';
                            if (typeof Comparator !== 'undefined') Comparator.reset();
                        } 
                        else if (currentProfile === 'Simulate') {
                            if (simContainer) simContainer.style.display = 'flex';
                            if (typeof Simulator !== 'undefined') Simulator.init();
                        } 
                        else {
                            // Default to Standard Reviewer
                            if (mainDrop) mainDrop.style.display = 'block';
                        }
                    };
                }

    if (kcsListBtn) kcsListBtn.onclick = () => window.open('https://access.redhat.com/solutions', '_blank');

    // ==========================================
    // 6. DRAG AND DROP / FILE UPLOAD
    // ==========================================
    if (dropZone) {
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.style.background = '#d9d9d9';
            dropZone.style.borderColor = '#ee0000';
        });

        dropZone.addEventListener('dragleave', () => {
            dropZone.style.background = '#b3b3b3';
            dropZone.style.borderColor = '#666';
        });

        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.style.background = '#b3b3b3';
            const files = e.dataTransfer.files;
            if (files.length > 0) handleFile(files[0]);
        });
    }

    if (uploadBtn && fileInput) {
        uploadBtn.onclick = () => fileInput.click();
        fileInput.onchange = (e) => {
            if (e.target.files.length > 0) handleFile(e.target.files[0]);
        };
    }

    async function handleFile(file) {
        if (!file) return;
        
        const originalText = uploadBtn.innerText;
        uploadBtn.innerText = "STREAMING TO BRIDGE...";
        uploadBtn.disabled = true;

        if (!isExternalReport) {
            dashboard.style.display = 'block';
            clusterList.innerHTML = '<div class="loading-box"><p style="color:white;">Analyzing binary stream...</p></div>';
        }

        try {
            const fileContent = await file.text();
            
            // --- THE TOGGLE: Automatic JVM Sniffing ---
            const isJVM = fileContent.includes("# JRE version:");
            const endpoint = isJVM ? '/api/analyze-jvm' : '/api/analyze';

            const response = await fetch(endpoint, {
                method: 'POST',
                body: fileContent,
                headers: {
                    'X-DRC-Profile': currentProfile,
                    'X-DRC-Eval-Undefined': isOnlineMode.toString(),
                    'Content-Type': 'text/plain'
                }
            });

            if (!response.ok) throw new Error(`Server Error: ${await response.text()}`);
            const data = await response.json();

            // Tag data with type for renderer
            if (data.metadata) data.metadata.isJVM = isJVM;

            sessionStorage.setItem('drc_report_data', JSON.stringify(data));
            console.log(`Analysis Context Locked (${isJVM ? 'JVM' : 'OCP'}).`);

            if (isExternalReport) {
                const reportWindow = window.open('report.html', 'DRC_Report', 'width=1100,height=900,scrollbars=yes');
                if (!reportWindow) alert("Popup blocked! Please allow popups.");
            } else {
                renderDashboard(data);
            }
        } catch (error) {
            alert("Analysis Failed: " + error.message);
        } finally {
            uploadBtn.innerText = originalText;
            uploadBtn.disabled = false;
        }
    }

    // ==========================================
    // 7. DASHBOARD & HISTOGRAM RENDERING
    // ==========================================
    function renderHistogram(summary) {
        let histContainer = document.getElementById('drc-histogram');
        if (!histContainer) {
            histContainer = document.createElement('div');
            histContainer.id = 'drc-histogram';
            histContainer.className = 'histogram-container';
            clusterList.parentNode.insertBefore(histContainer, clusterList);
        }

        const levels = ["CRITICAL", "ERROR", "WARNING", "NOTICE"];
        const counts = levels.map(l => summary[l] || 0);
        const maxCount = Math.max(...counts, 1);

        histContainer.innerHTML = levels.map(lvl => {
            const count = summary[lvl] || 0;
            const height = (count / maxCount) * 100;
            return `
                <div class="bar-wrapper">
                    <span class="bar-value">${count > 0 ? count : ''}</span>
                    <div class="bar-fill ${lvl.toLowerCase()}" style="height: ${height}%"></div>
                    <span class="bar-label">${lvl}</span>
                </div>`;
        }).join('');
    }

    function renderDashboard(data) {
        dashboard.style.display = 'block';
        clusterList.innerHTML = '';
        
        const oldHist = document.getElementById('drc-histogram');
        if (oldHist) oldHist.innerHTML = ''; 

        if (data.metadata && data.metadata.summary) {
            renderHistogram(data.metadata.summary);
        }

        // Handle JVM Tree Rendering
        if (data.metadata && data.metadata.isJVM) {
            const tree = data.results[0];
            const summaryTitle = document.createElement('h3');
            summaryTitle.className = 'section-title';
            summaryTitle.innerText = "JVM RUNTIME REVIEW";
            clusterList.appendChild(summaryTitle);

            for (const [section, content] of Object.entries(tree)) {
                if (section === "Summary") continue;
                const card = document.createElement('div');
                card.className = 'card';
                card.style.flexDirection = 'column';
                card.style.alignItems = 'flex-start';

                let html = `<strong style="color: #ee0000; border-bottom: 1px solid #ccc; width: 100%; margin-bottom: 10px; display: block;">${section.replace(/_/g, ' ').toUpperCase()}</strong><ul style="list-style: none; padding: 0; width: 100%;">`;
                
                for (const [key, val] of Object.entries(content)) {
                    if (key === "Note" && val) {
                        const crit = (content.Crit || 'NOTICE').toUpperCase();
                        const color = crit === 'CRITICAL' ? '#e60000' : (crit === 'WARNING' ? '#007bff' : '#28a745');
                        html += `<li style="background: rgba(0,0,0,0.05); padding: 8px; border-left: 4px solid ${color}; margin: 5px 0;"><strong>ADVICE:</strong> ${val}</li>`;
                    } else if (key !== "Crit") {
                        html += `<li style="font-size: 0.9em; margin: 3px 0;"><strong>${key.replace(/_/g, ' ')}:</strong> ${val}</li>`;
                    }
                }
                html += `</ul>`;
                card.innerHTML = html;
                clusterList.appendChild(card);
            }
        } 
        // Handle Standard OCP Findings Rendering
        else {
            const sourceData = Array.isArray(data) ? data : (data.results || []);
            const summaryTitle = document.createElement('h3');
            summaryTitle.className = 'section-title';
            summaryTitle.innerText = "ANALYSIS SUMMARY";
            clusterList.appendChild(summaryTitle);

            sourceData.forEach(res => {
                if (res.findings) {
                    res.findings.forEach(f => {
                        const card = document.createElement('div');
                        card.className = 'card';
                        const dot = document.createElement('div');
                        dot.className = 'dot';
                        
                        const severity = f.crit ? f.crit.toUpperCase() : 'NOTICE';
                        if (severity === 'CRITICAL') dot.style.background = '#e60000';
                        else if (severity === 'IMPORTANT' || severity === 'ERROR') dot.style.background = '#ff8c00';
                        else if (severity === 'WARNING') dot.style.background = '#007bff';
                        else dot.style.background = '#28a745';

                        const text = document.createElement('div');
                        text.className = 'card-text';
                        let cleanRef = (f.ref || '').replace('NOTICE: ', '').replace(/_/g, ' ');

                        const kcsPattern = /(KCS|KB)\s*(\d+)/gi;
                        const linkedRef = cleanRef.replace(kcsPattern, (match, type, id) => {
                            return `<a href="https://access.redhat.com/solutions/${id}" target="_blank" style="color: #005fba; text-decoration: underline; font-weight: bold;">${match}</a>`;
                        });

                        text.innerHTML = `<strong>${res.name.toUpperCase()}:</strong> ${linkedRef}`;
                        card.appendChild(dot);
                        card.appendChild(text);
                        clusterList.appendChild(card);
                    });
                }
            });
        }

        const rawTitle = document.createElement('h3');
        rawTitle.className = 'section-title';
        rawTitle.style.marginTop = "40px";
        rawTitle.innerText = "RAW DETAILED DATA";
        clusterList.appendChild(rawTitle);

        const rawBox = document.createElement('pre');
        rawBox.className = 'raw-box'; 
        rawBox.innerText = JSON.stringify(data, null, 2);
        clusterList.appendChild(rawBox);
    }

    async function fetchRules() {
        const rulesContent = document.getElementById('rulesContent');
        if (!rulesContent) return;
        rulesContent.innerText = "Fetching rules...";
        try {
            const res = await fetch('/api/rules');
            const data = await res.json();
            rulesContent.innerText = JSON.stringify(data, null, 4);
        } catch (e) { rulesContent.innerText = "Error loading rules."; }
    }

    if (exportBtn) {
        exportBtn.onclick = () => {
            const content = clusterList.innerText;
            if (content.length < 5) return;
            const blob = new Blob([content], { type: 'text/plain' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'DRC_Report.txt';
            a.click();
        };
    }
};