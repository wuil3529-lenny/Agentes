function togglePanel(panelId) {
    const panel = document.getElementById(panelId);
    
    if (['gpu-panel', 'ram-panel', 'net-panel'].includes(panelId)) {
        const prefix = panelId.split('-')[0];
        const collapsed = document.getElementById(`${prefix}-collapsed`);
        if (panel.classList.contains('hidden')) {
            panel.classList.remove('hidden');
            collapsed.classList.add('hidden');
        } else {
            panel.classList.add('hidden');
            collapsed.classList.remove('hidden');
        }
    } 

    if (['gpu-panel', 'ram-panel', 'net-panel'].includes(panelId)) {
        const anyExpanded = document.querySelectorAll('#left-sidebar .panel:not(.hidden)').length > 0;
        document.getElementById('left-sidebar').style.minWidth = anyExpanded ? '280px' : '60px';
    }

    else if (panelId === 'kanban-panel') {
        const collapsed = document.getElementById('kanban-collapsed');
        if (panel.classList.contains('hidden')) {
            panel.classList.remove('hidden');
            collapsed.classList.add('hidden');
        } else {
            panel.classList.add('hidden');
            collapsed.classList.remove('hidden');
        }
    }
}


function connect() {
    window.ws = new WebSocket(`ws://${window.location.host}/ws`);
    ws.onclose = () => { 
        updateEstado({estado: 'desconectada'}); 
        if (typeof setCrewStatus === 'function') setCrewStatus(false);
        const btn = document.getElementById('system-status-btn'); 
        if(btn) { 
            btn.innerHTML = '<div class=\'w-2 h-2 rounded-full bg-error shadow-[0_0_8px_#ff5449] animate-pulse\'></div><span class=\'font-label text-[10px] text-error uppercase tracking-widest\'>DESCONECTADO</span>'; 
            btn.classList.replace('border-primary/30', 'border-error/30'); 
        } 
        setTimeout(connect, 3000); // Auto-reconnect
    };
    ws.onerror = () => { 
        if (typeof setCrewStatus === 'function') setCrewStatus(false);
        ws.close(); 
    };
    ws.onmessage = function(event) {
        try {
            const data = JSON.parse(event.data);
            if (data.type === 'update') {
                if (typeof setCrewStatus === 'function') {
                    const est = data.estado_tripulacion;
                    const isOnline = (data.tripulacion_activa === true) || (est && (est.estado === 'activa' || est.estado === 'conectada' || est.estado === 'activo'));
                    setCrewStatus(isOnline);
                }
                if (typeof updatePizarra !== 'undefined') updatePizarra(data.pizarra);
                if (typeof updateArchivados !== 'undefined') updateArchivados(data.tickets_archivados);
                if (data.tareas_programadas) { cacheProgramadas = data.tareas_programadas; renderProgramadas(); }
                if (typeof updateChat !== 'undefined') updateChat(data.chat);
                if (typeof updateLogs !== 'undefined') updateLogs(data.logs);
                if (typeof updateCostos !== 'undefined') updateCostos(data.costos);
                if (typeof updateEstado !== 'undefined') updateEstado(data.estado_tripulacion);
                try { updateMainMetrics(data.system, data.costos, data.pizarra); } catch(e) { console.error('Metrics Error:', e); }
            }
        } catch (e) {
            console.error('WS Error:', e);
            const btn = document.getElementById('system-status-btn');
            if(btn) btn.innerHTML = '<span class="text-error">Error: ' + e.message + '</span>';
        }
    };
}

function updateMainMetrics(sys, costos, pizarra) {
    if (costos) {
        // Update global metrics
        const mTokens = document.getElementById('metric-tokens');
        const mCost = document.getElementById('metric-cost');
        if (mTokens) {
            let tokensStr = costos.tokens;
            if (costos.tokens >= 1000000) tokensStr = (costos.tokens / 1000000).toFixed(1) + 'M';
            else if (costos.tokens >= 1000) tokensStr = (costos.tokens / 1000).toFixed(1) + 'K';
            mTokens.innerText = tokensStr;
            const mTokSub = document.getElementById('metric-tokens-sub');
            if (mTokSub) mTokSub.innerText = costos.tokens.toLocaleString() + ' tokens totales';
        }
        if (mCost) {
            mCost.innerText = '$' + costos.costo.toFixed(2);
            const mCostSub = document.getElementById('metric-cost-sub');
            if (mCostSub) {
                let pct = ((costos.costo / 10.0) * 100).toFixed(1);
                mCostSub.innerText = `Presupuesto ($10): ${pct}%`;
            }
        }
        
        // Update per-agent metrics
        const ags = ['luffy', 'zoro', 'sanji', 'nami', 'robin'];
        ags.forEach(ag => {
            let agTokens = 0;
            let agCosto = 0.0;
            if (costos.agentes && costos.agentes[ag]) {
                agTokens = costos.agentes[ag].tokens || 0;
                agCosto = costos.agentes[ag].costo || 0.0;
            }
            const elTokens = document.getElementById('tokens-' + ag);
            const elCosto = document.getElementById('costo-' + ag);
            const elBar = document.getElementById('bar-' + ag);
            
            if (elTokens) elTokens.innerText = agTokens.toLocaleString();
            if (elCosto) elCosto.innerText = agCosto.toFixed(3);
            if (elBar) {
                // Let's make the bar reflect the percentage of total tokens
                let pct = 0;
                if (costos.tokens > 0) {
                    pct = (agTokens / costos.tokens) * 100;
                }
                elBar.style.width = Math.min(pct, 100) + '%';
            }
        });
    }

    if (sys) {
        if (sys.ram) {
            const elRam = document.getElementById('hw-ram-val');
            if (elRam) elRam.innerText = (sys.ram.percent || 0) + '%';
        }
        if (sys.cpu !== undefined) {
            const elCpu = document.getElementById('hw-cpu-val');
            if (elCpu) elCpu.innerText = sys.cpu + '%';
        }
        const statusSub = document.getElementById('hw-status-text');
        if (statusSub) {
            const cpu = sys.cpu || 0;
            const ram = (sys.ram && sys.ram.percent) || 0;
            if (cpu > 85 || ram > 90) {
                statusSub.innerText = 'Carga Crítica de Hardware';
                statusSub.className = 'text-error';
            } else if (cpu > 60 || ram > 75) {
                statusSub.innerText = 'Carga Moderada';
                statusSub.className = 'text-tertiary';
            } else {
                statusSub.innerText = 'Carga de sistema estable';
                statusSub.className = 'text-secondary';
            }
        }
        const netUp = document.getElementById('net-up');
        const netDown = document.getElementById('net-down');
        if (netUp && sys.network) netUp.innerText = (sys.network.up_speed / 1024).toFixed(1);
        if (netDown && sys.network) netDown.innerText = (sys.network.down_speed / 1024).toFixed(1);
    }

    if (pizarra) {
        const elPrec = document.getElementById('metric-precision');
        if (elPrec) {
            const total = pizarra.length;
            const completas = pizarra.filter(t => (t.estado || '').toLowerCase().includes('complet') || (t.estado || '').toLowerCase().includes('archiv')).length;
            let prec = total > 0 ? ((completas / total) * 100).toFixed(1) : '99.4';
            elPrec.innerText = prec + '%';
        }
    }
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/[&<>"']/g, function(m) {
        return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[m];
    });
}

