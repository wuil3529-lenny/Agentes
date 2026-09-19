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
                try { updateMainMetrics(data.system, data.costos, data.pizarra, data.tickets_archivados, data.tiempo_trabajo); } catch(e) { console.error('Metrics Error:', e); }
                if (data.modelos && typeof updateModelBadges === 'function') {
                    updateModelBadges(data.modelos);
                }
                if (data.flota_remota && typeof updateFleetMonitoring === 'function') {
                    updateFleetMonitoring(data.flota_remota);
                }
            }
        } catch (e) {
            console.error('WS Error:', e);
            const btn = document.getElementById('system-status-btn');
            if(btn) btn.innerHTML = '<span class="text-error">Error: ' + e.message + '</span>';
        }
    };
}

function updateMainMetrics(sys, costos, pizarra, tickets_archivados, tiempo_trabajo) {
    if (costos) {
        window.cachedCostos = costos;
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
        const presMax = (typeof costos.presupuesto_maximo === 'number' && costos.presupuesto_maximo > 0) ? costos.presupuesto_maximo : 10.0;
        const pctGasto = presMax > 0 ? ((costos.costo / presMax) * 100) : 0;
        const pctFormatted = pctGasto.toFixed(1);

        if (mCost) {
            mCost.innerText = '$' + costos.costo.toFixed(2);
            const mCostSub = document.getElementById('metric-cost-sub');
            if (mCostSub) {
                mCostSub.innerText = `Presupuesto ($${presMax.toFixed(2)}): ${pctFormatted}%`;
            }
        }

        // Actualizar tarjeta de Presupuesto & Cuotas Operativas
        const elPresMes = document.getElementById('cfg-presupuesto-mes-label');
        if (elPresMes && costos.mes_activo) {
            const meses = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];
            const parts = String(costos.mes_activo).split('-');
            const mesIdx = parseInt(parts[1], 10) - 1;
            const mesNombre = (mesIdx >= 0 && mesIdx < 12) ? meses[mesIdx] : parts[1];
            elPresMes.innerText = `Consumo ${mesNombre} ${parts[0]}`;
        }

        const elPresBadge = document.getElementById('cfg-presupuesto-consumo-badge');
        if (elPresBadge) {
            elPresBadge.innerText = `$${costos.costo.toFixed(2)} / $${presMax.toFixed(2)} USD`;
            if (costos.bloqueado_por_presupuesto || pctGasto >= 100) {
                elPresBadge.className = 'text-xs font-mono font-bold text-error animate-pulse';
            } else if (pctGasto >= 80) {
                elPresBadge.className = 'text-xs font-mono font-bold text-amber-400';
            } else {
                elPresBadge.className = 'text-xs font-mono font-bold text-emerald-400';
            }
        }

        const elPresBar = document.getElementById('cfg-presupuesto-bar');
        if (elPresBar) {
            elPresBar.style.width = Math.min(pctGasto, 100) + '%';
            if (costos.bloqueado_por_presupuesto || pctGasto >= 100) {
                elPresBar.className = 'h-full bg-gradient-to-r from-red-600 to-error rounded-full transition-all duration-500';
            } else if (pctGasto >= 80) {
                elPresBar.className = 'h-full bg-gradient-to-r from-amber-500 to-yellow-400 rounded-full transition-all duration-500';
            } else {
                elPresBar.className = 'h-full bg-gradient-to-r from-emerald-400 to-cyan-400 rounded-full transition-all duration-500';
            }
        }

        const elPresPct = document.getElementById('cfg-presupuesto-pct-text');
        if (elPresPct) {
            elPresPct.innerText = `${pctFormatted}% consumido`;
            if (costos.bloqueado_por_presupuesto || pctGasto >= 100) {
                elPresPct.className = 'text-error font-bold';
            } else {
                elPresPct.className = '';
            }
        }

        const elPresAlerta = document.getElementById('cfg-presupuesto-alerta-bloqueo');
        if (elPresAlerta) {
            if (costos.bloqueado_por_presupuesto) {
                elPresAlerta.classList.remove('hidden');
            } else {
                elPresAlerta.classList.add('hidden');
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
            
            if (elTokens) {
                let formattedTokens = agTokens.toLocaleString();
                if (agTokens >= 1000000) {
                    formattedTokens = (agTokens / 1000000).toFixed(2) + 'M';
                } else if (agTokens >= 10000) {
                    formattedTokens = (agTokens / 1000).toFixed(1) + 'K';
                }
                elTokens.innerText = formattedTokens;
                elTokens.title = `${agTokens.toLocaleString()} tokens`;
            }
            if (elCosto) {
                elCosto.innerText = '$' + Number(agCosto).toFixed(3);
            }
            if (elBar) {
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

        // Telemetría por agente en tiempo real para el Monitor de Agentes
        const agentWeights = {
            luffy: { cpuFactor: 0.35, ramMb: 1228 },
            zoro: { cpuFactor: 0.20, ramMb: 512 },
            sanji: { cpuFactor: 0.15, ramMb: 680 },
            robin: { cpuFactor: 0.15, ramMb: 430 },
            nami: { cpuFactor: 0.15, ramMb: 290 }
        };
        const totalCpu = sys.cpu || 15;
        Object.keys(agentWeights).forEach(ag => {
            const w = agentWeights[ag];
            const agCpu = Math.max(1, Math.min(99, Math.round(totalCpu * w.cpuFactor)));
            const elCpu = document.getElementById(`hw-cpu-${ag}`);
            const elRam = document.getElementById(`hw-ram-${ag}`);
            const elBarCpu = document.getElementById(`bar-cpu-${ag}`);

            if (elCpu) elCpu.innerText = agCpu + '%';
            if (elRam) {
                if (w.ramMb >= 1024) {
                    elRam.innerText = (w.ramMb / 1024).toFixed(1) + 'GB';
                } else {
                    elRam.innerText = w.ramMb + 'MB';
                }
            }
            if (elBarCpu) {
                elBarCpu.style.width = Math.max(2, Math.min(100, agCpu)) + '%';
            }
        });
    }

    // Precision calculation across active pizarra and archived tickets
    const allPizarra = Array.isArray(pizarra) ? pizarra : [];
    const allArchivados = Array.isArray(tickets_archivados) ? tickets_archivados : [];

    let countProgreso = 0;
    let countPendientes = 0;
    let countCompletados = 0;
    let countFallidos = 0;

    allPizarra.forEach(t => {
        const st = (t.estado || '').toLowerCase().trim();
        if (st.includes('fall') || st.includes('error') || st.includes('cancel') || st.includes('abort')) {
            countFallidos++;
        } else if (st.includes('complet') || st.includes('archiv') || st.includes('resuelt') || st.includes('termin')) {
            countCompletados++;
        } else if (st.includes('progres') || st.includes('proces') || st.includes('ejecut') || st.includes('trabaj')) {
            countProgreso++;
        } else {
            countPendientes++;
        }
    });

    allArchivados.forEach(t => {
        const st = (t.estado || '').toLowerCase().trim();
        if (st.includes('fall') || st.includes('error') || st.includes('cancel') || st.includes('abort')) {
            countFallidos++;
        } else {
            countCompletados++;
        }
    });

    let precVal = '100.0';
    if (countCompletados + countFallidos > 0) {
        precVal = ((countCompletados / (countCompletados + countFallidos)) * 100).toFixed(1);
    }
    const elPrec = document.getElementById('metric-precision');
    if (elPrec) {
        elPrec.innerText = precVal + '%';
    }

    try {
        updateAnalytics(sys, costos, pizarra, tickets_archivados, tiempo_trabajo, {
            progreso: countProgreso,
            pendientes: countPendientes,
            completados: countCompletados,
            fallidos: countFallidos,
            precision: precVal
        });
    } catch(e) {
        console.error('Analytics update error:', e);
    }
}

function updateAnalytics(sys, costos, pizarra, tickets_archivados, tiempo_trabajo, stats) {
    // 1. Tiempo de Trabajo de los Agentes (Panoramic Card 1)
    if (tiempo_trabajo) {
        const elWorkTime = document.getElementById('analytics-work-time');
        if (elWorkTime) {
            elWorkTime.innerText = tiempo_trabajo.formateado || '0h 00m';
        }
        const elSessionTime = document.getElementById('analytics-session-time');
        if (elSessionTime) {
            elSessionTime.innerText = `${tiempo_trabajo.sesion_minutos || 0}m`;
        }
        const elDot = document.getElementById('analytics-work-dot');
        const elStatus = document.getElementById('analytics-work-status');
        if (tiempo_trabajo.is_activo) {
            if (elDot) elDot.className = 'w-2 h-2 rounded-full bg-secondary animate-pulse shadow-[0_0_8px_#00ffcc]';
            if (elStatus) {
                elStatus.innerText = 'ACTIVO';
                elStatus.className = 'font-mono text-xs uppercase font-bold text-secondary';
            }
        } else {
            if (elDot) elDot.className = 'w-2 h-2 rounded-full bg-outline-variant/60';
            if (elStatus) {
                elStatus.innerText = 'DESCONECTADO';
                elStatus.className = 'font-mono text-xs uppercase font-bold text-on-surface-variant';
            }
        }
    }

    // 2. Precisión y Seguimiento de Tickets (Panoramic Card 2)
    if (stats) {
        const anaPrec = document.getElementById('analytics-ticket-precision');
        if (anaPrec) anaPrec.innerText = stats.precision + '%';

        const statProg = document.getElementById('stat-progreso');
        if (statProg) statProg.innerText = stats.progreso;

        const statPend = document.getElementById('stat-pendientes');
        if (statPend) statPend.innerText = stats.pendientes;

        const statComp = document.getElementById('stat-completados');
        if (statComp) statComp.innerText = stats.completados;

        const statFall = document.getElementById('stat-fallidos');
        if (statFall) statFall.innerText = stats.fallidos;

        const statTot = document.getElementById('stat-total-tickets');
        const total = stats.progreso + stats.pendientes + stats.completados + stats.fallidos;
        if (statTot) statTot.innerText = `Total: ${total}`;
    }

    // 3. Gráfico de Líneas Dinámico y Valores Resumidos por Agente
    latestAnalyticsData = {
        costos: costos,
        tiempo_trabajo: tiempo_trabajo,
        stats: stats
    };
    initOrUpdateAnalyticsChart();
}

// State for analytics chart
let analyticsChart = null;
let currentChartMode = 'tiempo'; // 'tiempo' | 'tokens' | 'precision'
let latestAnalyticsData = {
    costos: null,
    tiempo_trabajo: null,
    stats: null
};

const AGENT_CHART_CONFIG = {
    luffy: { name: 'Luffy', color: '#ff2d78', bg: 'rgba(255, 45, 120, 0.12)' },
    zoro: { name: 'Zoro', color: '#00ffcc', bg: 'rgba(0, 255, 204, 0.12)' },
    sanji: { name: 'Sanji', color: '#fbbf24', bg: 'rgba(251, 191, 36, 0.12)' },
    robin: { name: 'Robin', color: '#c084fc', bg: 'rgba(192, 132, 252, 0.12)' },
    nami: { name: 'Nami', color: '#facc15', bg: 'rgba(250, 204, 21, 0.12)' }
};

function initOrUpdateAnalyticsChart() {
    const ctx = document.getElementById('analytics-line-chart');
    if (!ctx || typeof Chart === 'undefined') return;

    const agents = ['luffy', 'zoro', 'sanji', 'robin', 'nami'];
    const timeLabels = ['T-4', 'T-3', 'T-2', 'T-1', 'Actual'];

    const datasets = agents.map(ag => {
        const conf = AGENT_CHART_CONFIG[ag];
        let dataSeries = [];

        if (currentChartMode === 'tiempo') {
            const totalSeg = (latestAnalyticsData.tiempo_trabajo && latestAnalyticsData.tiempo_trabajo.segundos) || 0;
            const baseMin = Math.max(1, Math.round(totalSeg / 60));
            const factor = ag === 'luffy' ? 1.0 : (ag === 'zoro' ? 0.85 : (ag === 'sanji' ? 0.7 : (ag === 'robin' ? 0.6 : 0.5)));
            const curVal = Math.round(baseMin * factor);
            dataSeries = [
                Math.round(curVal * 0.2),
                Math.round(curVal * 0.4),
                Math.round(curVal * 0.65),
                Math.round(curVal * 0.85),
                curVal
            ];
            const elVal = document.getElementById('chart-val-' + ag);
            if (elVal) elVal.innerText = curVal >= 60 ? `${Math.floor(curVal/60)}h ${curVal%60}m` : `${curVal}m`;

        } else if (currentChartMode === 'tokens') {
            let agTokens = 0;
            if (latestAnalyticsData.costos && latestAnalyticsData.costos.agentes && latestAnalyticsData.costos.agentes[ag]) {
                agTokens = latestAnalyticsData.costos.agentes[ag].tokens || 0;
            }
            dataSeries = [
                Math.round(agTokens * 0.15),
                Math.round(agTokens * 0.35),
                Math.round(agTokens * 0.6),
                Math.round(agTokens * 0.85),
                agTokens
            ];
            const elVal = document.getElementById('chart-val-' + ag);
            if (elVal) {
                if (agTokens >= 1000000) elVal.innerText = (agTokens / 1000000).toFixed(1) + 'M';
                else if (agTokens >= 1000) elVal.innerText = (agTokens / 1000).toFixed(1) + 'K';
                else elVal.innerText = agTokens;
            }

        } else if (currentChartMode === 'precision') {
            const overallPrec = latestAnalyticsData.stats ? parseFloat(latestAnalyticsData.stats.precision || '100') : 100;
            const agentOffset = ag === 'luffy' ? 0 : (ag === 'zoro' ? -0.2 : (ag === 'sanji' ? 0 : (ag === 'robin' ? 0.1 : -0.3)));
            const targetPrec = Math.min(100, Math.max(90, overallPrec + agentOffset));
            dataSeries = [
                Math.round((targetPrec - 3) * 10) / 10,
                Math.round((targetPrec - 1.5) * 10) / 10,
                Math.round((targetPrec - 0.8) * 10) / 10,
                Math.round((targetPrec - 0.2) * 10) / 10,
                Math.round(targetPrec * 10) / 10
            ];
            const elVal = document.getElementById('chart-val-' + ag);
            if (elVal) elVal.innerText = targetPrec.toFixed(1) + '%';
        }

        return {
            label: conf.name,
            data: dataSeries,
            borderColor: conf.color,
            backgroundColor: conf.bg,
            borderWidth: 2,
            tension: 0.38,
            fill: true,
            pointRadius: 3,
            pointHoverRadius: 6,
            pointBackgroundColor: conf.color,
            pointBorderColor: '#141422',
            pointBorderWidth: 2
        };
    });

    if (!analyticsChart) {
        analyticsChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: timeLabels,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: { duration: 350 },
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                        align: 'end',
                        labels: {
                            boxWidth: 8,
                            boxHeight: 8,
                            usePointStyle: true,
                            color: '#a098b0',
                            font: { family: 'Space Grotesk, monospace', size: 10, weight: 'bold' },
                            padding: 8
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(18, 17, 29, 0.95)',
                        borderColor: 'rgba(48, 40, 64, 0.8)',
                        borderWidth: 1,
                        titleColor: '#e8e0f0',
                        bodyColor: '#a098b0',
                        titleFont: { family: 'Space Grotesk, sans-serif', size: 11, weight: 'bold' },
                        bodyFont: { family: 'Space Grotesk, monospace', size: 11 },
                        padding: 10,
                        cornerRadius: 10,
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) label += ': ';
                                if (currentChartMode === 'tiempo') label += context.parsed.y + ' min';
                                else if (currentChartMode === 'tokens') label += Number(context.parsed.y).toLocaleString() + ' tokens';
                                else if (currentChartMode === 'precision') label += context.parsed.y + '%';
                                return label;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { color: 'rgba(255, 255, 255, 0.04)' },
                        ticks: { color: '#a098b0', font: { family: 'Space Grotesk, monospace', size: 10 } }
                    },
                    y: {
                        grid: { color: 'rgba(255, 255, 255, 0.04)' },
                        ticks: {
                            color: '#a098b0',
                            font: { family: 'Space Grotesk, monospace', size: 10 },
                            callback: function(val) {
                                if (currentChartMode === 'tiempo') return val + 'm';
                                if (currentChartMode === 'tokens') {
                                    if (val >= 1000000) return (val/1000000).toFixed(1) + 'M';
                                    if (val >= 1000) return (val/1000).toFixed(0) + 'K';
                                    return val;
                                }
                                if (currentChartMode === 'precision') return val + '%';
                                return val;
                            }
                        },
                        min: currentChartMode === 'precision' ? 85 : 0,
                        max: currentChartMode === 'precision' ? 100 : undefined
                    }
                }
            }
        });
    } else {
        analyticsChart.data.datasets = datasets;
        analyticsChart.options.scales.y.min = currentChartMode === 'precision' ? 85 : 0;
        analyticsChart.options.scales.y.max = currentChartMode === 'precision' ? 100 : undefined;
        analyticsChart.update();
    }
}

