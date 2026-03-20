/**
 * DRC Advisor v2.5 - Comparator Module
 * Final 10:35 PM ET Build - Type-Aware Rendering
 */

const Comparator = {
    treeA: null,
    treeB: null,

    reset: function() {
        this.treeA = null;
        this.treeB = null;
        const labelA = document.getElementById('label-a');
        const labelB = document.getElementById('label-b');
        if (labelA) labelA.innerText = "SOURCE (A)";
        if (labelB) labelB.innerText = "TARGET (B)";
        console.log("Comparator Memory Flushed.");
    },

    parseData: function(data) {
        // Sniff for the tree inside the Bridge response
        if (data.results && data.results[0]) return data.results[0];
        if (Array.isArray(data)) return data[0];
        return data;
    },

    render: function() {
        if (!this.treeA || !this.treeB) return;

        const dashboard = document.getElementById('dashboard');
        const clusterList = document.getElementById('cluster-list');
        
        if (dashboard) dashboard.style.display = 'block';
        if (clusterList) {
            clusterList.innerHTML = `<h2 class="section-title">⚖️ DRIFT ANALYSIS: A vs B</h2>`;
            
            // Get unique categories from both trees
            const categories = new Set([
                ...Object.keys(this.treeA),
                ...Object.keys(this.treeB)
            ]);
            
            categories.forEach(cat => {
                if (['metadata', 'Summary', 'findings', 'Crit', 'Note'].includes(cat)) return;

                const valA = this.treeA[cat];
                const valB = this.treeB[cat];

                let html = `<div class="card" style="flex-direction:column; align-items:flex-start; margin-bottom: 20px;">
                    <h3 style="color:#ee0000; width:100%; border-bottom:1px solid #333; margin-bottom:10px;">${cat.toUpperCase()}</h3>
                    <table class="drift-table" style="width:100%; border-collapse:collapse; font-size:12px;">`;

                // CASE 1: Nested Object (like JVM_SETTINGS: { Xmx: "4g" })
                if (typeof valA === 'object' && valA !== null) {
                    const keys = new Set([
                        ...Object.keys(valA), 
                        ...Object.keys(valB || {})
                    ]);
                    
                    keys.forEach(key => {
                        if (key === "Note" || key === "Crit") return;
                        const subA = valA[key] || "—";
                        const subB = (valB && valB[key]) ? valB[key] : "—";
                        html += this.generateRow(key, subA, subB);
                    });
                } 
                // CASE 2: Simple Value (like NAMESPACE: "prod")
                else {
                    html += this.generateRow("Setting Value", valA || "—", valB || "—");
                }

                html += `</table></div>`;
                clusterList.innerHTML += html;
            });
        }
    },

    generateRow: function(label, a, b) {
        const drift = String(a).trim() !== String(b).trim();
        return `<tr style="${drift ? 'background:rgba(238,0,0,0.1); font-weight:bold;' : ''} border-bottom:1px solid #222;">
                    <td style="padding:8px; color:#888; width:30%;">${label.replace(/_/g, ' ')}</td>
                    <td style="width:35%; color: ${drift ? '#fff' : '#ccc'};">${a}</td>
                    <td style="width:35%; color: ${drift ? '#fff' : '#ccc'};">
                        ${b} ${drift ? '<span style="color:#ee0000; margin-left:10px;">⚠️ DRIFT</span>' : ''}
                    </td>
                </tr>`;
    }
};

// Independent logic for the dual-drop zones
document.addEventListener('DOMContentLoaded', () => {
    const fileA = document.getElementById('file-a');
    const fileB = document.getElementById('file-b');
    const dropA = document.getElementById('drop-zone-a');
    const dropB = document.getElementById('drop-zone-b');

    if (dropA) dropA.onclick = () => fileA.click();
    if (dropB) dropB.onclick = () => fileB.click();

    const process = async (input, slot) => {
        const file = input.files[0];
        if (!file) return;

        const label = document.getElementById(slot === 'A' ? 'label-a' : 'label-b');
        label.innerText = "⌛ Analyzing...";

        try {
            const content = await file.text();
            const endpoint = content.includes("# JRE version:") ? '/api/analyze-jvm' : '/api/analyze';
            const res = await fetch(endpoint, { method: 'POST', body: content });
            const data = await res.json();
            
            if (slot === 'A') Comparator.treeA = Comparator.parseData(data);
            else Comparator.treeB = Comparator.parseData(data);

            label.innerText = `✅ ${file.name}`;
            if (Comparator.treeA && Comparator.treeB) Comparator.render();
        } catch (e) {
            label.innerText = "❌ Error";
            console.error(e);
        }
    };

    if (fileA) fileA.onchange = () => process(fileA, 'A');
    if (fileB) fileB.onchange = () => process(fileB, 'B');
});