function updateChat(messages) {
    const container = document.getElementById('chat-messages');
    if (!container) return;
    
    const msgList = Array.isArray(messages) ? messages : (messages && messages.mensajes ? messages.mensajes : []);
    
    const agentColors = {
        'usuario': { border: 'border-primary/40', bg: 'bg-primary/20', text: 'text-primary', name: 'Capitán (Tú)' },
        'luffy': { border: 'border-primary/50', bg: 'bg-primary/10', text: 'text-primary', name: 'Luffy' },
        'zoro': { border: 'border-secondary/50', bg: 'bg-secondary/10', text: 'text-secondary', name: 'Zoro' },
        'sanji': { border: 'border-tertiary/50', bg: 'bg-tertiary/10', text: 'text-tertiary', name: 'Sanji' },
        'nami': { border: 'border-amber-400/50', bg: 'bg-amber-400/10', text: 'text-amber-400', name: 'Nami' },
        'robin': { border: 'border-purple-400/50', bg: 'bg-purple-400/10', text: 'text-purple-400', name: 'Robin' }
    };

    if (container.dataset.lastCount != msgList.length) {
        container.dataset.lastCount = msgList.length;
        container.innerHTML = '';
        
        msgList.forEach(msg => {
            const div = document.createElement('div');
            const senderRaw = (msg.de || 'sistema').toLowerCase();
            const isUser = senderRaw === 'usuario';
            const theme = agentColors[senderRaw] || { border: 'border-outline-variant/30', bg: 'bg-surface-container-high', text: 'text-secondary', name: msg.de || 'Agente' };
            
            let msgText = '';
            if (msg.contenido && typeof msg.contenido === 'object') {
                msgText = msg.contenido.texto || JSON.stringify(msg.contenido);
            } else {
                msgText = String(msg.contenido || '');
            }

            let timeStr = '';
            if (msg.timestamp) {
                try {
                    const d = new Date(msg.timestamp);
                    timeStr = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                } catch(e) {}
            }

            div.className = isUser 
                ? 'self-end bg-primary/20 text-on-surface p-3 rounded-2xl rounded-tr-none border border-primary/40 max-w-[88%] shadow-[0_0_12px_rgba(255,45,120,0.2)] text-xs transition-all'
                : `self-start ${theme.bg} text-on-surface p-3 rounded-2xl rounded-tl-none border ${theme.border} max-w-[88%] shadow-md text-xs transition-all`;

            div.innerHTML = `
                <div class="flex justify-between items-center gap-3 mb-1">
                    <span class="${theme.text} font-bold tracking-wider uppercase text-[10px]">${theme.name}</span>
                    ${timeStr ? `<span class="text-[9px] text-on-surface-variant/50">${timeStr}</span>` : ''}
                </div>
                <div class="leading-relaxed whitespace-pre-wrap select-text">${escapeHtml(msgText)}</div>
            `;
            container.appendChild(div);
        });

        if (msgList.length > 0) {
            const lastMsg = msgList[msgList.length - 1];
            if (lastMsg && lastMsg.de && lastMsg.de.toLowerCase() !== 'usuario') {
                if (typeof setSpeakingAgent === 'function') {
                    setSpeakingAgent(lastMsg.de);
                }
            }
        }

        setTimeout(() => {
            container.scrollTop = container.scrollHeight;
        }, 50);
    }
}

function updateLogs(logs) {
    const container = document.getElementById('logs-container');
    if (!container || !logs) return;

    let logItems = [];
    if (Array.isArray(logs)) {
        logItems = logs;
    } else if (typeof logs === 'string') {
        logItems = logs.split('\n').filter(l => l.trim()).slice(-40).map(l => ({ origen: 'sistema', texto: l }));
    }

    if (logItems.length === 0) return;

    const lastItem = logItems[logItems.length - 1];
    const currentSig = `${logItems.length}_${lastItem.origen || ''}_${lastItem.texto || ''}`;
    if (container.dataset.lastSig !== currentSig) {
        container.dataset.lastSig = currentSig;
        container.innerHTML = '';

        logItems.forEach(item => {
            const div = document.createElement('div');
            div.className = 'flex gap-2 text-[11px] leading-relaxed font-mono items-start';

            const origen = item.origen ? item.origen.toUpperCase() : 'LOG';
            const texto = item.texto || String(item);

            let tagClass = 'text-primary font-bold';
            const low = texto.toLowerCase();
            if (low.includes('error') || low.includes('fail') || low.includes('exception') || low.includes('traceback') || low.includes('crítico')) {
                tagClass = 'text-error font-bold';
            } else if (low.includes('warn')) {
                tagClass = 'text-tertiary font-bold';
            } else if (low.includes('success') || low.includes('ok') || low.includes('✓') || low.includes('activo')) {
                tagClass = 'text-secondary font-bold';
            }

            div.innerHTML = `
                <span class="text-on-surface-variant/40 shrink-0">[${escapeHtml(origen)}]</span>
                <span class="${tagClass} shrink-0">&gt;</span>
                <span class="text-on-surface-variant/90 break-all select-text">${escapeHtml(texto)}</span>
            `;
            container.appendChild(div);
        });

        container.scrollTop = container.scrollHeight;
    }
}