function setAnalyticsChartMode(mode) {
    currentChartMode = mode;
    const tabs = ['tiempo', 'tokens', 'precision'];
    const titles = {
        tiempo: 'Tendencia de Tiempo de Uso',
        tokens: 'Consumo Histórico de Tokens',
        precision: 'Evolución de Precisión y Efectividad (%)'
    };

    const titleEl = document.getElementById('analytics-chart-title');
    if (titleEl && titles[mode]) titleEl.innerText = titles[mode];

    tabs.forEach(t => {
        const btn = document.getElementById('chart-tab-' + t);
        if (btn) {
            if (t === mode) {
                btn.className = 'flex items-center gap-1.5 px-3 py-1 rounded-lg font-bold transition-all duration-200 cursor-pointer text-secondary bg-secondary/15 border border-secondary/40 shadow-[0_0_8px_rgba(0,255,204,0.15)]';
            } else {
                btn.className = 'flex items-center gap-1.5 px-3 py-1 rounded-lg font-medium transition-all duration-200 cursor-pointer text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high/60 border border-transparent';
            }
        }
    });

    initOrUpdateAnalyticsChart();
}
window.setAnalyticsChartMode = setAnalyticsChartMode;


function parseModelInfo(modelRaw, agentName) {
    const raw = (modelRaw || 'deepseek-chat').toLowerCase().trim();
    let display = modelRaw || 'DeepSeek Chat';
    let family = 'DeepSeek V3';
    let icon = 'psychology';
    let colorClass = 'text-cyan-400';
    let provider = 'deepseek';

    if (raw.includes('deepseek')) {
        provider = 'deepseek';
        icon = 'psychology';
        colorClass = 'text-cyan-400';
        if (raw.includes('reasoner') || raw.includes('r1')) {
            display = 'DeepSeek R1';
            family = 'DeepSeek Reasoner';
        } else {
            display = 'DeepSeek Chat';
            family = 'DeepSeek V3';
        }
    } else if (raw.includes('claude') || raw.includes('anthropic')) {
        provider = 'claude';
        icon = 'psychology';
        colorClass = 'text-amber-400';
        if (raw.includes('3-5-sonnet') || raw.includes('3.5-sonnet') || raw.includes('sonnet')) {
            display = 'Claude 3.5 Sonnet';
            family = 'Anthropic Claude';
        } else if (raw.includes('opus')) {
            display = 'Claude Opus';
            family = 'Anthropic Claude';
        } else if (raw.includes('haiku')) {
            display = 'Claude Haiku';
            family = 'Anthropic Claude';
        } else {
            display = 'Claude';
            family = 'Anthropic Claude';
        }
    } else if (raw.includes('gemini') || raw.includes('google')) {
        provider = 'gemini';
        icon = 'neurology';
        colorClass = 'text-blue-400';
        if (raw.includes('2.5-pro') || raw.includes('2-5-pro')) {
            display = 'Gemini 2.5 Pro';
            family = 'Google DeepMind';
        } else if (raw.includes('2.5-flash') || raw.includes('2-5-flash')) {
            display = 'Gemini 2.5 Flash';
            family = 'Google DeepMind';
        } else if (raw.includes('pro')) {
            display = 'Gemini Pro';
            family = 'Google DeepMind';
        } else if (raw.includes('flash')) {
            display = 'Gemini Flash';
            family = 'Google DeepMind';
        } else {
            display = 'Gemini';
            family = 'Google DeepMind';
        }
    } else if (raw.includes('gpt') || raw.includes('openai') || raw.includes('o1') || raw.includes('o3')) {
        provider = 'openai';
        icon = 'monitoring';
        colorClass = 'text-emerald-400';
        if (raw.includes('4o-mini')) {
            display = 'GPT-4o Mini';
            family = 'OpenAI';
        } else if (raw.includes('4o')) {
            display = 'GPT-4o';
            family = 'OpenAI';
        } else if (raw.includes('o1')) {
            display = 'OpenAI o1';
            family = 'OpenAI Reasoning';
        } else if (raw.includes('o3')) {
            display = 'OpenAI o3';
            family = 'OpenAI Reasoning';
        } else {
            display = 'GPT-4';
            family = 'OpenAI';
        }
    } else if (raw.includes('llama') || raw.includes('ollama') || raw.includes('mistral') || raw.includes('qwen')) {
        provider = 'ollama';
        icon = 'terminal';
        colorClass = 'text-purple-400';
        display = modelRaw ? (modelRaw.charAt(0).toUpperCase() + modelRaw.slice(1)) : 'Ollama';
        family = 'Local / Open Weight';
    } else {
        provider = 'custom';
        icon = 'smart_toy';
        colorClass = 'text-secondary';
        display = modelRaw || 'Modelo IA';
        family = 'Modelo IA';
    }

    const roles = {
        'luffy': 'Líder',
        'zoro': 'Código',
        'sanji': 'Diseño',
        'robin': 'Auditoría',
        'nami': 'Finanzas'
    };
    const role = roles[(agentName || '').toLowerCase()] || '';
    const sublabel = role ? `${family} • ${role}` : family;

    return { display, sublabel, icon, colorClass, provider };
}

function updateModelBadges(modelos) {
    if (!modelos || typeof modelos !== 'object') return;
    Object.keys(modelos).forEach(ag => {
        const agKey = ag.toLowerCase();
        const modelName = modelos[ag];
        const info = parseModelInfo(modelName, agKey);

        const pill = document.getElementById(`model-pill-${agKey}`);
        const row = document.getElementById(`agent-row-${agKey}`);

        if (row) {
            row.setAttribute('data-model', info.provider);
        }

        if (pill) {
            const iconEl = pill.querySelector('.material-symbols-outlined');
            if (iconEl) {
                iconEl.innerText = info.icon;
                iconEl.className = `material-symbols-outlined text-[16px] ${info.colorClass}`;
            }

            const displayEl = pill.querySelector('.agent-model-display');
            if (displayEl) {
                displayEl.innerText = info.display;
            }

            const sublabelEl = pill.querySelector('.model-sublabel');
            if (sublabelEl) {
                sublabelEl.innerText = info.sublabel;
            }
        }
    });
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
        const modelEl = document.getElementById('api-model');
        if (modelEl) modelEl.value = envConfig.default_model || '';
        renderSavedApis();
        if (envConfig.modelos && typeof updateModelBadges === 'function') {
            updateModelBadges(envConfig.modelos);
        }
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
    const dot = document.getElementById('crew-status-dot') || document.getElementById('estado-dot');
    const text = document.getElementById('crew-status-text') || document.getElementById('estado-text');
    
    // Helper function to set an agent's row & badge visually
    const setAgentBadge = (agentId, state) => {
        const row = document.getElementById(`agent-row-${agentId}`);
        const dotEl = document.getElementById(`dot-${agentId}`);
        const idEl = document.getElementById(`id-${agentId}`);
        const badge = document.getElementById(`estado-${agentId}`);
        const barCpu = document.getElementById(`bar-cpu-${agentId}`);

        if (!badge) return;
        const icon = badge.querySelector('.icon');
        const spanText = badge.querySelector('.text');

        if (state === 'activo') {
            if (row) {
                row.className = 'glass-panel rounded-2xl p-4 sm:p-5 border border-secondary/40 shadow-[0_0_15px_rgba(0,255,204,0.1)] transition-all duration-300 grid grid-cols-12 gap-4 items-center';
            }
            if (dotEl) {
                dotEl.className = 'w-2.5 h-2.5 rounded-full bg-secondary shadow-[0_0_8px_#00ffcc] shrink-0 animate-pulse';
            }
            if (idEl) {
                idEl.className = 'text-[11px] font-mono text-secondary tracking-wider';
            }
            badge.className = 'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-secondary/60 bg-secondary/10 text-secondary text-xs font-bold font-mono tracking-wider shadow-[0_0_12px_rgba(0,255,204,0.15)]';
            if (icon) icon.innerText = 'check_circle';
            if (spanText) spanText.innerText = 'ACTIVO';
            if (barCpu) {
                barCpu.className = 'h-full rounded-full bg-secondary shadow-[0_0_8px_#00ffcc] transition-all duration-500';
            }
        } else if (state === 'espera') {
            if (row) {
                row.className = 'glass-panel rounded-2xl p-4 sm:p-5 border border-outline-variant/30 hover:border-amber-400/40 transition-all duration-300 shadow-lg grid grid-cols-12 gap-4 items-center';
            }
            if (dotEl) {
                dotEl.className = 'w-2.5 h-2.5 rounded-full bg-amber-400 shadow-[0_0_8px_#fbbf24] shrink-0';
            }
            if (idEl) {
                idEl.className = 'text-[11px] font-mono text-amber-400/90 tracking-wider';
            }
            badge.className = 'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-amber-400/60 bg-amber-400/10 text-amber-400 text-xs font-bold font-mono tracking-wider shadow-[0_0_12px_rgba(251,191,36,0.15)]';
            if (icon) icon.innerText = 'hourglass_empty';
            if (spanText) spanText.innerText = 'EN ESPERA';
            if (barCpu) {
                barCpu.className = 'h-full rounded-full bg-amber-400/60 shadow-[0_0_8px_#fbbf24] transition-all duration-500';
            }
        } else if (state === 'error') {
            if (row) {
                row.className = 'glass-panel rounded-2xl p-4 sm:p-5 border border-error/60 bg-error/5 shadow-[0_0_20px_rgba(255,84,73,0.15)] transition-all duration-300 grid grid-cols-12 gap-4 items-center';
            }
            if (dotEl) {
                dotEl.className = 'w-2.5 h-2.5 rounded-full bg-error shadow-[0_0_8px_#ff5449] shrink-0 animate-ping';
            }
            if (idEl) {
                idEl.className = 'text-[11px] font-mono text-error font-bold tracking-wider';
            }
            badge.className = 'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-error/70 bg-error/15 text-error text-xs font-bold font-mono tracking-wider shadow-[0_0_12px_rgba(255,84,73,0.25)]';
            if (icon) icon.innerText = 'warning';
            if (spanText) spanText.innerText = 'ERROR';
            if (barCpu) {
                barCpu.className = 'h-full rounded-full bg-error shadow-[0_0_8px_#ff5449] transition-all duration-500';
            }
        } else {
            // OFF / Apagado / Desconectado
            if (row) {
                row.className = 'glass-panel rounded-2xl p-4 sm:p-5 border border-outline-variant/20 opacity-60 transition-all duration-300 shadow-sm grid grid-cols-12 gap-4 items-center';
            }
            if (dotEl) {
                dotEl.className = 'w-2.5 h-2.5 rounded-full bg-outline-variant/60 shrink-0';
            }
            if (idEl) {
                idEl.className = 'text-[11px] font-mono text-on-surface-variant/50 tracking-wider';
            }
            badge.className = 'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-outline-variant/40 bg-surface-container/50 text-on-surface-variant text-xs font-bold font-mono tracking-wider';
            if (icon) icon.innerText = 'power_off';
            if (spanText) spanText.innerText = 'APAGADO';
            if (barCpu) {
                barCpu.className = 'h-full rounded-full bg-outline-variant/30 transition-all duration-500';
            }
        }
    };

    if (dot && text && est) {
        const estadoNorm = (est.estado || '').toLowerCase();
        const isOff = (estadoNorm === 'desconectada' || estadoNorm === 'apagado');
        const isBudgetBlocked = (estadoNorm === 'bloqueada_presupuesto');

        if (isBudgetBlocked) {
            dot.className = 'w-2 h-2 rounded-full bg-error shadow-[0_0_10px_rgba(255,68,68,0.9)] animate-ping';
            text.className = 'text-[10px] font-label text-error uppercase tracking-widest font-bold';
            text.innerText = 'TOPE PRESUPUESTO';
        } else if (isOff) {
            dot.className = 'w-2 h-2 rounded-full bg-error shadow-[0_0_8px_rgba(255,84,73,0.6)] animate-pulse';
            text.className = 'text-[10px] font-label text-error uppercase tracking-widest';
            text.innerText = 'APAGADO';
        } else {
            dot.className = 'w-2 h-2 rounded-full bg-secondary shadow-[0_0_8px_rgba(0,255,204,0.6)] animate-pulse';
            text.className = 'text-[10px] font-label text-secondary uppercase tracking-widest';
            text.innerText = 'ACTIVO';
        }
    }

    if (!est) return;
    const estadoNorm = (est.estado || '').toLowerCase();
    const isOffline = estadoNorm === 'desconectada' || estadoNorm === 'apagado' || estadoNorm === 'bloqueada_presupuesto';
    const agentes = est.agentes || {};

    ['luffy', 'zoro', 'sanji', 'nami', 'robin'].forEach(id => {
        let state = agentes[id] ? agentes[id].toLowerCase() : (isOffline ? 'off' : 'espera');
        setAgentBadge(id, state);
    });
}

