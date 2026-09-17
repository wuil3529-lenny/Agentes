function updateLogs(text) {
    const el = document.getElementById('logs-content');
    if (el && el.innerText !== text) {
        el.innerText = text || 'Sin logs activos.';
        const panel = el.parentElement;
        panel.scrollTop = panel.scrollHeight;
    }
}

function updatePizarra(text) {
    const board = document.getElementById('kanban-board');
    if (!board) return;
    if (!text || text.trim() === '') {
        board.innerHTML = '<div style="color:var(--text-dim);">Pizarra vacía.</div>';
        return;
    }
    
    const parts = text.split(/##\s+(?=TKT-)/i);
    let html = '';
    
    parts.forEach(part => {
        if (!part.trim().toUpperCase().startsWith('TKT-')) return;
        
        const lines = part.split('\n');
        const titleLine = lines[0].trim();
        
        let desc = '', status = '', resp = '';
        lines.forEach(line => {
            if (line.match(/- \*\*Descripci[oó]n:\*\*/i)) {
                desc = line.replace(/- \*\*Descripci[oó]n:\*\*\s*/i, '').trim();
            } else if (line.match(/- \*\*Estado:\*\*/i)) {
                status = line.replace(/- \*\*Estado:\*\*\s*/i, '').trim();
            } else if (line.match(/- \*\*Responsable:\*\*/i)) {
                resp = line.replace(/- \*\*Responsable:\*\*\s*/i, '').trim();
            }
        });
        
        html += `
            <div class="ticket-card" style="border: 1px solid var(--border-color); padding: 10px; margin-bottom: 10px; border-radius: 4px; background: rgba(0,0,0,0.2);">
                <h4 style="margin: 0 0 5px 0; color: var(--accent-cyan); font-size: 14px;">${titleLine}</h4>
                <p style="margin: 0 0 10px 0; font-size: 12px; color: var(--text-dim);">${desc}</p>
                <div style="display: flex; justify-content: space-between; font-size: 11px; font-weight: bold;">
                    <span style="color: var(--accent-blue);">[ ${status} ]</span>
                    <span style="color: var(--accent-magenta);">Resp: ${resp}</span>
                </div>
            </div>
        `;
    });
    
    if (html === '') {
         board.innerHTML = '<div style="color:var(--text-dim);">No hay tickets activos.</div>';
    } else {
         board.innerHTML = html;
    }
}