function updateCostos(costos) {
    const tokenEl = document.getElementById('token-count');
    const costEl = document.getElementById('cost-count');
    if (tokenEl) tokenEl.innerText = costos.tokens.toLocaleString();
    if (costEl) costEl.innerText = costos.costo.toFixed(4);
}

connect();

// Drag and Drop functionality
const modules = document.querySelectorAll('.hw-module');
const container = document.getElementById('left-sidebar');

modules.forEach((module, index) => {
    module.style.top = (index * 60) + 'px';
});

modules.forEach(module => {
    module.addEventListener('dragstart', (e) => {
        module.classList.add('dragging');
        const rect = module.getBoundingClientRect();
        e.dataTransfer.setData('text/plain', JSON.stringify({
            offsetY: e.clientY - rect.top
        }));
        e.dataTransfer.effectAllowed = 'move';
    });
    module.addEventListener('dragend', () => {
        module.classList.remove('dragging');
    });
});

if (container) {
    container.addEventListener('dragover', e => {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
    });

    container.addEventListener('drop', e => {
        e.preventDefault();
        const draggable = document.querySelector('.dragging');
        if (!draggable) return;
        
        const data = e.dataTransfer.getData('text/plain');
        if (!data) return;
        const offsetData = JSON.parse(data);
        
        const containerRect = container.getBoundingClientRect();
        let newY = e.clientY - containerRect.top - offsetData.offsetY;
        
        if (newY < 0) newY = 0;
        if (newY > containerRect.height - draggable.offsetHeight) newY = containerRect.height - draggable.offsetHeight;
        
        draggable.style.top = newY + 'px';
    });
}

function closeAllModals() {
    document.getElementById('modal-overlay')?.classList.add('hidden');
    document.querySelectorAll('.custom-modal').forEach(m => m.classList.add('hidden'));
}
function openModal(modalId) {
    closeAllModals();
    if (modalId === 'inicio') return;
    const overlay = document.getElementById('modal-overlay');
    const modal = document.getElementById('modal-' + modalId);
    if (overlay && modal) {
        overlay.classList.remove('hidden');
        modal.classList.remove('hidden');
    }
    if (modalId === 'configuraciones') {
        fetchEnvConfig();
    }
}

async function saveApiConfig() {
    const provider = document.getElementById('api-provider').value;
    const apiKey = document.getElementById('api-key').value;
    const model = document.getElementById('api-model').value;
    if (!apiKey && provider !== 'ollama') {
        alert('Por favor, ingresa una API Key válida.');
        return;
    }
    try {
        const res = await fetch('/api/config/env', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ provider, api_key: apiKey, model })
        });
        const data = await res.json();
        alert(data.message);
    } catch(e) {
        alert('Error al guardar: ' + e);
    }
}

async function restartContainer() {
    if(confirm('¿Estás seguro de que deseas reiniciar el contenedor de la tripulación?')) {
        try {
            const res = await fetch('/api/system/restart', { method: 'POST' });
            const data = await res.json();
            alert(data.message);
        } catch(e) {
            alert('Error al reiniciar: ' + e);
        }
    }
}

function ensureLuminance(hex) {
    let r = parseInt(hex.slice(1, 3), 16);
    let g = parseInt(hex.slice(3, 5), 16);
    let b = parseInt(hex.slice(5, 7), 16);
    
    let luma = (r * 299 + g * 587 + b * 114) / 1000;
    const minLuma = 140; // Umbral de brillo necesario para fondos oscuros
    
    if (luma < minLuma) {
        let t = (minLuma - luma) / (255 - luma);
        r = Math.round(r + (255 - r) * t);
        g = Math.round(g + (255 - g) * t);
        b = Math.round(b + (255 - b) * t);
        
        const toHex = (c) => {
            const h = c.toString(16);
            return h.length === 1 ? '0' + h : h;
        };
        return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
    }
    return hex;
}

function updateThemeColor(color) {
    const safeColor = ensureLuminance(color);
    document.documentElement.style.setProperty('--accent-blue', safeColor);
    
    // Actualizar el selector para que el usuario vea el ajuste
    const picker = document.getElementById('color-accent');
    if (picker && safeColor !== color) {
        picker.value = safeColor;
    }
}

function updateBackground(type) {
    const bg = document.getElementById('virtual-bg');
    if (!bg) return;
    
    // Aplicar heurística de minimalismo y reducción de ruido visual
    bg.style.backgroundSize = 'auto';
    bg.style.backgroundColor = 'transparent';
    
    if (type === 'gradient') {
        // Sutil gradiente corporativo para romper la planitud sin ser invasivo
        bg.style.background = 'radial-gradient(circle at top left, rgba(255,255,255,0.03) 0%, transparent 50%)';
        bg.style.opacity = '1';
    } else if (type === 'grid') {
        // Rejilla de alta precisión (sutil)
        bg.style.background = 'linear-gradient(rgba(255, 255, 255, 0.02) 1px, transparent 1px), linear-gradient(90deg, rgba(255, 255, 255, 0.02) 1px, transparent 1px)';
        bg.style.backgroundSize = '40px 40px';
        bg.style.opacity = '1';
    } else if (type === 'particles') {
        // Textura suave en lugar de partículas caóticas
        bg.style.background = 'url("https://www.transparenttextures.com/patterns/cubes.png")';
        bg.style.opacity = '0.05';
    }
}

let envConfig = { keys: {}, default_model: '' };

async function fetchEnvConfig() {
    try {
        const res = await fetch('/api/config/env');
        envConfig = await res.json();
        document.getElementById('api-model').value = envConfig.default_model || '';
        renderSavedApis();
    } catch(e) { console.error('Error fetching env:', e); }
}

function loadProviderKey() {
    // No auto-fill anymore, let the user type new keys cleanly
    document.getElementById('api-key').value = '';
}