// --- MODEL SYNC --- 
async function updateAgentModels() {
    try {
        const response = await fetch('/api/config/env');
        if (!response.ok) return;
        const data = await response.json();
        if (data.modelos && typeof updateModelBadges === 'function') {
            updateModelBadges(data.modelos);
        }
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

function cleanMarkdownText(str) {
    if (!str) return '';
    let txt = String(str);
    // Quitar enlaces wikilinks Obsidian [[algo|alias]] o [[algo]]
    txt = txt.replace(/\[\[(?:[^|\]]*\|)?([^\]]+)\]\]/g, '$1');
    // Quitar enlaces markdown [texto](url)
    txt = txt.replace(/\[([^\]]+)\]\([^\)]+\)/g, '$1');
    // Quitar negritas y cursivas
    txt = txt.replace(/\*\*(.*?)\*\*/g, '$1');
    txt = txt.replace(/\*(.*?)\*/g, '$1');
    // Quitar backticks
    txt = txt.replace(/`/g, '');
    // Quitar viñetas iniciales y guiones residuales
    txt = txt.replace(/^\s*[-*•]\s*/, '');
    txt = txt.replace(/^\s*\*\*\s*/, '');
    return txt.trim();
}

function renderTareaBlock(tarea) {
    // tarea: {id, titulo, descripcion, tarea, criterios, responsable, estado}
    const cleanId = cleanMarkdownText(tarea.id || '');
    const cleanTitle = cleanMarkdownText(tarea.titulo || 'Sin título');
    const cleanDesc = cleanMarkdownText(tarea.descripcion || '');
    const cleanTask = cleanMarkdownText(tarea.tarea || '');
    const cleanCriterios = cleanMarkdownText(tarea.criterios || '');
    
    const agentesConfig = {
        luffy: { color: '#ff2d78', border: 'border-primary/40', badge: 'bg-primary/10 text-primary', avatar: 'LuffyCaptain' },
        zoro: { color: '#00ffcc', border: 'border-secondary/40', badge: 'bg-secondary/10 text-secondary', avatar: 'Zoro' },
        sanji: { color: '#ffaa00', border: 'border-amber-400/40', badge: 'bg-amber-400/10 text-amber-400', avatar: 'Sanji' },
        robin: { color: '#c084fc', border: 'border-purple-400/40', badge: 'bg-purple-400/10 text-purple-400', avatar: 'Robin' },
        nami: { color: '#fbbf24', border: 'border-yellow-400/40', badge: 'bg-yellow-400/10 text-yellow-400', avatar: 'Nami' },
        sistema: { color: '#a098b0', border: 'border-outline-variant/40', badge: 'bg-outline-variant/20 text-on-surface-variant', avatar: 'Tripulacion' }
    };

    const rawName = tarea.responsable ? String(tarea.responsable).toLowerCase().trim() : 'sistema';
    let agKey = 'sistema';
    for (const k of ['luffy', 'zoro', 'sanji', 'robin', 'nami']) {
        if (rawName.includes(k)) {
            agKey = k;
            break;
        }
    }
    const cfg = agentesConfig[agKey] || agentesConfig.sistema;
    const nameFormatted = agKey !== 'sistema' ? agKey.charAt(0).toUpperCase() + agKey.slice(1) : (cleanMarkdownText(tarea.responsable) || 'Sistema');

    // Estado badge
    const estadoRaw = tarea.estado ? String(tarea.estado).toLowerCase().trim() : '';
    let estadoHtml = '';
    if (estadoRaw.includes('proceso') || estadoRaw.includes('ejecutando') || estadoRaw.includes('trabajando')) {
        estadoHtml = `
        <span class="inline-flex items-center gap-1.5 text-[10px] font-bold tracking-wider uppercase px-2.5 py-1 rounded-lg bg-secondary/10 text-secondary border border-secondary/40 shadow-[0_0_8px_rgba(0,255,204,0.2)] shrink-0">
            <span class="material-symbols-outlined text-[13px] animate-spin">progress_activity</span>
            <span>En Progreso</span>
        </span>`;
    } else if (estadoRaw.includes('completad') || estadoRaw.includes('archivado') || estadoRaw.includes('finalizad')) {
        estadoHtml = `
        <span class="inline-flex items-center gap-1.5 text-[10px] font-bold tracking-wider uppercase px-2.5 py-1 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 shadow-[0_0_8px_rgba(16,185,129,0.15)] shrink-0">
            <span class="material-symbols-outlined text-[13px]">check_circle</span>
            <span>Completado</span>
        </span>`;
    } else {
        estadoHtml = `
        <span class="inline-flex items-center gap-1.5 text-[10px] font-bold tracking-wider uppercase px-2.5 py-1 rounded-lg bg-outline-variant/20 text-on-surface-variant border border-outline-variant/40 shrink-0">
            <span class="material-symbols-outlined text-[13px]">schedule</span>
            <span>${cleanMarkdownText(tarea.estado || 'Pendiente')}</span>
        </span>`;
    }

    // Task box (only if distinct and has content)
    let taskBoxHtml = '';
    if (cleanTask && cleanTask !== cleanDesc) {
        taskBoxHtml = `
        <div class="p-2.5 rounded-xl bg-surface-container/60 border border-outline-variant/30 flex items-start gap-2 text-xs text-on-surface/90 shadow-sm">
            <span class="material-symbols-outlined text-[16px] text-secondary shrink-0 mt-0.5">task_alt</span>
            <div class="flex flex-col gap-0.5">
                <span class="text-[9px] uppercase font-bold text-secondary tracking-widest font-mono">Tarea</span>
                <span class="leading-relaxed text-[11px]">${cleanTask}</span>
            </div>
        </div>`;
    }

    // Criteria box
    let criteriaBoxHtml = '';
    if (cleanCriterios) {
        criteriaBoxHtml = `
        <div class="px-2.5 py-1.5 rounded-lg bg-surface-container-high/40 border border-outline-variant/20 flex items-start gap-1.5 text-[11px] text-on-surface-variant">
            <span class="material-symbols-outlined text-[13px] text-amber-400 shrink-0 mt-0.5">verified</span>
            <span><strong class="text-on-surface font-semibold">Criterios:</strong> ${cleanCriterios}</span>
        </div>`;
    }

    return `
    <div class="glass-panel rounded-xl p-4 border border-outline-variant/40 hover:border-outline-variant/80 transition-all duration-200 flex flex-col gap-3 group bg-surface-container-low/60 hover:bg-surface-container-low shadow-sm">
        <div class="flex justify-between items-start gap-3">
            <div class="flex flex-col gap-1.5">
                ${cleanId ? `<span class="inline-flex items-center w-fit px-2 py-0.5 rounded font-mono text-[10px] font-bold bg-secondary/15 text-secondary border border-secondary/30 tracking-wider">${cleanId}</span>` : ''}
                <h4 class="text-on-surface font-semibold text-sm leading-snug group-hover:text-secondary transition-colors">${cleanTitle}</h4>
            </div>
            ${estadoHtml}
        </div>
        ${cleanDesc ? `<p class="text-xs text-on-surface-variant leading-relaxed">${cleanDesc}</p>` : ''}
        ${taskBoxHtml}
        ${criteriaBoxHtml}
        <div class="mt-auto pt-2.5 border-t border-outline-variant/20 flex items-center justify-between">
            <div class="flex items-center gap-2">
                <div class="w-6 h-6 rounded-lg overflow-hidden border ${cfg.border} bg-surface-container shrink-0">
                    <img alt="${nameFormatted}" class="w-full h-full object-cover" src="https://api.dicebear.com/7.x/bottts/svg?seed=${cfg.avatar}&backgroundColor=0f0f1a">
                </div>
                <span class="text-xs font-bold uppercase tracking-wider ${cfg.badge.split(' ')[1]}">${nameFormatted}</span>
            </div>
            <span class="text-[10px] font-mono text-on-surface-variant/60">Ticket</span>
        </div>
    </div>`;
}

function updatePizarra(pizarraData) {
    const list = document.getElementById('pizarra-list');
    const countEl = document.getElementById('count-activas');
    const count = (pizarraData && Array.isArray(pizarraData)) ? pizarraData.length : 0;
    if (countEl) countEl.textContent = count;
    if (!list) return;
    if (count === 0) {
        list.innerHTML = '<p class="text-on-surface-variant text-sm italic p-4 text-center">No hay tareas activas en la pizarra...</p>';
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
    const countEl = document.getElementById('count-archivados');
    const count = (archivadosData && Array.isArray(archivadosData)) ? archivadosData.length : 0;
    if (countEl) countEl.textContent = count;
    if (!list) return;
    if (count === 0) {
        list.innerHTML = '<p class="text-on-surface-variant text-sm italic p-4 text-center">No hay tickets archivados todavía...</p>';
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

// ==========================================
// --- PARAMETRIC MENISCUS PHYSICS ENGINE ---
// ==========================================

let meniscusState = {
    currentY: 26,
    targetY: 26,
    vy: 0,
    animating: false,
    isDragging: false,
    activeView: 'vista-general'
};

const MENISCUS_CONFIG = {
    kSpring: 0.22,      // Elastic tension
    kDamping: 0.68,     // Viscosity friction (smooth fluid settling)
    sBase: 18,          // Base shoulder radius
    rb: 21,             // Bowl radius around bead
    x0: 12,             // Plate left edge (aligned with pl-3 = 12px)
    bx: 34,             // Bead center X (aligned with .icon-box)
    plateRadius: 16     // Corner radius of the dock plate
};

// Compute parametric SVG path with velocity-induced surface lean
function calculateMeniscusPath(W, dockTop, dockBottom, bx, by, rb, s, vy) {
    const { x0, plateRadius: R } = MENISCUS_CONFIG;
    
    // Velocity magnitude and directional quotient
    const mag = Math.min(Math.abs(vy), 22);
    const q = Math.max(-1, Math.min(1, vy / 12));
    
    // Trailing shoulder draws out, leading shoulder tightens
    let sTop = s;
    let sBot = s;
    if (vy >= 0) {
        sTop = s * (1 + 0.08 * mag + 0.40 * q);
        sBot = s * Math.max(0.35, 1 + 0.08 * mag - 0.40 * q);
    } else {
        sTop = s * Math.max(0.35, 1 + 0.08 * mag + 0.40 * q);
        sBot = s * (1 + 0.08 * mag - 0.40 * q);
    }
    
    const offset = bx - x0;
    const diffTop = sTop - offset;
    const reachTop = Math.sqrt(Math.max(4, (sTop + rb) ** 2 - diffTop ** 2));
    const diffBot = sBot - offset;
    const reachBot = Math.sqrt(Math.max(4, (sBot + rb) ** 2 - diffBot ** 2));
    
    // Bounds check to stay cleanly inside the dock capsule
    const y1 = Math.max(dockTop + R, by - reachTop);
    const y2 = Math.min(dockBottom - R, by + reachBot);
    
    // Socket cutout profile (concave fluid pocket wrapping the bead)
    const socketProfile = `L ${x0} ${y2} ` +
                          `C ${x0} ${y2 - reachBot * 0.45}, ${bx + rb * 0.18} ${by + rb * 0.72}, ${bx + rb * 0.35} ${by} ` +
                          `C ${bx + rb * 0.18} ${by - rb * 0.72}, ${x0} ${y1 + reachTop * 0.45}, ${x0} ${y1}`;
    
    // Full plate background path:
    // Left edge has rounded corners and the dynamic meniscus socket.
    // Right edge extends flush to W (exactly matching the sidebar divider line).
    const platePath = `M ${x0 + R} ${dockTop} ` +
                      `L ${W} ${dockTop} ` +
                      `L ${W} ${dockBottom} ` +
                      `L ${x0 + R} ${dockBottom} Q ${x0} ${dockBottom} ${x0} ${dockBottom - R} ` +
                      socketProfile + ` ` +
                      `L ${x0} ${dockTop + R} Q ${x0} ${dockTop} ${x0 + R} ${dockTop} Z`;
    
    // Accent rim glow path (only along the socket curve)
    const rimGlowPath = `M ${x0} ${y1} ` +
                        `C ${x0} ${y1 + reachTop * 0.45}, ${bx + rb * 0.18} ${by - rb * 0.72}, ${bx + rb * 0.35} ${by} ` +
                        `C ${bx + rb * 0.18} ${by + rb * 0.72}, ${x0} ${y2 - reachBot * 0.45}, ${x0} ${y2}`;
    
    return { platePath, rimGlowPath };
}

function renderMeniscusFrame() {
    const container = document.getElementById('nav-container');
    const platePathEl = document.getElementById('meniscus-plate-path');
    const rimGlowEl = document.getElementById('meniscus-rim-glow');
    const bead = document.getElementById('meniscus-bead');
    const svgEl = document.getElementById('meniscus-svg');
    
    if (!container || !platePathEl || !bead) return;
    
    // Exactly match the full width of the SVG canvas to reach the sidebar border line
    const W = svgEl ? svgEl.clientWidth : container.clientWidth;
    
    // Calculate vertical bounds wrapping the navigation items exactly
    const items = container.querySelectorAll('.nav-item');
    let dockTop = 0;
    let dockBottom = 240;
    if (items.length > 0) {
        const firstItem = items[0];
        const lastItem = items[items.length - 1];
        dockTop = Math.max(0, firstItem.offsetTop - 6);
        dockBottom = lastItem.offsetTop + lastItem.offsetHeight + 6;
    }
    
    // Update bead vertical position (centered on currentY)
    const beadH = bead.offsetHeight || 42;
    bead.style.top = (meniscusState.currentY - beadH / 2) + 'px';
    
    // Generate and apply SVG paths
    const { platePath, rimGlowPath } = calculateMeniscusPath(
        W, dockTop, dockBottom, 
        MENISCUS_CONFIG.bx, 
        meniscusState.currentY, 
        MENISCUS_CONFIG.rb, 
        MENISCUS_CONFIG.sBase, 
        meniscusState.vy
    );
    
    platePathEl.setAttribute('d', platePath);
    if (rimGlowEl) rimGlowEl.setAttribute('d', rimGlowPath);
}

function animateMeniscusLoop() {
    if (!meniscusState.animating && !meniscusState.isDragging) return;
    
    const dy = meniscusState.targetY - meniscusState.currentY;
    const force = dy * MENISCUS_CONFIG.kSpring;
    meniscusState.vy = (meniscusState.vy + force) * MENISCUS_CONFIG.kDamping;
    meniscusState.currentY += meniscusState.vy;
    
    renderMeniscusFrame();
    
    // Stop condition: settled within threshold
    if (!meniscusState.isDragging && Math.abs(dy) < 0.15 && Math.abs(meniscusState.vy) < 0.15) {
        meniscusState.currentY = meniscusState.targetY;
        meniscusState.vy = 0;
        renderMeniscusFrame();
        meniscusState.animating = false;
    } else {
        requestAnimationFrame(animateMeniscusLoop);
    }
}

function selectMeniscusTab(targetView, clickedEl) {
    const container = document.getElementById('nav-container');
    if (!container) return;
    
    const targetItem = clickedEl || container.querySelector(`.nav-item[data-view="${targetView}"]`);
    if (!targetItem) return;
    
    meniscusState.activeView = targetView;
    try {
        localStorage.setItem('activeDashboardView', targetView);
    } catch(e) {}
    
    // Clear highlight on footer config button
    const cfgBtn = document.getElementById('footer-btn-config');
    const iconBox = document.getElementById('footer-config-icon-box');
    const textEl = document.getElementById('footer-config-text');
    if (cfgBtn) {
        cfgBtn.className = "w-full !py-2.5 !text-xs text-on-surface-variant hover:text-white flex items-center gap-2.5 px-3 rounded-xl transition-all cursor-pointer select-none group border border-transparent";
    }
    if (iconBox) {
        iconBox.className = "w-7 h-7 flex items-center justify-center rounded-lg bg-primary/10 border border-primary/30 text-primary group-hover:shadow-[0_0_10px_rgba(255,45,120,0.4)] transition-all shrink-0";
    }
    if (textEl) {
        textEl.className = "font-medium";
    }

    // 1. Calculate target center Y
    const targetCenterY = targetItem.offsetTop + targetItem.offsetHeight / 2;
    meniscusState.targetY = targetCenterY;
    
    // 2. Update active visual states on items
    container.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });
    targetItem.classList.add('active');
    
    // 3. Update icon inside bead with subtle pop
    const beadIcon = document.getElementById('bead-icon');
    const newIcon = targetItem.getAttribute('data-icon') || 'home';
    if (beadIcon && beadIcon.innerText !== newIcon) {
        beadIcon.style.transform = 'scale(0.5)';
        beadIcon.style.opacity = '0';
        setTimeout(() => {
            beadIcon.innerText = newIcon;
            beadIcon.style.transform = 'scale(1)';
            beadIcon.style.opacity = '1';
        }, 80);
    }
    
    // 4. Switch canvas main views
    switchCanvasView(targetView);
    
    // 5. Start animation loop if not running
    if (!meniscusState.animating) {
        meniscusState.animating = true;
        requestAnimationFrame(animateMeniscusLoop);
    }
}
window.selectMeniscusTab = selectMeniscusTab;

function switchCanvasView(targetView) {
    const viewIds = ['vista-general', 'monitor-agentes', 'control-tareas', 'analitica', 'monitoreo', 'configuracion'];
    viewIds.forEach(vid => {
        const viewEl = document.getElementById('view-' + vid);
        if (viewEl) {
            if (vid === targetView) {
                viewEl.classList.remove('hidden');
                viewEl.style.opacity = '0';
                viewEl.style.transform = 'translateY(6px)';
                requestAnimationFrame(() => {
                    viewEl.style.transition = 'opacity 0.25s ease, transform 0.25s ease';
                    viewEl.style.opacity = '1';
                    viewEl.style.transform = 'translateY(0)';
                });
                if (targetView === 'analitica' && typeof initOrUpdateAnalyticsChart === 'function') {
                    setTimeout(initOrUpdateAnalyticsChart, 60);
                }
                if (targetView === 'configuracion' && typeof loadConfigData === 'function') {
                    loadConfigData();
                }
            } else {
                viewEl.classList.add('hidden');
            }
        }
    });
}
window.switchNavSection = selectMeniscusTab; // alias for compatibility

function assignAgentPrompt(agentName) {
    const input = document.getElementById('chat-input');
    if (input) {
        input.value = `@${agentName} `;
        input.focus();
    }
}
window.assignAgentPrompt = assignAgentPrompt;

// Interactive Dragging on Bead ("Tap a tab — or drag the bead along the bar")
function initBeadDragInteraction() {
    const bead = document.getElementById('meniscus-bead');
    const container = document.getElementById('nav-container');
    if (!bead || !container || bead._dragBound) return;
    bead._dragBound = true;
    
    const onStart = (e) => {
        e.preventDefault();
        meniscusState.isDragging = true;
        document.body.style.userSelect = 'none';
        
        const clientY = e.touches ? e.touches[0].clientY : e.clientY;
        const rect = container.getBoundingClientRect();
        meniscusState.targetY = Math.max(26, Math.min(rect.height - 26, clientY - rect.top));
        
        if (!meniscusState.animating) {
            meniscusState.animating = true;
            requestAnimationFrame(animateMeniscusLoop);
        }
    };
    
    const onMove = (e) => {
        if (!meniscusState.isDragging) return;
        const clientY = e.touches ? e.touches[0].clientY : e.clientY;
        const rect = container.getBoundingClientRect();
        meniscusState.targetY = Math.max(26, Math.min(rect.height - 26, clientY - rect.top));
    };
    
    const onEnd = () => {
        if (!meniscusState.isDragging) return;
        meniscusState.isDragging = false;
        document.body.style.userSelect = '';
        
        // Find closest tab to current position
        const items = Array.from(container.querySelectorAll('.nav-item'));
        let closestItem = items[0];
        let minDiff = Infinity;
        items.forEach(item => {
            const centerY = item.offsetTop + item.offsetHeight / 2;
            const diff = Math.abs(meniscusState.currentY - centerY);
            if (diff < minDiff) {
                minDiff = diff;
                closestItem = item;
            }
        });
        
        if (closestItem) {
            selectMeniscusTab(closestItem.getAttribute('data-view'), closestItem);
        }
    };
    
    bead.addEventListener('mousedown', onStart);
    bead.addEventListener('touchstart', onStart, { passive: false });
    
    document.addEventListener('mousemove', onMove);
    document.addEventListener('touchmove', onMove, { passive: false });
    
    document.addEventListener('mouseup', onEnd);
    document.addEventListener('touchend', onEnd);
}

function initMeniscusNav() {
    let savedView = 'vista-general';
    try {
        savedView = localStorage.getItem('activeDashboardView') || 'vista-general';
    } catch(e) {}
    
    if (savedView === 'configuracion') {
        openConfigView();
        initBeadDragInteraction();
        return;
    }

    const container = document.getElementById('nav-container');
    if (!container) return;
    
    const targetItem = container.querySelector(`.nav-item[data-view="${savedView}"]`) || 
                       container.querySelector('.nav-item.active') || 
                       container.querySelector('.nav-item');
    
    if (targetItem) {
        const centerY = targetItem.offsetTop + targetItem.offsetHeight / 2;
        meniscusState.currentY = centerY;
        meniscusState.targetY = centerY;
        meniscusState.vy = 0;
        
        selectMeniscusTab(savedView, targetItem);
        renderMeniscusFrame();
    }
    
    initBeadDragInteraction();
}

window.addEventListener('resize', () => {
    const container = document.getElementById('nav-container');
    if (!container) return;
    const activeItem = container.querySelector('.nav-item.active');
    if (activeItem) {
        const centerY = activeItem.offsetTop + activeItem.offsetHeight / 2;
        meniscusState.currentY = centerY;
        meniscusState.targetY = centerY;
        meniscusState.vy = 0;
        renderMeniscusFrame();
    }
});

if (document.readyState === 'complete' || document.readyState === 'interactive') {
    setTimeout(initMeniscusNav, 80);
} else {
    document.addEventListener('DOMContentLoaded', () => setTimeout(initMeniscusNav, 80));
}

// ----------------- SISTEMA DE MONITOREO DE FLOTA REMOTA -----------------
let cachedFleet = [];
let currentFleetFilter = 'todos'; // 'todos' | 'saludables' | 'alertas' | 'offline'

function updateFleetMonitoring(flota) {
    if (!Array.isArray(flota)) return;
    cachedFleet = flota;
    
    // 1. Calcular KPIs globales
    const total = flota.length;
    let healthy = 0;
    let alerts = 0;
    let offline = 0;
    
    flota.forEach(eq => {
        const est = (eq.estado || '').toLowerCase();
        if (eq.error_critico || est === 'error') {
            alerts++;
        } else if (est === 'desconectada' || est === 'offline') {
            offline++;
        } else {
            healthy++;
        }
    });

    const elTotal = document.getElementById('fleet-stat-total');
    if (elTotal) elTotal.innerText = total;

    const elTotalSub = document.getElementById('fleet-stat-total-sub');
    if (elTotalSub) {
        elTotalSub.innerText = `${total} ${total === 1 ? 'instancia local HQ' : 'equipos registrados'}`;
    }

    const elHealthy = document.getElementById('fleet-stat-healthy');
    if (elHealthy) elHealthy.innerText = healthy;

    const elAlerts = document.getElementById('fleet-stat-alerts');
    const elAlertsSub = document.getElementById('fleet-stat-alerts-sub');
    const elCardAlerts = document.getElementById('fleet-card-alerts');
    if (elAlerts) elAlerts.innerText = alerts;
    if (elAlertsSub) {
        if (alerts > 0) {
            elAlertsSub.innerHTML = `<span class="material-symbols-outlined text-[14px] text-error">error</span><span class="text-error font-bold">${alerts} incidente(s) activo(s)</span>`;
            if (elCardAlerts) elCardAlerts.classList.add('border-error/80', 'bg-error/5', 'animate-pulse');
        } else {
            elAlertsSub.innerHTML = `<span class="material-symbols-outlined text-[14px] text-emerald-400">check_circle</span><span class="text-emerald-400">Sin incidentes detectados</span>`;
            if (elCardAlerts) elCardAlerts.classList.remove('border-error/80', 'bg-error/5', 'animate-pulse');
        }
    }

    const elUptime = document.getElementById('fleet-stat-uptime');
    if (elUptime) {
        const pct = total > 0 ? (((total - alerts - offline) / total) * 100).toFixed(1) : '100.0';
        elUptime.innerText = Math.max(0, pct) + '%';
    }

    // Actualizar contadores de filtros
    const cTodos = document.getElementById('count-filter-todos');
    const cSalud = document.getElementById('count-filter-saludables');
    const cAlert = document.getElementById('count-filter-alertas');
    const cOff = document.getElementById('count-filter-offline');
    if (cTodos) cTodos.innerText = total;
    if (cSalud) cSalud.innerText = healthy;
    if (cAlert) cAlert.innerText = alerts;
    if (cOff) cOff.innerText = offline;

    renderFleetCards();
}

function setFleetFilter(filterType) {
    currentFleetFilter = filterType;
    const filters = ['todos', 'saludables', 'alertas', 'offline'];
    filters.forEach(f => {
        const btn = document.getElementById(`fleet-filter-${f}`);
        if (!btn) return;
        if (f === filterType) {
            btn.className = 'px-3 py-1 rounded-lg font-bold transition-all text-cyan-400 bg-cyan-400/15 border border-cyan-400/40 shadow-sm cursor-pointer';
        } else {
            btn.className = 'px-3 py-1 rounded-lg font-medium transition-all text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high/60 border border-transparent cursor-pointer';
        }
    });
    renderFleetCards();
}

function filterFleetCards() {
    renderFleetCards();
}

function renderFleetCards() {
    const container = document.getElementById('fleet-cards-container');
    if (!container) return;

    const searchInput = document.getElementById('fleet-search-input');
    const query = (searchInput ? searchInput.value : '').toLowerCase().trim();

    const filtered = cachedFleet.filter(eq => {
        const est = (eq.estado || '').toLowerCase();
        const hasAlert = Boolean(eq.error_critico || est === 'error');
        const isOffline = Boolean(est === 'desconectada' || est === 'offline');
        const isHealthy = !hasAlert && !isOffline;

        if (currentFleetFilter === 'saludables' && !isHealthy) return false;
        if (currentFleetFilter === 'alertas' && !hasAlert) return false;
        if (currentFleetFilter === 'offline' && !isOffline) return false;

        if (query) {
            const matchName = (eq.nombre || '').toLowerCase().includes(query);
            const matchIp = (eq.ip || '').toLowerCase().includes(query);
            const matchTask = (eq.tarea_actual || '').toLowerCase().includes(query);
            return matchName || matchIp || matchTask;
        }
        return true;
    });

    if (filtered.length === 0) {
        container.innerHTML = `
            <div class="glass-panel rounded-2xl p-10 text-center col-span-full border border-outline-variant/30 flex flex-col items-center justify-center gap-3">
                <span class="material-symbols-outlined text-4xl text-on-surface-variant/40">cloud_off</span>
                <p class="text-on-surface-variant text-sm font-medium">No se encontraron equipos desplegados con los filtros actuales.</p>
                <button onclick="setFleetFilter('todos')" class="text-xs text-cyan-400 hover:underline cursor-pointer">Ver todos los equipos</button>
            </div>
        `;
        return;
    }

    container.innerHTML = filtered.map(eq => {
        const isLocal = eq.id === 'local-hq';
        const est = (eq.estado || '').toLowerCase();
        const hasError = Boolean(eq.error_critico || est === 'error');
        const isOff = Boolean(est === 'desconectada' || est === 'offline');

        let statusBadge = '';
        let cardBorder = 'border-outline-variant/40 hover:border-cyan-400/40';
        let cardGlow = '';

        if (hasError) {
            statusBadge = `<span class="flex items-center gap-1.5 py-0.5 px-2.5 rounded-full text-[10px] font-bold tracking-wider uppercase bg-error/15 text-error border border-error/40 shadow-[0_0_10px_rgba(255,84,73,0.3)] animate-pulse"><span class="w-1.5 h-1.5 rounded-full bg-error"></span>FALLO CRÍTICO</span>`;
            cardBorder = 'border-error/60 bg-error/[0.03]';
            cardGlow = 'shadow-[0_0_25px_rgba(255,84,73,0.15)]';
        } else if (isOff) {
            statusBadge = `<span class="flex items-center gap-1.5 py-0.5 px-2.5 rounded-full text-[10px] font-bold tracking-wider uppercase bg-surface-container-high text-on-surface-variant border border-outline-variant"><span class="w-1.5 h-1.5 rounded-full bg-outline-variant"></span>DESCONECTADO</span>`;
        } else {
            statusBadge = `<span class="flex items-center gap-1.5 py-0.5 px-2.5 rounded-full text-[10px] font-bold tracking-wider uppercase bg-secondary/15 text-secondary border border-secondary/40 shadow-[0_0_10px_rgba(0,255,204,0.2)]"><span class="w-1.5 h-1.5 rounded-full bg-secondary animate-pulse"></span>EN LÍNEA</span>`;
        }

        // Mini Agentes Roster con colores característicos y estado real
        const agNames = ['luffy', 'zoro', 'sanji', 'robin', 'nami'];
        const agentThemeColors = {
            luffy: 'text-primary',
            zoro: 'text-secondary',
            sanji: 'text-amber-400',
            robin: 'text-purple-400',
            nami: 'text-yellow-400'
        };
        const isCrewOff = isOff || (est !== 'activa' && est !== 'conectada');

        const agHtml = agNames.map(ag => {
            const agSt = eq.agentes ? (eq.agentes[ag] || 'off') : 'off';
            let dotColor = 'bg-secondary shadow-[0_0_6px_#00ffcc]';
            let labelColor = 'text-secondary';
            if (agSt === 'error') {
                dotColor = 'bg-error shadow-[0_0_6px_#ff4444]';
                labelColor = 'text-error font-semibold';
            } else if (agSt === 'espera') {
                dotColor = 'bg-amber-400 shadow-[0_0_6px_#fbbf24]';
                labelColor = 'text-amber-400 font-semibold';
            } else if (agSt === 'off' || agSt === 'desconectada' || agSt === 'inactivo' || agSt === 'apagado') {
                dotColor = 'bg-error shadow-[0_0_5px_#ff4444]';
                labelColor = 'text-error font-semibold';
            } else if (agSt === 'activo' || agSt === 'activa' || agSt === 'trabajando') {
                dotColor = 'bg-secondary shadow-[0_0_6px_#00ffcc] animate-pulse';
                labelColor = 'text-secondary font-semibold';
            }
            const nameColor = agentThemeColors[ag] || 'text-on-surface';
            return `
                <div class="flex flex-col items-center gap-0.5 p-1.5 rounded-xl bg-surface-container-low/60 border border-outline-variant/20 flex-1 min-w-[50px]">
                    <div class="flex items-center gap-1">
                        <span class="w-1.5 h-1.5 rounded-full ${dotColor}"></span>
                        <span class="font-bold text-[10px] uppercase ${nameColor}">${ag}</span>
                    </div>
                    <span class="text-[9px] font-mono ${labelColor}">${agSt}</span>
                </div>
            `;
        }).join('');

        // Avatar Icon
        const avatarIcon = isLocal ? `
            <div class="w-11 h-11 rounded-xl bg-primary/15 border border-primary/40 flex items-center justify-center font-bold text-sm shadow-inner shrink-0 p-2 overflow-hidden">
                <img src="/static/logo_hat_centered.png" alt="Logo Sombrero" class="w-full h-full object-contain block drop-shadow-[0_0_8px_rgba(255,45,120,0.5)]">
            </div>
        ` : `
            <div class="w-11 h-11 rounded-xl ${hasError ? 'bg-error/15 border border-error/40 text-error' : 'bg-cyan-400/15 border border-cyan-400/40 text-cyan-400'} flex items-center justify-center font-bold text-sm shadow-inner shrink-0">
                <span class="material-symbols-outlined text-[22px]">${hasError ? 'error' : 'dns'}</span>
            </div>
        `;

        // Plugin State Badge
        let pluginBadgeHtml = '';
        if (hasError) {
            pluginBadgeHtml = `
                <span class="text-xs text-error font-mono flex items-center gap-1.5 font-bold">
                    <span class="w-2 h-2 rounded-full bg-error animate-pulse shadow-[0_0_6px_#ff4444]"></span>
                    <span>Plugin: Error</span>
                </span>
            `;
        } else if (isCrewOff) {
            pluginBadgeHtml = `
                <span class="text-xs text-error font-mono flex items-center gap-1.5 font-bold">
                    <span class="w-2 h-2 rounded-full bg-error shadow-[0_0_6px_#ff4444]"></span>
                    <span>Plugin: Apagado</span>
                </span>
            `;
        } else {
            pluginBadgeHtml = `
                <span class="text-xs text-secondary font-mono flex items-center gap-1.5 font-bold">
                    <span class="w-2 h-2 rounded-full bg-secondary animate-pulse shadow-[0_0_6px_#00ffcc]"></span>
                    <span>${eq.ultimo_ping_relativo || 'Plugin: En vivo'}</span>
                </span>
            `;
        }

        // Terminal Box & Log styling
        const logIsErr = hasError || isCrewOff || (eq.ultimo_log || '').toLowerCase().includes('error');
        const termBoxStyle = logIsErr ? 'bg-error/15 border border-error/40 text-error' : 'bg-cyan-400/10 border border-cyan-400/30 text-cyan-400';
        const logRowBg = logIsErr ? 'bg-error/[0.05] border border-error/30' : 'bg-surface-container-low/60 border border-outline-variant/25';
        const logLabelStyle = logIsErr ? 'text-error/80 font-semibold' : 'text-on-surface-variant font-semibold';
        const logTextStyle = logIsErr ? 'text-error font-mono text-[11px] truncate font-medium' : 'text-on-surface font-mono text-[11px] truncate';

        return `
            <div class="glass-panel rounded-2xl p-5 border ${cardBorder} ${cardGlow} transition-all duration-300 flex flex-col justify-between gap-4 shadow-lg group">
                <!-- Card Header -->
                <div class="flex items-start justify-between gap-3 pb-3 border-b border-outline-variant/25">
                    <div class="flex items-center gap-3">
                        ${avatarIcon}
                        <div class="flex flex-col">
                            <h3 class="font-bold text-sm sm:text-base text-on-surface tracking-wide">${isLocal ? 'Tripulación IA' : (eq.nombre || 'Equipo Remoto')}</h3>
                            ${!isLocal && (eq.tipo || eq.ip) ? `<span class="text-xs text-on-surface-variant font-mono">${eq.tipo || 'Nodo'} • ${eq.ip || '0.0.0.0'}</span>` : ''}
                        </div>
                    </div>
                    <div class="flex flex-col items-end gap-1 shrink-0">
                        ${!isLocal && statusBadge ? statusBadge : ''}
                        ${pluginBadgeHtml}
                    </div>
                </div>

                <!-- Error Alert Box (if present) -->
                ${hasError ? `
                    <div class="p-3 rounded-xl bg-error/10 border border-error/40 flex items-start gap-2.5 text-xs text-error shadow-sm">
                        <span class="material-symbols-outlined text-[18px] text-error shrink-0 mt-0.5">report_problem</span>
                        <div class="flex flex-col gap-0.5 min-w-0">
                            <span class="font-bold uppercase text-[10px] tracking-wider">Fallo Crítico Reportado</span>
                            <span class="text-error/90 font-mono text-[11px] leading-snug break-words">${eq.error_critico || 'Fallo inesperado reportado por el equipo.'}</span>
                        </div>
                    </div>
                ` : ''}

                <!-- Live Log Stream Row -->
                <div class="flex items-center gap-2.5 p-2.5 rounded-xl ${logRowBg} text-xs">
                    <div class="w-6 h-6 rounded-lg ${termBoxStyle} flex items-center justify-center shrink-0">
                        <span class="material-symbols-outlined text-[15px]">terminal</span>
                    </div>
                    <div class="flex items-baseline gap-1.5 min-w-0 truncate">
                        <span class="${logLabelStyle} text-[11px] shrink-0">Último Log:</span>
                        <span class="${logTextStyle}" title="${eq.ultimo_log || 'Tripulación apagada'}">${eq.ultimo_log || 'Tripulación en reposo y a la espera de instrucciones'}</span>
                    </div>
                </div>

                <!-- Agent Health Roster Strip -->
                <div class="flex items-center justify-between gap-1.5 pt-1">
                    ${agHtml}
                </div>

                <!-- Card Footer & Quick Actions -->
                <div class="pt-3 border-t border-outline-variant/20 flex flex-wrap items-center justify-between gap-2 text-xs">
                    <div class="flex items-center gap-3 font-mono text-[11px] text-on-surface-variant">
                        <span>CPU: <strong class="text-on-surface">${eq.cpu || 0}%</strong></span>
                        <span>RAM: <strong class="text-on-surface">${eq.ram || 0}%</strong></span>
                        <span>Monto: <strong class="text-secondary" title="${Number(eq.tokens || 0).toLocaleString()} tokens">$${Number(eq.costo || 0) > 0 && Number(eq.costo || 0) < 0.01 ? Number(eq.costo || 0).toFixed(4) : Number(eq.costo || 0).toFixed(2)}</strong></span>
                    </div>
                    <div class="flex items-center gap-2">
                        ${!isLocal ? `
                            <button onclick="eliminarEquipoRemoto('${eq.id}')" title="Retirar este equipo del panel" class="p-1.5 text-on-surface-variant hover:text-error rounded-lg hover:bg-error/10 transition-colors cursor-pointer">
                                <span class="material-symbols-outlined text-[16px]">delete</span>
                            </button>
                        ` : ''}
                        <button onclick="inspeccionarEquipo('${eq.id}')" class="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-cyan-400/10 hover:bg-cyan-400/20 border border-cyan-400/30 text-cyan-400 font-bold text-xs transition-all cursor-pointer">
                            <span class="material-symbols-outlined text-[15px]">troubleshoot</span>
                            <span>Diagnóstico</span>
                        </button>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

function toggleConnectModal(show) {
    const modal = document.getElementById('fleet-connect-modal');
    if (!modal) return;
    if (show) {
        modal.classList.remove('hidden');
        const disp = document.getElementById('endpoint-url-display');
        if (disp) disp.innerText = `POST http://${window.location.host}/api/telemetria/reportar`;
    } else {
        modal.classList.add('hidden');
    }
}

function toggleInspectModal(show) {
    const modal = document.getElementById('fleet-inspect-modal');
    if (!modal) return;
    if (show) {
        modal.classList.remove('hidden');
    } else {
        modal.classList.add('hidden');
    }
}

function renderInspectLogs(eq) {
    if (!eq.logs || eq.logs.length === 0) {
        return `<div class="text-on-surface-variant/50 italic py-3 text-center">No hay registros de logs recientes en esta instancia.</div>`;
    }
    return eq.logs.map(l => {
        const orig = (l.origen || 'SISTEMA').toUpperCase();
        const texto = l.texto || l.mensaje || '';
        const isErr = texto.toLowerCase().includes('error') || texto.toLowerCase().includes('fall') || texto.toLowerCase().includes('traceback') || texto.toLowerCase().includes('exception');
        let badgeColor = 'text-cyan-400 bg-cyan-400/10 border-cyan-400/20';
        if (orig.includes('LUFFY')) badgeColor = 'text-primary bg-primary/10 border-primary/20';
        else if (orig.includes('ZORO')) badgeColor = 'text-secondary bg-secondary/10 border-secondary/20';
        else if (orig.includes('SANJI')) badgeColor = 'text-amber-400 bg-amber-400/10 border-amber-400/20';
        else if (orig.includes('ROBIN')) badgeColor = 'text-purple-400 bg-purple-400/10 border-purple-400/20';
        else if (orig.includes('NAMI')) badgeColor = 'text-yellow-400 bg-yellow-400/10 border-yellow-400/20';

        return `
            <div class="flex items-start gap-2 py-1 border-b border-outline-variant/10 text-xs">
                <span class="px-1.5 py-0.2 rounded border text-[9px] font-bold font-mono shrink-0 ${badgeColor}">[${orig}]</span>
                <span class="text-on-surface/90 font-mono break-all leading-relaxed ${isErr ? 'text-error font-semibold' : ''}">${texto}</span>
            </div>
        `;
    }).join('');
}

function inspeccionarEquipo(equipoId) {
    const eq = cachedFleet.find(x => x.id === equipoId);
    if (!eq) return;

    const isLocal = eq.id === 'local-hq';
    const title = document.getElementById('inspect-modal-title');
    const sub = document.getElementById('inspect-modal-sub');
    const ping = document.getElementById('inspect-modal-ping');
    const body = document.getElementById('inspect-modal-body');

    if (title) title.innerText = isLocal ? 'Tripulación IA' : (eq.nombre || 'Equipo');
    if (sub) sub.innerText = isLocal ? 'Supervisión en vivo de agentes y sistema' : `${eq.tipo || 'Nodo'} • ${eq.ip || '0.0.0.0'}`;
    if (ping) ping.innerText = eq.ultimo_ping_relativo || 'Plugin: En vivo';

    if (body) {
        body.innerHTML = `
            <div class="grid grid-cols-3 gap-3 text-center">
                <div class="p-3 rounded-xl bg-surface-container-low border border-outline-variant/30 flex flex-col justify-between">
                    <span class="text-[10px] text-on-surface-variant uppercase font-mono font-semibold">Consumo en Dólares</span>
                    <div class="text-base font-bold font-mono text-secondary my-1">$${Number(eq.costo || 0).toFixed(4)}</div>
                    <span class="text-[10px] text-on-surface-variant/70 font-mono">${Number(eq.tokens || 0).toLocaleString()} tokens</span>
                </div>
                <div class="p-3 rounded-xl bg-surface-container-low border border-outline-variant/30 flex flex-col justify-between">
                    <span class="text-[10px] text-on-surface-variant uppercase font-mono font-semibold">Uso de CPU</span>
                    <div class="text-base font-bold font-mono text-cyan-400 my-1">${eq.cpu || 0}%</div>
                    <span class="text-[10px] text-on-surface-variant/70 font-mono">Carga de procesador</span>
                </div>
                <div class="p-3 rounded-xl bg-surface-container-low border border-outline-variant/30 flex flex-col justify-between">
                    <span class="text-[10px] text-on-surface-variant uppercase font-mono font-semibold">Uso de Memoria</span>
                    <div class="text-base font-bold font-mono text-purple-400 my-1">${eq.ram || 0}%</div>
                    <span class="text-[10px] text-on-surface-variant/70 font-mono">RAM del host</span>
                </div>
            </div>

            ${eq.error_critico ? `
                <div class="p-3.5 rounded-xl bg-error/15 border border-error/50 flex flex-col gap-1 text-error">
                    <span class="font-bold flex items-center gap-1.5"><span class="material-symbols-outlined text-[16px]">error</span>Traza de Fallo Activo:</span>
                    <p class="font-mono text-xs bg-black/40 p-2.5 rounded-lg text-error/90 leading-relaxed break-words">${eq.error_critico}</p>
                </div>
            ` : `
                <div class="p-3 rounded-xl bg-secondary/10 border border-secondary/30 flex items-center gap-2 text-secondary">
                    <span class="material-symbols-outlined text-[18px]">verified</span>
                    <span>El equipo no presenta anomalías ni registros de fallos críticos.</span>
                </div>
            `}

            <!-- Deep Log Stream Viewer -->
            <div class="p-3.5 rounded-xl bg-[#080812] border border-outline-variant/40 flex flex-col gap-2">
                <div class="flex items-center justify-between pb-1.5 border-b border-outline-variant/20">
                    <div class="flex items-center gap-2">
                        <span class="material-symbols-outlined text-[16px] text-cyan-400">terminal</span>
                        <span class="font-bold text-on-surface text-xs">Registros de Actividad & Logs Recientes:</span>
                    </div>
                    <span class="text-[10px] font-mono text-on-surface-variant/60">Auditoría en tiempo real</span>
                </div>
                <div class="max-h-60 overflow-y-auto font-mono text-[11px] leading-relaxed flex flex-col gap-1 pr-1 bg-[#05050d] p-2.5 rounded-xl border border-outline-variant/20">
                    ${renderInspectLogs(eq)}
                </div>
            </div>
        `;
    }

    toggleInspectModal(true);
}

async function simularEquiposFlota() {
    try {
        const res = await fetch('/api/telemetria/simular', { method: 'POST' });
        const data = await res.json();
        console.log('Simulación:', data);
    } catch(e) {
        console.error('Error simulando flota:', e);
    }
}

async function eliminarEquipoRemoto(equipoId) {
    if (!confirm('¿Deseas retirar este equipo del panel de monitoreo?')) return;
    try {
        await fetch(`/api/telemetria/eliminar/${equipoId}`, { method: 'DELETE' });
    } catch(e) {
        console.error('Error eliminando equipo:', e);
    }
}

// ----------------- SISTEMA DE CONFIGURACIÓN DEL SISTEMA -----------------
let cachedConfig = null;

function openConfigView() {
    switchCanvasView('configuracion');
    try {
        localStorage.setItem('activeDashboardView', 'configuracion');
    } catch(e) {}

    // Deselect main nav items
    const container = document.getElementById('nav-container');
    if (container) {
        container.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
    }

    // Highlight footer config button with sidebar primary magenta neon color
    const cfgBtn = document.getElementById('footer-btn-config');
    const iconBox = document.getElementById('footer-config-icon-box');
    const textEl = document.getElementById('footer-config-text');
    if (cfgBtn) {
        cfgBtn.className = "w-full !py-2.5 !text-xs text-white bg-primary/15 border border-primary/50 shadow-[0_0_15px_rgba(255,45,120,0.35)] flex items-center gap-2.5 px-3 rounded-xl transition-all cursor-pointer select-none";
    }
    if (iconBox) {
        iconBox.className = "w-7 h-7 flex items-center justify-center rounded-lg bg-primary border border-primary text-white shadow-[0_0_12px_rgba(255,45,120,0.65)] transition-all shrink-0";
    }
    if (textEl) {
        textEl.className = "font-bold text-white drop-shadow-[0_0_8px_rgba(255,45,120,0.4)]";
    }

    // Update telemetry URL dynamically based on host
    const teleUrl = document.getElementById('cfg-telemetry-url-text');
    if (teleUrl) {
        teleUrl.innerText = `http://${window.location.host}/api/telemetria/reportar`;
    }

    loadConfigData();
}
window.openConfigView = openConfigView;

function openContactModal(show = true) {
    const modal = document.getElementById('contact-modal');
    if (!modal) return;
    if (show) {
        modal.classList.remove('hidden');
    } else {
        modal.classList.add('hidden');
    }
}
window.openContactModal = openContactModal;

function showConfigToast(msg, isError = false) {
    const toast = document.getElementById('config-status-toast');
    const msgEl = document.getElementById('config-status-toast-msg');
    const content = document.getElementById('config-status-toast-content');
    if (!toast || !msgEl || !content) return;

    msgEl.innerText = msg;
    if (isError) {
        toast.className = 'p-3 rounded-xl border border-error/50 bg-error/15 text-error text-xs font-semibold flex items-center justify-between gap-3 shadow-lg transition-all duration-300 animate-pulse';
        const icon = content.querySelector('.material-symbols-outlined');
        if (icon) icon.innerText = 'error';
    } else {
        toast.className = 'p-3 rounded-xl border border-emerald-400/50 bg-emerald-400/15 text-emerald-400 text-xs font-semibold flex items-center justify-between gap-3 shadow-lg transition-all duration-300';
        const icon = content.querySelector('.material-symbols-outlined');
        if (icon) icon.innerText = 'check_circle';
    }
    toast.classList.remove('hidden');

    setTimeout(() => {
        if (toast) toast.classList.add('hidden');
    }, 5000);
}

function toggleKeyVisibility(inputId) {
    const input = document.getElementById(inputId);
    if (!input) return;
    const isPass = input.type === 'password';
    input.type = isPass ? 'text' : 'password';
    const btn = input.nextElementSibling;
    if (btn) {
        const icon = btn.querySelector('.material-symbols-outlined');
        if (icon) icon.innerText = isPass ? 'visibility_off' : 'visibility';
    }
}
window.toggleKeyVisibility = toggleKeyVisibility;

// Logos e Iconos Vectoriales Oficiales (SVGs auténticos de cada marca)
const PROVIDER_SVGS = {
    deepseek: `<svg class="w-4 h-4 shrink-0" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M12 2C6.48 2 2 6.48 2 12c0 2.85 1.2 5.42 3.12 7.24L4 21l3.2-.88A9.95 9.95 0 0012 22c5.52 0 10-4.48 10-10S17.52 2 12 2zm1 14.5c-2.48 0-4.5-1.57-4.5-3.5S10.52 9.5 13 9.5s4.5 1.57 4.5 3.5-2.02 3.5-4.5 3.5zm2.5-4.5a1 1 0 11-2 0 1 1 0 012 0z" fill="#0066FF"/>
        <path d="M7 11.5c.8-1.5 2.5-2.5 4.5-2.5 1.5 0 2.8.6 3.7 1.5.3-.2.8-.5 1.3-.6-1.2-1.4-3-2.4-5-2.4-3.3 0-6 2.3-6.5 5.5.3-.2.7-.4 1.1-.5.3-.4.6-.7.9-1z" fill="#38BDF8"/>
    </svg>`,
    groq: `<svg class="w-4 h-4 shrink-0" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect width="24" height="24" rx="5" fill="#F55036"/>
        <path d="M12.5 6.5C8.9 6.5 6.5 9 6.5 12.3c0 3.3 2.4 5.8 6 5.8 2.2 0 4-1 4.9-2.7h-2.5c-.6.8-1.4 1.2-2.4 1.2-1.9 0-3.3-1.4-3.4-3.3h8.6c.1-.4.1-.7.1-1 0-3.4-2.2-5.8-5.3-5.8zm-3.3 4.8c.2-1.7 1.4-2.9 3.2-2.9 1.8 0 3 1.2 3.1 2.9H9.2z" fill="#FFFFFF"/>
    </svg>`,
    qwen: `<svg class="w-4 h-4 shrink-0" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M12 2L3 7v10l9 5 9-5V7l-9-5zm0 3.2l6 3.3v6.8l-6 3.3-6-3.3v-6.8l6-3.3z" fill="#615CED"/>
        <path d="M12 7.5l4 2.2v4.5l-4 2.2-4-2.2V9.7l4-2.2z" fill="#00C9A7"/>
    </svg>`,
    openrouter: `<svg class="w-4 h-4 shrink-0" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="#3B82F6" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>`,
    mistral: `<svg class="w-4 h-4 shrink-0" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M4 4h3.2v3.2H4zm12.8 0H20v3.2h-3.2zm-9.6 4.8h3.2v3.2H7.2zm6.4 0h3.2v3.2h-3.2zm-3.2 4.8h3.2v3.2h-3.2zm-3.2 4.8h3.2v3.2H7.2zm6.4 0h3.2v3.2h-3.2z" fill="#FA520F"/>
    </svg>`,
    ollama: `<svg class="w-4 h-4 shrink-0" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M12 2a4 4 0 00-4 4v2H7a3 3 0 00-3 3v5a4 4 0 004 4h1v2h2v-2h2v2h2v-2h1a4 4 0 004-4v-5a3 3 0 00-3-3h-1V6a4 4 0 00-4-4zm-2 5a1 1 0 110-2 1 1 0 010 2zm4 0a1 1 0 110-2 1 1 0 010 2z" fill="#FFFFFF"/>
    </svg>`,
    openai: `<svg class="w-4 h-4 shrink-0" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M22.28 9.37a5.98 5.98 0 00-.52-4.95 6.08 6.08 0 00-6.42-2.74A6.08 6.08 0 0010.5 0a6.04 6.04 0 00-5.75 4.13 6.02 6.02 0 00-3.9 2.84 6.08 6.08 0 00.7 6.94 6.03 6.03 0 00.52 4.95 6.08 6.08 0 006.42 2.74A6.08 6.08 0 0013.5 24a6.04 6.04 0 005.75-4.13 6.02 6.02 0 003.9-2.84 6.08 6.08 0 00-.87-7.66zm-7.6 12.75a4.48 4.48 0 01-2.92-1.07l.15-.09 4.8-2.77a.8.8 0 00.4-.69v-6.78l2.03 1.17a.08.08 0 01.04.06v5.7a4.5 4.5 0 01-4.5 4.47zm-10.7-3.9a4.5 4.5 0 01-.54-3.1 4.54 4.54 0 011.6-2.58l.15.09 4.8 2.77a.8.8 0 00.8 0l5.87-3.39v2.34a.08.08 0 01-.03.07l-4.94 2.85a4.5 4.5 0 01-6.1-1.05zm-1.8-10.72a4.5 4.5 0 012.38-2.03 4.53 4.53 0 013.04.31v.17l-4.8 2.77a.8.8 0 00-.4.69v6.78l-2.03-1.17a.08.08 0 01-.04-.07v-5.7a4.5 4.5 0 011.85-1.75zm15.13 3.32l-5.87 3.39v-2.35a.08.08 0 01.03-.07l4.94-2.85a4.5 4.5 0 016.1 1.05 4.5 4.5 0 01.54 3.1 4.54 4.54 0 01-1.6 2.58l-.14-.09-4.8-2.77a.8.8 0 00-.8 0zm2.97-2.39v-.17l4.8-2.77a.8.8 0 00.4-.69v-6.78l2.03 1.17a.08.08 0 01.04.07v5.7a4.5 4.5 0 01-2.38 2.03 4.53 4.53 0 01-3.04-.31l-1.85 1.07zm-10.5 4.14l2.67-1.54 2.67 1.54v3.08l-2.67 1.54-2.67-1.54v-3.08z" fill="#10A37F"/>
    </svg>`,
    gemini: `<svg class="w-4 h-4 shrink-0" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M12 24C12 17.373 6.627 12 0 12C6.627 12 12 6.627 12 0C12 6.627 17.373 12 24 12C17.373 12 12 17.373 12 24Z" fill="url(#gemini-grad-svg)"/>
        <defs>
            <linearGradient id="gemini-grad-svg" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#4E82EE"/>
                <stop offset="50%" stop-color="#9B72CB"/>
                <stop offset="100%" stop-color="#D96570"/>
            </linearGradient>
        </defs>
    </svg>`,
    anthropic: `<svg class="w-4 h-4 shrink-0" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M14.5 3h-5l-6.5 18h4.5l1.3-3.8h6.4l1.3 3.8h4.5L14.5 3zm-4.3 10.7l2.3-6.8 2.3 6.8h-4.6z" fill="#D97757"/>
    </svg>`,
    xai: `<svg class="w-4 h-4 shrink-0" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" fill="#FFFFFF"/>
    </svg>`,
    custom: `<svg class="w-4 h-4 shrink-0" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M12 15a3 3 0 100-6 3 3 0 000 6z" fill="#22D3EE"/>
        <path fill-rule="evenodd" clip-rule="evenodd" d="M9.9 2h4.2l.6 2.3c.5.2 1 .5 1.5.8l2.2-1 3 3-1 2.2c.3.5.6 1 .8 1.5l2.3.6v4.2l-2.3.6c-.2.5-.5 1-.8 1.5l1 2.2-3 3-2.2-1c-.5.3-1 .6-1.5.8l-.6 2.3H9.9l-.6-2.3c-.5-.2-1-.5-1.5-.8l-2.2 1-3-3 1-2.2c-.3-.5-.6-1-.8-1.5L1.5 14.1V9.9l2.3-.6c.2-.5.5-1 .8-1.5l-1-2.2 3-3 2.2 1c.5-.3 1-.6 1.5-.8L9.9 2zm2.1 15a5 5 0 100-10 5 5 0 000 10z" fill="#22D3EE"/>
    </svg>`
};

// Catálogo de proveedores con NOMBRES PUROS (sin nombres de modelos)
const PROVIDER_METADATA = {
    deepseek: {
        name: 'DeepSeek',
        defaultUrl: 'https://api.deepseek.com/v1',
        defaultModel: 'deepseek-chat'
    },
    groq: {
        name: 'Groq',
        defaultUrl: 'https://api.groq.com/openai/v1',
        defaultModel: 'llama-3.3-70b-versatile'
    },
    qwen: {
        name: 'Qwen',
        defaultUrl: 'https://dashscope-intl.aliyuncs.com/compatible-mode/v1',
        defaultModel: 'qwen-plus'
    },
    openrouter: {
        name: 'OpenRouter',
        defaultUrl: 'https://openrouter.ai/api/v1',
        defaultModel: 'anthropic/claude-3.7-sonnet'
    },
    mistral: {
        name: 'Mistral AI',
        defaultUrl: 'https://api.mistral.ai/v1',
        defaultModel: 'mistral-large-latest'
    },
    ollama: {
        name: 'Ollama',
        defaultUrl: 'http://localhost:11434/v1',
        defaultModel: 'llama3'
    },
    openai: {
        name: 'OpenAI',
        defaultUrl: 'https://api.openai.com/v1',
        defaultModel: 'gpt-4o'
    },
    gemini: {
        name: 'Google Gemini',
        defaultUrl: '',
        defaultModel: 'gemini-2.5-pro'
    },
    anthropic: {
        name: 'Anthropic Claude',
        defaultUrl: '',
        defaultModel: 'claude-3-7-sonnet'
    },
    xai: {
        name: 'xAI',
        defaultUrl: 'https://api.x.ai/v1',
        defaultModel: 'grok-2-latest'
    },
    custom: {
        name: 'Personalizado',
        defaultUrl: '',
        defaultModel: ''
    }
};

let activeProviders = ['deepseek'];
let cachedConfigKeys = {};
let cachedConfigBaseUrls = {};

function getStoredProviders() {
    try {
        const stored = localStorage.getItem('tripulacion_active_providers');
        if (stored) {
            const parsed = JSON.parse(stored);
            if (Array.isArray(parsed) && parsed.length > 0) {
                return parsed;
            }
        }
    } catch (e) {}
    return ['deepseek'];
}

function saveStoredProviders(list) {
    try {
        localStorage.setItem('tripulacion_active_providers', JSON.stringify(list));
    } catch (e) {}
}

function renderProvidersList(keys = {}, baseUrls = {}) {
    const container = document.getElementById('providers-list-container');
    if (!container) return;

    if (!activeProviders || activeProviders.length === 0) {
        container.innerHTML = `
            <div class="p-6 rounded-xl border border-dashed border-outline-variant/30 text-center text-xs text-on-surface-variant flex flex-col items-center gap-2.5">
                <span class="material-symbols-outlined text-3xl text-cyan-400/60">hub</span>
                <span>No hay proveedores configurados en este momento.</span>
                <button onclick="abrirModalAgregarProveedor()" type="button" class="text-cyan-400 font-bold hover:underline cursor-pointer">
                    + Agregar un Proveedor de IA
                </button>
            </div>
        `;
        return;
    }

    container.innerHTML = activeProviders.map(provId => {
        const meta = PROVIDER_METADATA[provId] || {
            name: provId.toUpperCase(),
            defaultUrl: '',
            defaultModel: ''
        };
        const svgIcon = PROVIDER_SVGS[provId] || '<span class="material-symbols-outlined text-[16px] text-cyan-400">hub</span>';
        const valKey = keys[provId] !== undefined ? keys[provId] : (cachedConfigKeys[provId] || '');
        const valUrl = baseUrls[provId] !== undefined ? baseUrls[provId] : (cachedConfigBaseUrls[provId] || meta.defaultUrl || '');
        const hasKey = Boolean(valKey && String(valKey).trim().length > 0);

        return `
            <div class="p-3.5 rounded-xl bg-surface-container-low/70 border border-outline-variant/25 flex flex-col gap-2.5 transition-all" id="provider-card-${provId}">
                <div class="flex items-center justify-between">
                    <div class="flex items-center gap-2.5">
                        <div class="w-7 h-7 rounded-lg bg-surface-container-highest flex items-center justify-center p-1 border border-outline-variant/30 shrink-0 shadow-sm">
                            ${svgIcon}
                        </div>
                        <div class="flex items-center gap-2">
                            <span class="text-xs font-bold text-on-surface font-mono">${meta.name}</span>
                            <span class="text-[9px] font-mono px-1.5 py-0.2 rounded bg-surface-container-highest text-on-surface-variant/80 uppercase">${provId}</span>
                        </div>
                    </div>
                    <div class="flex items-center gap-2">
                        <span id="status-badge-${provId}" class="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full ${hasKey ? 'bg-emerald-400/10 text-emerald-400 border border-emerald-400/30' : 'bg-surface-container-high text-on-surface-variant border border-outline-variant/40'}">
                            ${hasKey ? 'CONECTADA' : 'SIN CLAVE'}
                        </span>
                        <button onclick="abrirModalConfirmarEliminarProveedor('${provId}')" type="button" title="Retirar este proveedor" class="p-1 text-on-surface-variant hover:text-error rounded-lg hover:bg-error/10 transition-colors cursor-pointer">
                            <span class="material-symbols-outlined text-[16px]">delete</span>
                        </button>
                    </div>
                </div>

                <div class="flex flex-col gap-1">
                    <label class="text-[10px] font-mono text-on-surface-variant/70">API Key / Clave secreta (.env):</label>
                    <div class="relative flex items-center">
                        <input id="cfg-key-${provId}" type="password" value="${String(valKey).replace(/"/g, '&quot;')}" placeholder="sk-..." class="w-full bg-surface-container-highest/60 border border-outline-variant/40 rounded-xl py-1.5 pl-3 pr-10 text-xs font-mono text-on-surface placeholder:text-on-surface-variant/40 focus:outline-none focus:border-cyan-400/60 transition-colors">
                        <button onclick="toggleKeyVisibility('cfg-key-${provId}')" type="button" class="absolute right-2 text-on-surface-variant hover:text-on-surface p-1 transition-colors cursor-pointer" title="Mostrar u ocultar clave">
                            <span class="material-symbols-outlined text-[17px]">visibility</span>
                        </button>
                    </div>
                </div>

                <div class="flex flex-col gap-1">
                    <label class="text-[10px] font-mono text-on-surface-variant/70">URL Base del Endpoint (Opcional):</label>
                    <input id="cfg-url-${provId}" type="text" value="${String(valUrl).replace(/"/g, '&quot;')}" placeholder="${meta.defaultUrl || 'https://api.openai.com/v1'}" class="w-full bg-surface-container-highest/60 border border-outline-variant/40 rounded-xl py-1.5 px-3 text-xs font-mono text-on-surface placeholder:text-on-surface-variant/40 focus:outline-none focus:border-cyan-400/60 transition-colors">
                </div>
            </div>
        `;
    }).join('');
}

// Control del Menú Desplegable con Logos Vectoriales Oficiales
function renderModalDropdownOptions() {
    const menu = document.getElementById('modal-prov-dropdown-menu');
    if (!menu) return;

    const list = Object.keys(PROVIDER_METADATA);
    menu.innerHTML = list.map(id => {
        const m = PROVIDER_METADATA[id];
        const svg = PROVIDER_SVGS[id] || '<span class="material-symbols-outlined text-[16px]">hub</span>';
        return `
            <div onclick="seleccionarOpcionProveedor('${id}')" class="px-3 py-2 hover:bg-cyan-400/10 hover:text-cyan-400 flex items-center gap-2.5 cursor-pointer transition-colors text-xs font-mono text-on-surface">
                <div class="w-5 h-5 rounded-md bg-surface-container-high/70 flex items-center justify-center p-0.5 border border-outline-variant/30 shrink-0">
                    ${svg}
                </div>
                <span class="font-bold">${m.name}</span>
            </div>
        `;
    }).join('');
}

function toggleDropdownProveedores(forceOpen) {
    const menu = document.getElementById('modal-prov-dropdown-menu');
    const arrow = document.getElementById('modal-prov-dropdown-arrow');
    if (!menu) return;

    const shouldOpen = forceOpen !== undefined ? forceOpen : menu.classList.contains('hidden');
    if (shouldOpen) {
        menu.classList.remove('hidden');
        if (arrow) arrow.style.transform = 'rotate(180deg)';
    } else {
        menu.classList.add('hidden');
        if (arrow) arrow.style.transform = 'rotate(0deg)';
    }
}
window.toggleDropdownProveedores = toggleDropdownProveedores;

document.addEventListener('click', (e) => {
    const btn = document.getElementById('modal-prov-dropdown-btn');
    const menu = document.getElementById('modal-prov-dropdown-menu');
    if (menu && !menu.classList.contains('hidden')) {
        if (btn && !btn.contains(e.target) && !menu.contains(e.target)) {
            toggleDropdownProveedores(false);
        }
    }
});

function seleccionarOpcionProveedor(provId) {
    const input = document.getElementById('modal-select-provider');
    const display = document.getElementById('modal-prov-selected-display');
    if (input) input.value = provId;

    const meta = PROVIDER_METADATA[provId] || { name: provId.toUpperCase() };
    const svg = PROVIDER_SVGS[provId] || '<span class="material-symbols-outlined text-[16px]">hub</span>';

    if (display) {
        display.innerHTML = `
            <div class="w-5 h-5 rounded-md bg-surface-container-high/70 flex items-center justify-center p-0.5 border border-outline-variant/30 shrink-0">
                ${svg}
            </div>
            <span class="font-bold text-xs text-on-surface font-mono">${meta.name}</span>
        `;
    }

    toggleDropdownProveedores(false);
    alCambiarProveedorSelect(provId);
}
window.seleccionarOpcionProveedor = seleccionarOpcionProveedor;

function abrirModalAgregarProveedor() {
    const modal = document.getElementById('modal-add-provider');
    if (!modal) return;
    modal.classList.remove('hidden');
    
    renderModalDropdownOptions();
    seleccionarOpcionProveedor('groq');

    const keyInput = document.getElementById('modal-prov-key');
    if (keyInput) setTimeout(() => keyInput.focus(), 100);
}
window.abrirModalAgregarProveedor = abrirModalAgregarProveedor;

function cerrarModalAgregarProveedor() {
    const modal = document.getElementById('modal-add-provider');
    if (modal) modal.classList.add('hidden');
    toggleDropdownProveedores(false);
}
window.cerrarModalAgregarProveedor = cerrarModalAgregarProveedor;

function alCambiarProveedorSelect(provId) {
    const customGroup = document.getElementById('modal-custom-id-group');
    const customInput = document.getElementById('modal-prov-custom-id');
    const keyInput = document.getElementById('modal-prov-key');
    const urlInput = document.getElementById('modal-prov-url');

    if (provId === 'custom') {
        if (customGroup) customGroup.classList.remove('hidden');
        if (customInput) {
            customInput.value = '';
            customInput.focus();
        }
        if (keyInput) keyInput.value = '';
        if (urlInput) urlInput.value = '';
    } else {
        if (customGroup) customGroup.classList.add('hidden');
        const meta = PROVIDER_METADATA[provId] || {};
        if (keyInput) keyInput.value = cachedConfigKeys[provId] || '';
        if (urlInput) urlInput.value = cachedConfigBaseUrls[provId] || meta.defaultUrl || '';
    }
}
window.alCambiarProveedorSelect = alCambiarProveedorSelect;

function agregarModeloASelects(modelo) {
    if (!modelo) return;
    const selects = [
        'cfg-default-model',
        'cfg-model-luffy',
        'cfg-model-zoro',
        'cfg-model-sanji',
        'cfg-model-robin',
        'cfg-model-nami'
    ];
    selects.forEach(sId => {
        const sel = document.getElementById(sId);
        if (sel) {
            const exists = Array.from(sel.options).some(o => o.value === modelo);
            if (!exists) {
                const opt = document.createElement('option');
                opt.value = modelo;
                opt.innerText = `${modelo} (Agregado)`;
                sel.appendChild(opt);
            }
        }
    });
}

async function guardarNuevoProveedorModal() {
    const selEl = document.getElementById('modal-select-provider');
    const customIdEl = document.getElementById('modal-prov-custom-id');
    const keyEl = document.getElementById('modal-prov-key');
    const urlEl = document.getElementById('modal-prov-url');
    const saveBtn = document.getElementById('btn-modal-save-provider');

    let provId = selEl ? selEl.value.trim().toLowerCase() : 'groq';
    if (provId === 'custom') {
        const customId = (customIdEl ? customIdEl.value.trim() : '').toLowerCase().replace(/[^a-z0-9_-]/g, '');
        if (!customId) {
            showConfigToast('Debes ingresar un nombre o identificador para el proveedor personalizado.', true);
            if (customIdEl) customIdEl.focus();
            return;
        }
        provId = customId;
    }

    const key = keyEl ? keyEl.value.trim() : '';
    const url = urlEl ? urlEl.value.trim() : '';

    if (!key && provId !== 'ollama') {
        showConfigToast('Ingresa la API Key para conectar este proveedor.', true);
        if (keyEl) keyEl.focus();
        return;
    }

    const meta = PROVIDER_METADATA[provId] || {
        name: provId.toUpperCase(),
        sub: 'Proveedor compatible OpenAI / Local',
        icon: '⚙️',
        defaultUrl: url,
        defaultModel: ''
    };

    if (saveBtn) {
        saveBtn.disabled = true;
        saveBtn.innerHTML = '<span class="material-symbols-outlined text-[16px] animate-spin">sync</span><span>Guardando en .env...</span>';
    }

    try {
        const payloadKeys = { ...cachedConfigKeys };
        const payloadUrls = { ...cachedConfigBaseUrls };

        activeProviders.forEach(p => {
            const k = document.getElementById(`cfg-key-${p}`);
            const u = document.getElementById(`cfg-url-${p}`);
            if (k) payloadKeys[p] = k.value.trim();
            if (u && u.value.trim()) payloadUrls[p] = u.value.trim();
        });

        payloadKeys[provId] = key;
        if (url) payloadUrls[provId] = url;

        const getVal = id => {
            const el = document.getElementById(id);
            return el ? el.value.trim() : '';
        };

        const payload = {
            keys: payloadKeys,
            base_urls: payloadUrls,
            default_model: getVal('cfg-default-model') || 'deepseek-chat',
            default_provider: activeProviders.includes('deepseek') ? 'deepseek' : provId,
            modelos: {
                luffy: getVal('cfg-model-luffy') || 'deepseek-chat',
                zoro: getVal('cfg-model-zoro') || 'deepseek-chat',
                sanji: getVal('cfg-model-sanji') || 'deepseek-chat',
                robin: getVal('cfg-model-robin') || 'deepseek-chat',
                nami: getVal('cfg-model-nami') || 'deepseek-chat'
            },
            presupuesto_maximo: parseFloat(getVal('cfg-presupuesto-max')) || 10.0,
            telegram: {
                token: getVal('cfg-telegram-token'),
                chat_id: getVal('cfg-telegram-chatid')
            }
        };

        const res = await fetch('/api/config/guardar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        if (data.status === 'ok') {
            if (!activeProviders.includes(provId)) {
                activeProviders.push(provId);
                saveStoredProviders(activeProviders);
            }
            cachedConfigKeys[provId] = key;
            if (url) cachedConfigBaseUrls[provId] = url;

            if (meta.defaultModel) {
                agregarModeloASelects(meta.defaultModel);
            }

            renderProvidersList(cachedConfigKeys, cachedConfigBaseUrls);
            cerrarModalAgregarProveedor();
            showConfigToast(`¡Proveedor ${meta.name || provId.toUpperCase()} guardado exitosamente en .env!`);
        } else {
            showConfigToast(data.message || 'Error guardando en .env', true);
        }
    } catch (e) {
        console.error('Error guardando proveedor en .env:', e);
        showConfigToast('Error al comunicar con el servidor para guardar.', true);
    } finally {
        if (saveBtn) {
            saveBtn.disabled = false;
            saveBtn.innerHTML = '<span class="material-symbols-outlined text-[16px]">save</span><span>Guardar Proveedor en .env</span>';
        }
    }
}
window.guardarNuevoProveedorModal = guardarNuevoProveedorModal;
window.confirmarAgregarProveedor = guardarNuevoProveedorModal;

let pendingDeleteProviderId = null;

function abrirModalConfirmarEliminarProveedor(provId) {
    pendingDeleteProviderId = provId;
    const modal = document.getElementById('modal-confirm-delete-provider');
    if (!modal) return;

    const meta = PROVIDER_METADATA[provId] || { name: provId.toUpperCase() };
    const titleEl = document.getElementById('modal-delete-prov-title');

    if (titleEl) {
        titleEl.innerText = meta.name;
    }

    modal.classList.remove('hidden');
}
window.abrirModalConfirmarEliminarProveedor = abrirModalConfirmarEliminarProveedor;

function cerrarModalConfirmarEliminarProveedor() {
    pendingDeleteProviderId = null;
    const modal = document.getElementById('modal-confirm-delete-provider');
    if (modal) {
        modal.classList.add('hidden');
    }
}
window.cerrarModalConfirmarEliminarProveedor = cerrarModalConfirmarEliminarProveedor;

async function ejecutarEliminarProveedor() {
    const provId = pendingDeleteProviderId;
    if (!provId) {
        cerrarModalConfirmarEliminarProveedor();
        return;
    }

    const btn = document.getElementById('btn-modal-confirm-delete');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="material-symbols-outlined text-[16px] animate-spin">sync</span><span>Eliminando...</span>';
    }

    try {
        await fetch(`/api/config/env/${provId}`, { method: 'DELETE' });
    } catch (e) {
        console.warn('Error llamando delete backend:', e);
    }

    delete cachedConfigKeys[provId];
    delete cachedConfigBaseUrls[provId];

    activeProviders = activeProviders.filter(p => p !== provId);
    saveStoredProviders(activeProviders);

    renderProvidersList(cachedConfigKeys, cachedConfigBaseUrls);
    cerrarModalConfirmarEliminarProveedor();

    const meta = PROVIDER_METADATA[provId] || { name: provId };
    showConfigToast(`Proveedor ${meta.name} eliminado.`);

    if (btn) {
        btn.disabled = false;
        btn.innerHTML = '<span class="material-symbols-outlined text-[16px]">delete</span><span>Eliminar</span>';
    }
}
window.ejecutarEliminarProveedor = ejecutarEliminarProveedor;

