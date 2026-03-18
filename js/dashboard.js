window.onload = function() {
    console.log("DRC Advisor v2.3 Initializing... System Nominal.");

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

   // ==========================================
    // 3. ADVISOR BOT LOGIC (v2.3 Charizard)
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

            // Display user message and clear input
            appendMessage('user', val);
            botInput.value = '';

            const lowerVal = val.toLowerCase();

            // 1. Trigger Synthesis/Drafting Logic
            if (lowerVal.includes('synthesize') || lowerVal.includes('reply') || lowerVal.includes('draft')) {
                appendMessage('bot', 'Connecting to the Charizard Engine for synthesis...');
                
                try {
                    const res = await fetch('/api/bot-reply');
                    if (!res.ok) throw new Error("Synthesis service unavailable");
                    
                    const data = await res.text();
                    // Render synthesis as a pre-formatted block (isCode = true)
                    appendMessage('bot', data, true); 
                } catch (err) {
                    appendMessage('bot', 'Sorry, I had trouble connecting to the synthesis engine. Ensure the analysis is complete before drafting.');
                }
            } 
            // 2. Handle Common Greetings
            else if (lowerVal === 'hi' || lowerVal === 'hello' || lowerVal === 'hey' || lowerVal === 'o/') {
                appendMessage('bot', "Hello! o/ I'm the DRC Advisor Bot. I can turn your analysis into a professional customer reply based on collaborative engineering standards. Try asking me to **'synthesize results'**!");
            }
            // 3. "Not Implemented Yet" Fail-safe
            else {
                appendMessage('bot', "Sorry, that command is **not implemented yet**. Currently, I am focused on result synthesis and expertise in collaborative standards like DG tuning (https://docs.redhat.com/en/documentation/red_hat_data_grid/8.5/html/data_grid_performance_and_sizing_guide/index).");
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
    if (aboutBtn && aboutModal) {
        aboutBtn.onclick = () => aboutModal.style.display = "block";
    }

    if (viewRulesBtn && rulesModal) {
        viewRulesBtn.onclick = () => {
            rulesModal.style.display = "block";
            fetchRules();
        };
    }

    if (ruleExampleBtn && exampleModal) {
        ruleExampleBtn.onclick = () => exampleModal.style.display = "block";
    }

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

    if (profileSelect) {
        profileSelect.onchange = function() {
            currentProfile = this.value;
            console.log("Active Profile:", currentProfile);
        };
    }

    if (kcsListBtn) {
        kcsListBtn.onclick = () => window.open('https://access.redhat.com/solutions', '_blank');
    }

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
        dashboard.style.display = 'block';
        clusterList.innerHTML = '<div class="loading-box"><p style="color:white;">Analyzing binary stream...</p></div>';

        try {
            const fileContent = await file.text();
            const response = await fetch('/api/analyze', {
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
            renderDashboard(data);
        } catch (error) {
            clusterList.innerHTML = `<div class="card critical"><h3>Analysis Failed</h3><p>${error.message}</p></div>`;
        }
    }

    // ==========================================
    // 7. DASHBOARD RENDERING
    // ==========================================
    function renderDashboard(data) {
        dashboard.style.display = 'block';
        clusterList.innerHTML = '';
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
                    else if (severity === 'IMPORTANT') dot.style.background = '#ff8c00';
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