function renderSavedApis() {
    const list = document.getElementById('saved-apis-list');
    if (!list) return;
    list.innerHTML = '';
    
    const providers = Object.keys(envConfig.keys);
    if (providers.length === 0) {
        list.innerHTML = '<span style="color: #666;">No hay llaves guardadas.</span>';
        return;
    }
    
    providers.forEach(prov => {
        const div = document.createElement('div');
        div.style.display = 'flex';
        div.style.justifyContent = 'space-between';
        div.style.alignItems = 'center';
        div.style.background = 'rgba(0, 0, 0, 0.2)';
        div.style.padding = '8px 12px';
        div.style.borderRadius = '6px';
        div.style.border = '1px solid rgba(255, 255, 255, 0.1)';
        
        const provName = prov.charAt(0).toUpperCase() + prov.slice(1);
        div.innerHTML = `
            <div>
                <strong style="color: var(--accent-blue);">${provName}</strong>
                <span style="margin-left: 10px; color: #888; font-family: monospace;">********</span>
            </div>
            <button onclick="deleteApiKey('${prov}')" style="background: none; border: none; color: #ff4757; cursor: pointer;" title="Eliminar llave">
                <i class="fa-solid fa-trash"></i>
            </button>
        `;
        list.appendChild(div);
    });
}

async function deleteApiKey(provider) {
    if (confirm(`¿Eliminar la llave de ${provider.toUpperCase()}?`)) {
        try {
            const res = await fetch(`/api/config/env/${provider}`, { method: 'DELETE' });
            const data = await res.json();
            alert(data.message);
            // Refresh list
            fetchEnvConfig();
        } catch(e) {
            alert('Error: ' + e);
        }
    }
}

function saveVisualStyles() {
    const color = document.getElementById('color-accent').value;
    const bg = document.getElementById('bg-selector').value;
    localStorage.setItem('themeColor', color);
    localStorage.setItem('themeBg', bg);
    alert('¡Estilos visuales guardados correctamente!');
}

function loadVisualStyles() {
    const savedColor = localStorage.getItem('themeColor');
    const savedBg = localStorage.getItem('themeBg');
    if (savedColor) {
        const picker = document.getElementById('color-accent');
        if(picker) picker.value = savedColor;
        updateThemeColor(savedColor);
    }
    if (savedBg) {
        const bgSelect = document.getElementById('bg-selector');
        if(bgSelect) bgSelect.value = savedBg;
        updateBackground(savedBg);
    }
}

// Load styles when script runs
loadVisualStyles();



// Modos de Operación del Chat (Auto, Entrevista, Plan)
let currentChatMode = localStorage.getItem('selectedChatMode') || 'auto';

const chatModeConfigs = {
    'auto': {
        label: 'Modo Auto',
        borderClass: 'border-secondary/50',
        textClass: 'text-secondary',
        dotClass: 'bg-secondary shadow-[0_0_6px_#00ffcc]',
        placeholder: 'Escribe una orden a la tripulación...'
    },
    'entrevista': {
        label: 'Modo Entrevista',
        borderClass: 'border-purple-400/50',
        textClass: 'text-purple-400',
        dotClass: 'bg-purple-400 shadow-[0_0_6px_#c084fc]',
        placeholder: 'Plantea una idea o responde al entrevistador...'
    },
    'plan': {
        label: 'Modo Plan',
        borderClass: 'border-amber-400/50',
        textClass: 'text-amber-400',
        dotClass: 'bg-amber-400 shadow-[0_0_6px_#fbbf24]',
        placeholder: 'Indica el proyecto o problema a planificar...'
    }
};

function applyChatModeUI(mode) {
    const cfg = chatModeConfigs[mode] || chatModeConfigs['auto'];
    currentChatMode = mode;
    localStorage.setItem('selectedChatMode', mode);

    const btn = document.getElementById('chat-mode-btn');
    const label = document.getElementById('chat-mode-label');
    const dot = document.getElementById('chat-mode-dot');
    const input = document.getElementById('chat-input');

    if (label) label.innerText = cfg.label;
    if (dot) dot.className = `w-2 h-2 rounded-full ${cfg.dotClass} animate-pulse`;
    if (btn) {
        btn.title = `${cfg.label} (Click para cambiar modo)`;
        btn.classList.remove('border-secondary/50', 'border-purple-400/50', 'border-amber-400/50', 'text-secondary', 'text-purple-400', 'text-amber-400');
        btn.classList.add(cfg.borderClass, cfg.textClass);
    }
    if (input) input.placeholder = cfg.placeholder;
}

function toggleChatModeMenu(e) {
    if (e) e.stopPropagation();
    const menu = document.getElementById('chat-mode-menu');
    if (menu) menu.classList.toggle('hidden');
}
window.toggleChatModeMenu = toggleChatModeMenu;

async function selectChatMode(mode) {
    applyChatModeUI(mode);
    const menu = document.getElementById('chat-mode-menu');
    if (menu) menu.classList.add('hidden');
    try {
        await fetch('/api/modo', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ modo: mode })
        });
    } catch(err) {
        console.error('Error guardando modo:', err);
    }
}
window.selectChatMode = selectChatMode;

document.addEventListener('click', (e) => {
    const menu = document.getElementById('chat-mode-menu');
    const btn = document.getElementById('chat-mode-btn');
    if (menu && !menu.classList.contains('hidden') && btn && !btn.contains(e.target) && !menu.contains(e.target)) {
        menu.classList.add('hidden');
    }
});

// Inicializar modo en cuanto cargue el script
applyChatModeUI(currentChatMode);

// Logica del Chat
async function sendChatMessage() {
    const input = document.getElementById('chat-input');
    if (!input || !input.value.trim()) return;
    const text = input.value.trim();
    input.value = '';

    // Render immediately in chat (Optimistic UI)
    const container = document.getElementById('chat-messages');
    if (container) {
        const div = document.createElement('div');
        div.className = 'self-end bg-primary/20 text-on-surface p-3 rounded-2xl rounded-tr-none border border-primary/40 max-w-[88%] shadow-[0_0_12px_rgba(255,45,120,0.2)] text-xs transition-all';
        const now = new Date();
        const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        div.innerHTML = `
            <div class="flex justify-between items-center gap-3 mb-1">
                <span class="text-primary font-bold tracking-wider uppercase text-[10px]">Capitán (Tú)</span>
                <span class="text-[9px] text-on-surface-variant/50">${timeStr}</span>
            </div>
            <div class="leading-relaxed whitespace-pre-wrap select-text">${escapeHtml(text)}</div>
        `;
        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
    }

    try {
        await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ texto: text, modo: currentChatMode })
        });
    } catch(e) {
        console.error('Error enviando chat:', e);
    }
}
window.sendChatMessage = sendChatMessage;