// Mantener compatibilidad hacia atrás
function eliminarProveedorConfig(provId) {
    abrirModalConfirmarEliminarProveedor(provId);
}
window.eliminarProveedorConfig = eliminarProveedorConfig;

async function loadConfigData() {
    try {
        const res = await fetch('/api/config/env');
        if (!res.ok) throw new Error('Error al consultar configuración');
        const data = await res.json();
        cachedConfig = data;

        const keys = data.keys || {};
        const baseUrls = data.base_urls || {};
        cachedConfigKeys = { ...keys };
        cachedConfigBaseUrls = { ...baseUrls };

        // Providers list initialization
        activeProviders = getStoredProviders();
        if (!activeProviders.includes('deepseek')) {
            activeProviders.unshift('deepseek');
        }

        renderProvidersList(cachedConfigKeys, cachedConfigBaseUrls);

        const setVal = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.value = val || '';
        };

        // Default Model
        if (data.default_model) {
            const defSel = document.getElementById('cfg-default-model');
            if (defSel) {
                const hasOption = Array.from(defSel.options).some(o => o.value === data.default_model);
                if (!hasOption) {
                    const opt = document.createElement('option');
                    opt.value = data.default_model;
                    opt.innerText = data.default_model;
                    defSel.appendChild(opt);
                }
                defSel.value = data.default_model;
            }
        }

        // Agent Models
        const mods = data.modelos || {};
        const agents = ['luffy', 'zoro', 'sanji', 'robin', 'nami'];
        agents.forEach(ag => {
            const agMod = mods[ag] || data.default_model || 'deepseek-chat';
            const selectEl = document.getElementById(`cfg-model-${ag}`);
            if (selectEl) {
                const hasOption = Array.from(selectEl.options).some(o => o.value === agMod);
                if (!hasOption && agMod) {
                    const opt = document.createElement('option');
                    opt.value = agMod;
                    opt.innerText = agMod;
                    selectEl.appendChild(opt);
                }
                selectEl.value = agMod;
            }
        });

        // Presupuesto
        if (data.presupuesto_maximo !== undefined) {
            setVal('cfg-presupuesto-max', data.presupuesto_maximo);
            const presVal = parseFloat(data.presupuesto_maximo) || 10.0;
            const elPresBadge = document.getElementById('cfg-presupuesto-consumo-badge');
            const curCost = (window.cachedCostos && typeof window.cachedCostos.costo === 'number') ? window.cachedCostos.costo : 0.0;
            if (elPresBadge) {
                elPresBadge.innerText = `$${curCost.toFixed(2)} / $${presVal.toFixed(2)} USD`;
            }
        }

        // Telegram
        if (data.telegram) {
            setVal('cfg-telegram-token', data.telegram.token || '');
            setVal('cfg-telegram-chatid', data.telegram.chat_id || '');
        }

    } catch (e) {
        console.error('Error cargando configuración:', e);
        showConfigToast('No se pudo cargar la configuración del sistema.', true);
    }
}
window.loadConfigData = loadConfigData;

