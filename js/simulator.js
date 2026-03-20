/**
 * DRC Advisor v2.5 - Live OCP Simulator
 * 10:30 PM ET Build - Optimized for index.html integration
 */

const Simulator = {
    init: function() {
        const consoleBox = document.getElementById('sim-console');
        const simLabel = document.getElementById('sim-label');
        
        if (consoleBox) {
            consoleBox.style.display = 'none';
            consoleBox.innerHTML = "<p>> OCP SIMULATOR READY. WAITING FOR YAML...</p>";
        }
        if (simLabel) {
            simLabel.innerText = "🚀 DRAG YAML HERE FOR OCP DRY-RUN DEPLOYMENT";
        }

        this.bindEvents();
    },

    bindEvents: function() {
        const dropZone = document.getElementById('sim-drop-zone');
        const fileInput = document.getElementById('file-sim');

        if (!dropZone) return;

        // 1. Handle Clicks (Proxy to hidden input)
        dropZone.onclick = () => fileInput.click();
        fileInput.onchange = (e) => {
            if (e.target.files[0]) this.runDeployment(e.target.files[0]);
        };

        // 2. Handle Drag & Drop
        dropZone.ondragover = (e) => {
            e.preventDefault();
            dropZone.style.borderColor = "#28a745";
            dropZone.style.background = "rgba(40, 167, 69, 0.1)";
        };

        dropZone.ondragleave = () => {
            dropZone.style.borderColor = "#28a745";
            dropZone.style.background = "rgba(40, 167, 69, 0.05)";
        };

        dropZone.ondrop = (e) => {
            e.preventDefault();
            dropZone.style.background = "rgba(40, 167, 69, 0.05)";
            const file = e.dataTransfer.files[0];
            if (file) this.runDeployment(file);
        };
    },

    /**
         * OCP Simulator v2.5 - Recursive Auth Build
         * Handles dry-run and pops credentials if session is invalid.
         */
        runDeployment: async function(file, token = null, server = null) {
        const consoleBox = document.getElementById('sim-console');
        consoleBox.style.display = "block";

        const headers = {};
        if (token && server) {
            headers['X-OCP-Token'] = token;
            headers['X-OCP-Server'] = server;
        }

        try {
            const content = await file.text();
            const response = await fetch('/api/simulate-deploy', {
                method: 'POST',
                headers: headers,
                body: content
            });
            const data = await response.json();

            if (data.status === -1) {
                consoleBox.innerHTML += `<span style="color:orange;">⚠️ Token Authentication Required.</span><br>`;
                
                // POPUP BOXES
                const s = prompt("🌐 OCP API Server URL:", "https://api.sunbro2.nasa.az.cee.support:6443");
                const t = prompt("🔑 OCP Token (sha256~...):");
                
                if (s && t) {
                    return this.runDeployment(file, t, s);
                }
                return;
            }

            // Render Success/Fail...
            if (data.success) {
                consoleBox.innerHTML += `<span style="color:#28a745;">✅ VALIDATED ON CLUSTER</span><br><pre>${data.stdout}</pre>`;
            } else {
                consoleBox.innerHTML += `<span style="color:#ee0000;">❌ OCP REJECTED</span><br><pre style="color:orange;">${data.stderr}</pre>`;
            }
        } catch (e) {
            consoleBox.innerHTML += `<p style="color:red;">Bridge Error.</p>`;
        }
    }
};