function initChatListeners() {
    const btn = document.getElementById('send-btn');
    const input = document.getElementById('chat-input');
    if (btn && !btn._bound) {
        btn._bound = true;
        btn.addEventListener('click', sendChatMessage);
    }
    if (input && !input._bound) {
        input._bound = true;
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendChatMessage();
            }
        });
    }
}
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initChatListeners);
} else {
    initChatListeners();
}


// Chat UI Logic
function toggleChat() {
    const sidebar = document.getElementById('chat-sidebar');
    const btn = document.getElementById('chat-toggle-btn');
    if (sidebar.style.display === 'none') {
        sidebar.style.display = 'flex';
        btn.classList.add('hidden');
    } else {
        sidebar.style.display = 'none';
        btn.classList.remove('hidden');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const chatResizer = document.getElementById('chat-resizer');
    const chatSidebar = document.getElementById('chat-sidebar');
    let isResizing = false;

    if (chatResizer && chatSidebar) {
        chatResizer.addEventListener('mousedown', (e) => {
            isResizing = true;
            document.body.style.cursor = 'col-resize';
            e.preventDefault();
        });
        document.addEventListener('mousemove', (e) => {
            if (!isResizing) return;
            const rect = chatSidebar.getBoundingClientRect();
            const newWidth = rect.right - e.clientX;
            if (newWidth >= 300 && newWidth <= 800) {
                chatSidebar.style.width = newWidth + 'px';
            }
        });
        document.addEventListener('mouseup', () => {
            if (isResizing) {
                isResizing = false;
                document.body.style.cursor = 'default';
            }
        });
    }
});



function updateEstado(est) {
    const dot = document.getElementById('estado-dot');
    const text = document.getElementById('estado-text');
    
    // Helper function to set an agent's badge visually
    const setAgentBadge = (agentId, state) => {
        const badge = document.getElementById(`estado-${agentId}`);
        if (!badge) return;
        const icon = badge.querySelector('.icon');
        const spanText = badge.querySelector('.text');
        if (!icon || !spanText) return;
        
        // Strip old border/text colors safely keeping layout classes
        badge.className = badge.className.replace(/border-(primary|secondary|tertiary|purple|outline-variant)/g, '');
        badge.className = badge.className.replace(/text-(primary|secondary|tertiary|purple|on-surface-variant)/g, '');
        badge.className = badge.className.replace(/shadow-\[.*?\]/g, '');
        badge.className = badge.className.replace(/opacity-\\d+/g, '');
        
        if (state === 'activo') {
            let colorClass = 'primary'; // Luffy/Nami
            if (agentId === 'zoro') colorClass = 'secondary';
            else if (agentId === 'sanji') colorClass = 'tertiary';
            else if (agentId === 'robin') colorClass = 'purple';
            
            badge.classList.add(`border-${colorClass}`, `text-${colorClass}`);
            badge.style.boxShadow = `0 0 8px var(--tw-color-${colorClass}, rgba(255,255,255,0.2))`; // approximation
            icon.innerText = 'check_circle';
            spanText.innerText = 'ACTIVO';
            badge.classList.remove('opacity-50');
        } else if (state === 'espera') {
            // Yellow/warning style or just secondary
            badge.classList.add('border-tertiary', 'text-tertiary');
            badge.style.boxShadow = 'none';
            icon.innerText = 'hourglass_empty';
            spanText.innerText = 'EN ESPERA';
            badge.classList.remove('opacity-50');
        } else {
            // OFF state
            badge.classList.add('border-outline-variant', 'text-on-surface-variant', 'opacity-50');
            badge.style.boxShadow = 'none';
            icon.innerText = 'power_off';
            spanText.innerText = 'OFF';
        }
    };

    if (!dot || !text || !est) return;
    if (est.estado && est.estado.toLowerCase() === 'desconectada') {
        dot.className = 'w-2 h-2 rounded-full bg-error shadow-[0_0_8px_rgba(255,84,73,0.6)]';
        text.className = 'text-[10px] font-label text-error uppercase tracking-widest';
        text.innerText = 'TRIPULACIÓN DESCONECTADA';
        
        // All OFF
        ['luffy', 'zoro', 'sanji', 'nami', 'robin'].forEach(id => setAgentBadge(id, 'off'));
    } else {
        dot.className = 'w-2 h-2 rounded-full bg-secondary shadow-[0_0_8px_rgba(0,255,204,0.6)] animate-pulse';
        text.className = 'text-[10px] font-label text-secondary uppercase tracking-widest';
        text.innerText = 'TRIPULACIÓN ACTIVA';
        
        // Check agents inside est
        const agentes = est.agentes || {};
        ['luffy', 'zoro', 'sanji', 'nami', 'robin'].forEach(id => {
            // Default to 'espera' except Luffy who defaults to 'activo'
            let defaultState = (id === 'luffy') ? 'activo' : 'espera';
            let state = agentes[id] ? agentes[id].toLowerCase() : defaultState;
            setAgentBadge(id, state);
        });
    }
}


// --- MODEL SYNC --- 
async function updateAgentModels() {
    try {
        const response = await fetch('/api/config/env');
        if (!response.ok) return;
        const data = await response.json();
        const modelName = data.default_model;
        if (!modelName) return;
        
        document.querySelectorAll('.agent-model-display').forEach(el => {
            if (el.getAttribute('data-leader') === 'true') {
                el.textContent = modelName + ' (Líder)';
            } else {
                el.textContent = modelName;
            }
        });
    } catch (e) {
        console.error('Error syncing models:', e);
    }
}