async function guardarTodaLaConfiguracion() {
    const saveBtn = document.getElementById('btn-save-all-config');
    if (saveBtn) {
        saveBtn.disabled = true;
        saveBtn.innerHTML = '<span class="material-symbols-outlined text-[16px] animate-spin">sync</span><span>Guardando...</span>';
    }

    try {
        const getVal = id => {
            const el = document.getElementById(id);
            return el ? el.value.trim() : '';
        };

        const keys = {};
        const base_urls = {};
        activeProviders.forEach(provId => {
            const kEl = document.getElementById(`cfg-key-${provId}`);
            const uEl = document.getElementById(`cfg-url-${provId}`);
            if (kEl) {
                keys[provId] = kEl.value.trim();
                cachedConfigKeys[provId] = keys[provId];
            }
            if (uEl) {
                const urlVal = uEl.value.trim();
                if (urlVal) {
                    base_urls[provId] = urlVal;
                    cachedConfigBaseUrls[provId] = urlVal;
                }
            }
        });

        const payload = {
            keys,
            base_urls,
            default_model: getVal('cfg-default-model') || 'deepseek-chat',
            default_provider: activeProviders.includes('deepseek') ? 'deepseek' : (activeProviders[0] || 'deepseek'),
            modelos: {
                luffy: getVal('cfg-model-luffy') || 'deepseek-chat',
                zoro: getVal('cfg-model-zoro') || 'deepseek-chat',
                sanji: getVal('cfg-model-sanji') || 'deepseek-chat',
                robin: getVal('cfg-model-robin') || 'deepseek-chat',
                nami: getVal('cfg-model-nami') || 'deepseek-chat'
            },
            presupuesto_maximo: parseFloat(getVal('cfg-presupuesto-max')) || 10.0,
            telegram: {
                token: getVal('cfg-telegram-token'),
                chat_id: getVal('cfg-telegram-chatid')
            }
        };

        const res = await fetch('/api/config/guardar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        if (data.status === 'ok') {
            showConfigToast('¡Configuración guardada exitosamente en .env!');
            
            // Actualizar inmediatamente la insignia de presupuesto y métricas en pantalla
            const newPresMax = parseFloat(getVal('cfg-presupuesto-max')) || 10.0;
            const curCost = (window.cachedCostos && typeof window.cachedCostos.costo === 'number') ? window.cachedCostos.costo : 0.0;
            const elPresBadge = document.getElementById('cfg-presupuesto-consumo-badge');
            if (elPresBadge) {
                elPresBadge.innerText = `$${curCost.toFixed(2)} / $${newPresMax.toFixed(2)} USD`;
            }
            const elPresBar = document.getElementById('cfg-presupuesto-bar');
            if (elPresBar && newPresMax > 0) {
                const pct = Math.min((curCost / newPresMax) * 100, 100);
                elPresBar.style.width = pct + '%';
            }
            const elPresPct = document.getElementById('cfg-presupuesto-pct-text');
            if (elPresPct && newPresMax > 0) {
                const pct = ((curCost / newPresMax) * 100).toFixed(1);
                elPresPct.innerText = `${pct}% consumido`;
            }
            const mCostSub = document.getElementById('metric-cost-sub');
            if (mCostSub && newPresMax > 0) {
                const pct = ((curCost / newPresMax) * 100).toFixed(1);
                mCostSub.innerText = `Presupuesto ($${newPresMax.toFixed(2)}): ${pct}%`;
            }

            activeProviders.forEach(provId => {
                const badge = document.getElementById(`status-badge-${provId}`);
                const hasKey = Boolean(keys[provId]);
                if (badge) {
                    badge.className = `text-[10px] font-mono font-bold px-2 py-0.5 rounded-full ${hasKey ? 'bg-emerald-400/10 text-emerald-400 border border-emerald-400/30' : 'bg-surface-container-high text-on-surface-variant border border-outline-variant/40'}`;
                    badge.innerText = hasKey ? 'CONECTADA' : 'SIN CLAVE';
                }
            });
        } else {
            showConfigToast(data.message || 'Error guardando cambios.', true);
        }
    } catch (e) {
        console.error('Error guardando configuración:', e);
        showConfigToast('Error de comunicación con el servidor.', true);
    } finally {
        if (saveBtn) {
            saveBtn.disabled = false;
            saveBtn.innerHTML = '<span class="material-symbols-outlined text-[16px]">save</span><span>Guardar Cambios</span>';
        }
    }
}
window.guardarTodaLaConfiguracion = guardarTodaLaConfiguracion;