// Fetch initial state
document.addEventListener('DOMContentLoaded', () => {
    updateAgentModels();
    // Poll every 5 seconds for model changes in .env
    setInterval(updateAgentModels, 5000);
});
 


// --- KANBAN & TAREAS LOGIC ---
let currentFiltroProgramadas = 'diarias';
let cacheProgramadas = {};

function renderTareaBlock(tarea) {
    // tarea: {titulo, descripcion, responsable, estado}
    const colores = {
        luffy: 'var(--accent-red, #ff4444)',
        zoro: 'var(--accent-green, #00ffcc)',
        sanji: 'var(--accent-yellow, #ffe04a)',
        nami: 'var(--accent-pink, #ff2d78)',
        robin: 'var(--accent-purple, #a855f7)',
        sistema: '#ffffff'
    };
    
    const name = tarea.responsable ? tarea.responsable.toLowerCase() : 'sistema';
    const color = colores[name] || colores['sistema'];
    const nameFormatted = name.charAt(0).toUpperCase() + name.slice(1);
    
    let estadoBadge = '';
    const estado = tarea.estado ? tarea.estado.toLowerCase() : '';
    if (estado === 'ejecutando' || estado === 'en proceso') {
        estadoBadge = `<span class="text-[10px] font-bold uppercase px-2 py-0.5 rounded bg-secondary/20 text-secondary border border-secondary/50">Ejecutando</span>`;
    } else if (estado === 'completada' || estado === 'archivado') {
        estadoBadge = `<span class="text-[10px] font-bold uppercase px-2 py-0.5 rounded bg-primary/20 text-primary border border-primary/50">Completado</span>`;
    } else {
        estadoBadge = `<span class="text-[10px] font-bold uppercase px-2 py-0.5 rounded bg-outline-variant/30 text-on-surface-variant border border-outline-variant/50">${tarea.estado || 'Pendiente'}</span>`;
    }

    return `
    <div class="bg-surface border border-outline-variant/50 rounded-lg p-4 hover:border-[${color}]/50 transition-colors group flex flex-col">
        <div class="flex justify-between items-start mb-2">
            <h4 class="text-on-surface font-bold text-sm group-hover:text-[${color}] transition-colors">${tarea.titulo || 'Sin título'}</h4>
            ${estadoBadge}
        </div>
        <p class="text-xs text-on-surface-variant mb-3 line-clamp-2">${tarea.descripcion || tarea.tarea || ''}</p>
        <div class="mt-auto flex items-center gap-2">
            <div class="w-2 h-2 rounded-full" style="background-color: ${color}; box-shadow: 0 0 6px ${color};"></div>
            <span class="text-xs font-bold uppercase tracking-wider" style="color: ${color};">${nameFormatted}</span>
        </div>
    </div>`;
}

function updatePizarra(pizarraData) {
    const list = document.getElementById('pizarra-list');
    if (!list) return;
    if (!pizarraData || pizarraData.length === 0) {
        list.innerHTML = '<p class="text-on-surface-variant text-sm italic">No hay tareas activas en la pizarra...</p>';
        return;
    }
    
    let html = '';
    pizarraData.forEach(t => {
        html += renderTareaBlock(t);
    });
    list.innerHTML = html;
}

function updateArchivados(archivadosData) {
    const list = document.getElementById('archivados-list');
    if (!list) return;
    if (!archivadosData || archivadosData.length === 0) {
        list.innerHTML = '<p class="text-on-surface-variant text-sm italic">No hay tickets archivados todavía...</p>';
        return;
    }
    let html = '';
    archivadosData.forEach(t => {
        html += renderTareaBlock(t);
    });
    list.innerHTML = html;
}

function filterProgramadas(tipo) {
    currentFiltroProgramadas = tipo;
    const btns = ['diarias', 'semanales', 'mensuales'];
    btns.forEach(b => {
        const el = document.getElementById('btn-' + b);
        if (b === tipo) {
            el.className = 'flex-1 py-1.5 text-xs font-bold uppercase rounded text-secondary bg-secondary/10 transition-colors';
        } else {
            el.className = 'flex-1 py-1.5 text-xs font-bold uppercase rounded text-on-surface-variant hover:text-on-surface transition-colors';
        }
    });
    renderProgramadas();
}

function renderProgramadas() {
    const list = document.getElementById('programadas-list');
    if (!list) return;
    const data = cacheProgramadas[currentFiltroProgramadas];
    if (!data || data.length === 0) {
        list.innerHTML = '<p class="text-on-surface-variant text-sm italic">No hay tareas programadas para esta categoría.</p>';
        return;
    }
    let html = '';
    data.forEach(t => {
        html += renderTareaBlock(t);
    });
    list.innerHTML = html;
}

// Update WebSocket hook in connect function
// It will now also look for data.tickets_archivados and data.tareas_programadas

// ==========================================
// VOICE VISUALIZER & VOICE-TO-VOICE SYSTEM
// ==========================================

let voiceAudioContext = null;
let voiceAnalyser = null;
let voiceMicrophoneStream = null;
let voiceSessionActive = false;
let speechRecognizer = null;
let currentSpeakingAgent = null;
let speakingTimeout = null;

const agentThemeColors = {
    'luffy': { hex: '#ff2d78', rgb: '255, 45, 120', name: 'Luffy' },
    'zoro': { hex: '#00ffcc', rgb: '0, 255, 204', name: 'Zoro' },
    'sanji': { hex: '#ffaa00', rgb: '255, 170, 0', name: 'Sanji' },
    'robin': { hex: '#c084fc', rgb: '192, 132, 252', name: 'Robin' },
    'nami': { hex: '#fbbf24', rgb: '251, 191, 36', name: 'Nami' },
    'usuario': { hex: '#00ffcc', rgb: '0, 255, 204', name: 'Tú' },
    'sistema': { hex: '#ff2d78', rgb: '255, 45, 120', name: 'Tripulación' }
};