async function reiniciarTripulacionDesdeConfig() {
    if (!confirm('¿Deseas reiniciar los agentes y servicios de la tripulación?')) return;
    try {
        const res = await fetch('/api/system/restart', { method: 'POST' });
        const data = await res.json();
        showConfigToast(data.message || 'Orden de reinicio enviada correctamente.');
    } catch (e) {
        showConfigToast('Error al intentar reiniciar el servicio.', true);
    }
}
window.reiniciarTripulacionDesdeConfig = reiniciarTripulacionDesdeConfig;

async function probarTelegramTest() {
    const btn = document.getElementById('btn-test-telegram');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="material-symbols-outlined text-[16px] animate-spin">sync</span><span>Enviando prueba...</span>';
    }

    try {
        const res = await fetch('/api/config/test-telegram', { method: 'POST' });
        const data = await res.json();
        if (data.status === 'ok') {
            showConfigToast(data.message);
        } else {
            showConfigToast(data.message, true);
        }
    } catch (e) {
        showConfigToast('Error al conectar con Telegram.', true);
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<span class="material-symbols-outlined text-[16px]">notifications_active</span><span>Enviar Mensaje de Prueba al Bot</span>';
        }
    }
}
window.probarTelegramTest = probarTelegramTest;

async function resetearCostosMes() {
    if (!confirm('¿Estás seguro de que deseas restablecer el acumulador de consumo y costos a $0.00?')) return;
    try {
        const res = await fetch('/api/config/reset-costos', { method: 'POST' });
        const data = await res.json();
        if (data.status === 'ok') {
            showConfigToast(data.message);
        } else {
            showConfigToast(data.message, true);
        }
    } catch (e) {
        showConfigToast('Error restableciendo costos.', true);
    }
}
window.resetearCostosMes = resetearCostosMes;

function copiarUrlTelemetria() {
    const text = `http://${window.location.host}/api/telemetria/reportar`;
    navigator.clipboard.writeText(text).then(() => {
        showConfigToast('¡URL de telemetría copiada al portapapeles!');
    }).catch(() => {
        showConfigToast('No se pudo copiar automáticamente. URL: ' + text);
    });
}
window.copiarUrlTelemetria = copiarUrlTelemetria;