function initVoiceVisualizer() {
    const canvas = document.getElementById('voice-wave-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    function resizeCanvas() {
        if (!canvas) return;
        canvas.width = canvas.offsetWidth;
        canvas.height = canvas.offsetHeight;
    }
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    let phase = 0;

    function drawWave() {
        requestAnimationFrame(drawWave);
        if (!canvas || canvas.width === 0 || canvas.height === 0) return;

        const w = canvas.width;
        const h = canvas.height;
        const midY = h / 2;

        ctx.clearRect(0, 0, w, h);

        // Determine active color theme
        let activeTheme = agentThemeColors['luffy'];
        if (currentSpeakingAgent && agentThemeColors[currentSpeakingAgent.toLowerCase()]) {
            activeTheme = agentThemeColors[currentSpeakingAgent.toLowerCase()];
        } else if (voiceSessionActive) {
            activeTheme = agentThemeColors['usuario'];
        }

        // Get audio data if mic is active
        let freqSum = 0;
        let dataArray = null;
        if (voiceAnalyser && voiceSessionActive) {
            const bufferLength = voiceAnalyser.frequencyBinCount;
            dataArray = new Uint8Array(bufferLength);
            voiceAnalyser.getByteFrequencyData(dataArray);
            for (let i = 0; i < bufferLength; i++) {
                freqSum += dataArray[i];
            }
            freqSum = freqSum / bufferLength; // average level (0-255)
        }

        // Base amplitude & energy
        let energy = 1.0;
        if (voiceSessionActive && freqSum > 5) {
            energy = 1.0 + (freqSum / 16);
        } else if (currentSpeakingAgent) {
            energy = 2.5 + Math.sin(phase * 3) * 1.2;
        }

        phase += 0.04;

        // Draw multiple harmonic wave layers for a futuristic holographic effect
        const waves = [
            { count: 2, amp: 22 * energy, speed: 1.0, alpha: 0.85, width: 2.5 },
            { count: 3, amp: 16 * energy, speed: -1.3, alpha: 0.55, width: 2.0 },
            { count: 1.5, amp: 30 * energy, speed: 0.7, alpha: 0.35, width: 1.5 },
            { count: 4, amp: 10 * energy, speed: -1.8, alpha: 0.25, width: 1.0 }
        ];

        waves.forEach((wave, idx) => {
            ctx.beginPath();
            ctx.lineWidth = wave.width;
            ctx.strokeStyle = `rgba(${activeTheme.rgb}, ${wave.alpha})`;
            ctx.shadowBlur = 10;
            ctx.shadowColor = activeTheme.hex;

            for (let x = 0; x <= w; x += 3) {
                // Windowing function to taper edges at boundaries
                const envelope = Math.sin((x / w) * Math.PI);
                
                // Add mic data if active
                let micOffset = 0;
                if (dataArray && dataArray.length > 0) {
                    const dataIndex = Math.floor((x / w) * (dataArray.length / 2));
                    micOffset = (dataArray[dataIndex] / 255 - 0.5) * 45 * envelope;
                }

                const y = midY + Math.sin((x * 0.015 * wave.count) + (phase * wave.speed) + idx) * (wave.amp * envelope) + micOffset;
                if (x === 0) {
                    ctx.moveTo(x, y);
                } else {
                    ctx.lineTo(x, y);
                }
            }
            ctx.stroke();
            ctx.shadowBlur = 0;
        });

        // Center horizon line with subtle glow
        ctx.beginPath();
        ctx.lineWidth = 1;
        ctx.strokeStyle = `rgba(255, 255, 255, 0.08)`;
        ctx.moveTo(0, midY);
        ctx.lineTo(w, midY);
        ctx.stroke();
    }

    drawWave();
}

// Function to trigger voice visualization when an agent speaks
function setSpeakingAgent(agentName, durationMs = 4500) {
    currentSpeakingAgent = agentName ? agentName.toLowerCase() : null;
    const titleEl = document.getElementById('voice-agent-title');
    const badgeEl = document.getElementById('voice-speaker-badge');
    const descEl = document.getElementById('voice-agent-desc');
    const glowEl = document.getElementById('voice-glow');
    const iconEl = document.getElementById('voice-agent-icon');

    const theme = agentThemeColors[currentSpeakingAgent] || agentThemeColors['sistema'];

    if (currentSpeakingAgent) {
        if (titleEl) titleEl.innerText = `Transmisión de Voz: ${theme.name}`;
        if (badgeEl) {
            badgeEl.innerText = `${theme.name} Hablando`;
            badgeEl.className = `py-0.5 px-2.5 rounded-full text-[10px] font-bold tracking-wider uppercase border animate-pulse`;
            badgeEl.style.color = theme.hex;
            badgeEl.style.borderColor = theme.hex;
            badgeEl.style.backgroundColor = `rgba(${theme.rgb}, 0.15)`;
            badgeEl.style.boxShadow = `0 0 10px rgba(${theme.rgb}, 0.4)`;
        }
        if (descEl) descEl.innerText = `Ondas moduladas por la voz de ${theme.name}`;
        if (iconEl) iconEl.style.color = theme.hex;
        if (glowEl) {
            glowEl.style.background = `radial-gradient(ellipse at center, rgba(${theme.rgb}, 0.4) 0%, transparent 70%)`;
            glowEl.style.opacity = '0.5';
        }

        if (speakingTimeout) clearTimeout(speakingTimeout);
        speakingTimeout = setTimeout(() => {
            currentSpeakingAgent = null;
            if (!voiceSessionActive) {
                if (titleEl) titleEl.innerText = 'Canal de Voz con Luffy';
                if (badgeEl) {
                    badgeEl.innerText = 'En Reposo';
                    badgeEl.className = 'py-0.5 px-2.5 rounded-full text-[10px] font-bold tracking-wider uppercase bg-surface-container-high border border-outline-variant text-on-surface-variant';
                    badgeEl.style = '';
                }
                if (descEl) descEl.innerText = 'Enlace de comunicación bidireccional directa y continua con Luffy';
                if (iconEl) iconEl.style.color = '';
                if (glowEl) {
                    glowEl.style.background = 'radial-gradient(ellipse at center, rgba(255,45,120,0.3) 0%, transparent 70%)';
                    glowEl.style.opacity = '0.25';
                }
            }
        }, durationMs);
    }
}
window.setSpeakingAgent = setSpeakingAgent;

// Toggle Voice Session (Voz a Voz)
async function toggleVoiceSession() {
    const btn = document.getElementById('voice-toggle-btn');
    const btnText = document.getElementById('voice-btn-text');
    const btnIcon = document.getElementById('voice-btn-icon');
    const btnDot = document.getElementById('voice-btn-dot');
    const feedback = document.getElementById('voice-feedback');
    const badge = document.getElementById('voice-speaker-badge');

    if (!voiceSessionActive) {
        // INICIAR COMUNICACIÓN
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            voiceMicrophoneStream = stream;

            const AudioContextClass = window.AudioContext || window.webkitAudioContext;
            voiceAudioContext = new AudioContextClass();
            const source = voiceAudioContext.createMediaStreamSource(stream);
            voiceAnalyser = voiceAudioContext.createAnalyser();
            voiceAnalyser.fftSize = 256;
            source.connect(voiceAnalyser);

            voiceSessionActive = true;

            // Update Button & UI to Active State
            if (btn) {
                btn.className = 'group relative flex items-center gap-3 py-3.5 px-8 rounded-2xl bg-error/20 border border-error hover:bg-error/30 shadow-[0_0_30px_rgba(255,68,68,0.45)] transition-all duration-300 cursor-pointer text-sm font-bold text-error tracking-wider uppercase select-none';
            }
            if (btnDot) btnDot.className = 'w-3 h-3 rounded-full bg-error animate-pulse shadow-[0_0_10px_#ff4444]';
            if (btnIcon) {
                btnIcon.innerText = 'mic';
                btnIcon.className = 'material-symbols-outlined text-[22px] text-error animate-pulse';
            }
            if (btnText) btnText.innerText = 'Finalizar Comunicación Voz a Voz';
            if (badge) {
                badge.innerText = 'Escuchando Voz';
                badge.className = 'py-0.5 px-2.5 rounded-full text-[10px] font-bold tracking-wider uppercase bg-secondary/20 border border-secondary text-secondary animate-pulse shadow-[0_0_10px_rgba(0,255,204,0.4)]';
                badge.style = '';
            }
            if (feedback) {
                feedback.innerText = 'Micrófono activo • Háblale a la tripulación con confianza.';
                feedback.className = 'absolute bottom-4 inset-x-6 text-center text-xs font-mono text-secondary font-bold pointer-events-none transition-all';
            }

            // Web Speech Recognition for hands-free voice transcription
            const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
            if (SpeechRec) {
                speechRecognizer = new SpeechRec();
                speechRecognizer.continuous = true;
                speechRecognizer.interimResults = true;
                speechRecognizer.lang = 'es-ES';

                speechRecognizer.onresult = (event) => {
                    let interimTranscript = '';
                    let finalTranscript = '';
                    for (let i = event.resultIndex; i < event.results.length; ++i) {
                        if (event.results[i].isFinal) {
                            finalTranscript += event.results[i][0].transcript;
                        } else {
                            interimTranscript += event.results[i][0].transcript;
                        }
                    }
                    if (interimTranscript && feedback) {
                        feedback.innerText = `"${interimTranscript}"`;
                    }
                    if (finalTranscript) {
                        if (feedback) feedback.innerText = `Transmitiendo: "${finalTranscript}"`;
                        const chatIn = document.getElementById('chat-input');
                        if (chatIn) chatIn.value = finalTranscript;
                        if (typeof sendChatMessage === 'function') {
                            sendChatMessage();
                        }
                    }
                };

                speechRecognizer.onerror = (e) => {
                    console.warn('SpeechRecognition error:', e);
                };

                speechRecognizer.start();
            }

        } catch (err) {
            console.error('Error accediendo al micrófono:', err);
            alert('No se pudo acceder al micrófono: ' + (err.message || err));
        }
    } else {
        // DETENER COMUNICACIÓN
        if (voiceMicrophoneStream) {
            voiceMicrophoneStream.getTracks().forEach(t => t.stop());
            voiceMicrophoneStream = null;
        }
        if (voiceAudioContext) {
            voiceAudioContext.close().catch(() => {});
            voiceAudioContext = null;
            voiceAnalyser = null;
        }
        if (speechRecognizer) {
            try { speechRecognizer.stop(); } catch(e) {}
            speechRecognizer = null;
        }
        voiceSessionActive = false;

        // Restore Button & UI to Idle
        if (btn) {
            btn.className = 'group relative flex items-center gap-3 py-3.5 px-8 rounded-2xl bg-gradient-to-r from-primary/20 via-surface-container-highest to-secondary/20 hover:from-primary/30 hover:to-secondary/30 border border-primary/50 hover:border-secondary hover:shadow-[0_0_30px_rgba(0,255,204,0.3)] transition-all duration-300 cursor-pointer text-sm font-bold text-on-surface tracking-wider uppercase select-none';
        }
        if (btnDot) btnDot.className = 'w-3 h-3 rounded-full bg-primary animate-pulse shadow-[0_0_10px_#ff2d78]';
        if (btnIcon) {
            btnIcon.innerText = 'mic';
            btnIcon.className = 'material-symbols-outlined text-[22px] text-primary group-hover:text-secondary group-hover:scale-110 transition-all';
        }
        if (btnText) btnText.innerText = 'Iniciar Comunicación Voz a Voz';
        if (badge) {
            badge.innerText = 'En Reposo';
            badge.className = 'py-0.5 px-2.5 rounded-full text-[10px] font-bold tracking-wider uppercase bg-surface-container-high border border-outline-variant text-on-surface-variant';
            badge.style = '';
        }
        if (feedback) {
            feedback.innerText = 'Canal de voz exclusivo con Luffy en espera. Pulsa el botón inferior para comenzar a hablar.';
            feedback.className = 'absolute bottom-4 inset-x-6 text-center text-xs font-mono text-on-surface-variant/70 italic pointer-events-none transition-all';
        }
    }
}
window.toggleVoiceSession = toggleVoiceSession;

// Initialize visualizer on DOM ready or immediate if ready
if (document.readyState === 'complete' || document.readyState === 'interactive') {
    initVoiceVisualizer();
} else {
    document.addEventListener('DOMContentLoaded', initVoiceVisualizer);
}

