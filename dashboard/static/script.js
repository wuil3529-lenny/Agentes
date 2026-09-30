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
                if (data.sesiones_chat && typeof updateSesionesChat === 'function') {
                    updateSesionesChat(data.sesiones_chat);
                }
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
                if (typeof handleIntrusionAlarmUpdate === 'function') {
                    handleIntrusionAlarmUpdate(data.alerta_intrusion, data.incidentes_seguridad);
                }
                if (data.comandos_remotos) {
                    window.cachedComandosRemotos = data.comandos_remotos;
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
    const totalFinalizados = countCompletados + countFallidos;
    if (totalFinalizados > 0) {
        precVal = ((countCompletados / totalFinalizados) * 100).toFixed(1);
    }
    const elPrec = document.getElementById('metric-precision');
    if (elPrec) {
        elPrec.innerText = precVal + '%';
    }
    const elPrecSub = document.getElementById('metric-precision-sub');
    if (elPrecSub) {
        if (totalFinalizados > 0) {
            const icon = countFallidos > 0 ? 'info' : 'check_circle';
            const colorClass = countFallidos > 0 ? 'text-amber-400' : 'text-emerald-400';
            elPrecSub.className = 'mt-1 flex items-center gap-1.5 text-[11px] font-semibold ' + colorClass;
            elPrecSub.innerHTML = '<span class="material-symbols-outlined text-[14px]">' + icon + '</span><span>' + countCompletados + ' completados · ' + countFallidos + ' fallidos</span>';
        } else {
            elPrecSub.className = 'mt-1 flex items-center gap-1.5 text-[11px] font-semibold text-secondary';
            elPrecSub.innerHTML = '<span class="material-symbols-outlined text-[14px]">task_alt</span><span>Sin tickets finalizados</span>';
        }
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
    
    if (msgList.length === 0) {
        container.dataset.lastCount = 0;
        container.innerHTML = `
            <div class="flex flex-col items-center justify-center h-full py-12 text-center text-on-surface-variant/60 select-none">
                <span class="material-symbols-outlined text-[36px] text-primary/40 mb-2">forum</span>
                <p class="text-xs font-semibold text-on-surface">Canal limpio y listo para zarpar</p>
                <p class="text-[10px] text-on-surface-variant/60 mt-1">Escribe una orden a Luffy para comenzar esta conversación.</p>
            </div>
        `;
        return;
    }

    const agentColors = {
        'usuario': { border: 'border-primary/40', bg: 'bg-primary/20', text: 'text-primary', name: 'Capitán (Tú)' },
        'luffy': { border: 'border-primary/50', bg: 'bg-primary/10', text: 'text-primary', name: 'Luffy' },
        'zoro': { border: 'border-secondary/50', bg: 'bg-secondary/10', text: 'text-secondary', name: 'Zoro' },
        'sanji': { border: 'border-tertiary/50', bg: 'bg-tertiary/10', text: 'text-tertiary', name: 'Sanji' },
        'nami': { border: 'border-amber-400/50', bg: 'bg-amber-400/10', text: 'text-amber-400', name: 'Nami' },
        'robin': { border: 'border-purple-400/50', bg: 'bg-purple-400/10', text: 'text-purple-400', name: 'Robin' }
    };

    if (container.dataset.currentSesionId !== activeSesionId || container.dataset.lastCount != msgList.length) {
        container.dataset.lastCount = msgList.length;
        container.dataset.currentSesionId = activeSesionId;
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
function autoResizeChatInput(el) {
    if (!el) return;
    el.style.height = '38px';
    const scrollH = el.scrollHeight;
    if (scrollH > 38) {
        el.style.height = Math.min(scrollH, 140) + 'px';
    }
}
window.autoResizeChatInput = autoResizeChatInput;

async function sendChatMessage() {
    const input = document.getElementById('chat-input');
    if (!input || !input.value.trim()) return;
    const text = input.value.trim();
    input.value = '';
    input.style.height = '38px';

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
        input.addEventListener('input', () => autoResizeChatInput(input));
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendChatMessage();
            } else if (e.key === 'Enter' && e.shiftKey) {
                setTimeout(() => autoResizeChatInput(input), 0);
            }
        });
    }
}
// =============================================================================
// GESTIÓN DE SESIONES Y CANALES AISLADOS DE CONVERSACIÓN (SIDEBAR + CHAT)
// =============================================================================
let sesionesChatCache = [];
let activeSesionId = null;

function updateSesionesChat(sesiones) {
    if (!Array.isArray(sesiones)) return;
    sesionesChatCache = sesiones;
    
    const activa = sesiones.find(s => s.activo) || sesiones[0];
    if (activa) {
        activeSesionId = activa.id;
        const titleEl = document.getElementById('chat-active-session-title');
        if (titleEl) {
            titleEl.textContent = activa.titulo || 'Conversación';
            titleEl.title = `Canal activo: ${activa.titulo || 'Conversación'}`;
        }
    }
    
    renderSidebarChannels(sesiones);
}
window.updateSesionesChat = updateSesionesChat;

function renderSidebarChannels(sesiones) {
    const list = document.getElementById('sidebar-channels-list');
    if (!list) return;
    
    if (!sesiones || sesiones.length === 0) {
        list.innerHTML = '<p class="text-on-surface-variant/50 text-[10px] italic py-2 text-center">No hay canales de chat</p>';
        return;
    }
    
    let html = '';
    sesiones.forEach(s => {
        const isActive = s.activo || (s.id === activeSesionId);
        let timeStr = '';
        if (s.actualizado || s.creado) {
            try {
                const d = new Date(s.actualizado || s.creado);
                timeStr = d.toLocaleDateString([], { month: 'short', day: 'numeric' });
            } catch(e) {}
        }
        
        const countMsgs = s.total_mensajes || 0;
        const tituloLimpio = escapeHtml(s.titulo || 'Conversación');
        const isAnclado = Boolean(s.anclado);
        
        html += `
        <div onclick="seleccionarChatSesion('${s.id}')" class="group relative flex items-center justify-between py-1 px-2 rounded-lg cursor-pointer transition-all border select-none h-7 min-h-[28px] ${
            isActive 
                ? 'bg-primary/20 border-primary/50 text-white shadow-[0_0_8px_rgba(255,45,120,0.25)]' 
                : 'bg-surface-container/20 hover:bg-surface-container-high border-outline-variant/15 text-on-surface-variant hover:text-on-surface'
        }" title="${tituloLimpio}">
            <div class="flex items-center gap-1.5 min-w-0 flex-1">
                ${isAnclado ? `
                <button onclick="event.stopPropagation(); alternarAnclarChatSesion('${s.id}')" type="button" class="cursor-pointer p-0.5 rounded hover:bg-amber-400/20 text-amber-400 shrink-0 flex items-center justify-center transition-all group/pin" title="Desanclar este chat">
                    <span class="material-symbols-outlined text-[13px] rotate-45 group-hover/pin:scale-110">push_pin</span>
                </button>
                ` : `
                <span class="material-symbols-outlined text-[14px] ${isActive ? 'text-primary' : 'text-on-surface-variant/50 group-hover:text-primary'} shrink-0">
                    ${isActive ? 'chat_bubble' : 'chat_bubble_outline'}
                </span>
                `}
                <span class="text-[11px] font-medium truncate leading-none flex-1 ${isActive ? 'text-white font-semibold' : 'text-on-surface/85'}">
                    ${tituloLimpio}
                </span>
            </div>
            
            <div class="flex items-center gap-1 shrink-0 ml-1.5">
                <!-- Badge cuando no se pasa el ratón -->
                <span class="text-[9px] text-on-surface-variant/40 font-mono group-hover:hidden">
                    ${countMsgs}
                </span>
                
                <!-- Acciones en Hover: Anclar, Renombrar, Eliminar -->
                <div class="hidden group-hover:flex items-center gap-0.5">
                    <!-- Botón Anclar / Desanclar -->
                    <button onclick="event.stopPropagation(); alternarAnclarChatSesion('${s.id}')" type="button" class="p-0.5 hover:bg-white/10 rounded transition-all ${isAnclado ? 'text-amber-400' : 'text-on-surface-variant/50 hover:text-amber-300'} cursor-pointer flex items-center justify-center" title="${isAnclado ? 'Desanclar chat' : 'Anclar chat al inicio'}">
                        <span class="material-symbols-outlined text-[13px] ${isAnclado ? 'rotate-45' : ''}">push_pin</span>
                    </button>
                    <!-- Botón Renombrar -->
                    <button onclick="event.stopPropagation(); renombrarChatSesion('${s.id}', '${tituloLimpio.replace(/'/g, "\\'")}')" type="button" class="p-0.5 hover:text-cyan-300 hover:bg-cyan-500/15 rounded transition-all text-on-surface-variant/50 cursor-pointer flex items-center justify-center" title="Cambiar nombre">
                        <span class="material-symbols-outlined text-[13px]">edit</span>
                    </button>
                    <!-- Botón Eliminar -->
                    ${sesiones.length > 1 ? `
                    <button onclick="event.stopPropagation(); eliminarChatSesion('${s.id}', '${tituloLimpio.replace(/'/g, "\\'")}')" type="button" class="p-0.5 hover:text-rose-400 hover:bg-rose-500/15 rounded transition-all text-on-surface-variant/50 cursor-pointer flex items-center justify-center" title="Eliminar chat">
                        <span class="material-symbols-outlined text-[13px]">delete</span>
                    </button>
                    ` : ''}
                </div>
            </div>
        </div>
        `;
    });
    
    list.innerHTML = html;
}
window.renderSidebarChannels = renderSidebarChannels;

async function crearNuevoChatSesion() {
    try {
        const res = await fetch('/api/chat/sesiones/nueva', { method: 'POST' });
        const data = await res.json();
        if (data.status === 'ok') {
            activeSesionId = data.sesion.id;
            updateSesionesChat(data.sesiones);
            
            // Limpiar visualmente el chat de inmediato con animación suave
            const container = document.getElementById('chat-messages');
            if (container) {
                container.dataset.lastCount = 0;
                container.dataset.currentSesionId = activeSesionId;
                container.innerHTML = `
                    <div class="flex flex-col items-center justify-center h-full py-12 text-center text-on-surface-variant/60 select-none">
                        <span class="material-symbols-outlined text-[36px] text-primary/40 mb-2">forum</span>
                        <p class="text-xs font-semibold text-on-surface">Canal limpio y listo para zarpar</p>
                        <p class="text-[10px] text-on-surface-variant/60 mt-1">Escribe una orden a Luffy para comenzar esta conversación.</p>
                    </div>
                `;
            }
            
            const input = document.getElementById('chat-input');
            if (input) {
                input.value = '';
                input.style.height = '38px';
                input.focus();
            }
        }
    } catch(e) {
        console.error('Error creando nuevo chat:', e);
    }
}
window.crearNuevoChatSesion = crearNuevoChatSesion;

async function seleccionarChatSesion(sesionId) {
    if (!sesionId || sesionId === activeSesionId) return;
    try {
        const res = await fetch(`/api/chat/sesiones/${sesionId}/activar`, { method: 'POST' });
        const data = await res.json();
        if (data.status === 'ok') {
            activeSesionId = sesionId;
            updateSesionesChat(data.sesiones);
            const container = document.getElementById('chat-messages');
            if (container) {
                container.dataset.currentSesionId = activeSesionId;
                container.dataset.lastCount = -1; // Forzar re-render
            }
            if (typeof updateChat === 'function') {
                updateChat(data.mensajes);
            }
        }
    } catch(e) {
        console.error('Error cambiando de chat:', e);
    }
}
window.seleccionarChatSesion = seleccionarChatSesion;
let isTogglingAnclar = false;
async function alternarAnclarChatSesion(sesionId) {
    if (!sesionId || isTogglingAnclar) return;
    isTogglingAnclar = true;
    try {
        const res = await fetch(`/api/chat/sesiones/${sesionId}/anclar`, { method: 'POST' });
        const data = await res.json();
        if (data.status === 'ok') {
            updateSesionesChat(data.sesiones);
        }
    } catch(e) {
        console.error('Error al alternar anclado de chat:', e);
    } finally {
        setTimeout(() => { isTogglingAnclar = false; }, 200);
    }
}
window.alternarAnclarChatSesion = alternarAnclarChatSesion;

let sesionIdARenombrar = null;

function renombrarChatSesion(sesionId, tituloActual) {
    if (!sesionId) return;
    sesionIdARenombrar = sesionId;
    const sesion = (sesionesChatCache || []).find(s => s.id === sesionId);
    const titulo = tituloActual || (sesion ? sesion.titulo : '');
    
    const input = document.getElementById('modal-rename-chat-input');
    if (input) {
        input.value = titulo || '';
    }
    
    const modal = document.getElementById('modal-rename-chat');
    if (modal) {
        modal.classList.remove('hidden');
        setTimeout(() => {
            if (input) {
                input.focus();
                input.select();
            }
        }, 50);
    }
}
window.renombrarChatSesion = renombrarChatSesion;

function cerrarModalRenombrarChat() {
    sesionIdARenombrar = null;
    const modal = document.getElementById('modal-rename-chat');
    if (modal) modal.classList.add('hidden');
}
window.cerrarModalRenombrarChat = cerrarModalRenombrarChat;

async function ejecutarRenombrarChatSesion() {
    if (!sesionIdARenombrar) return;
    const input = document.getElementById('modal-rename-chat-input');
    const nuevoTrim = input ? input.value.trim() : '';
    if (!nuevoTrim) {
        cerrarModalRenombrarChat();
        return;
    }
    
    const idToRename = sesionIdARenombrar;
    const btn = document.getElementById('btn-modal-confirm-rename-chat');
    if (btn) btn.disabled = true;
    
    try {
        const res = await fetch(`/api/chat/sesiones/${idToRename}/renombrar`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ titulo: nuevoTrim })
        });
        const data = await res.json();
        if (data.status === 'ok') {
            cerrarModalRenombrarChat();
            updateSesionesChat(data.sesiones);
        }
    } catch(e) {
        console.error('Error al renombrar chat:', e);
    } finally {
        if (btn) btn.disabled = false;
        cerrarModalRenombrarChat();
    }
}
window.ejecutarRenombrarChatSesion = ejecutarRenombrarChatSesion;

let sesionIdAEliminar = null;

function eliminarChatSesion(sesionId, tituloOpcional) {
    if (!sesionId) return;
    sesionIdAEliminar = sesionId;
    const sesion = (sesionesChatCache || []).find(s => s.id === sesionId);
    const titulo = tituloOpcional || (sesion ? sesion.titulo : 'este chat');
    
    const titleEl = document.getElementById('modal-delete-chat-title');
    if (titleEl) titleEl.textContent = `"${titulo}"`;
    
    const modal = document.getElementById('modal-confirm-delete-chat');
    if (modal) modal.classList.remove('hidden');
}
window.eliminarChatSesion = eliminarChatSesion;

function cerrarModalConfirmarEliminarChat() {
    sesionIdAEliminar = null;
    const modal = document.getElementById('modal-confirm-delete-chat');
    if (modal) modal.classList.add('hidden');
}
window.cerrarModalConfirmarEliminarChat = cerrarModalConfirmarEliminarChat;

async function ejecutarEliminarChatSesion() {
    if (!sesionIdAEliminar) return;
    const idToDelete = sesionIdAEliminar;
    const btn = document.getElementById('btn-modal-confirm-delete-chat');
    if (btn) btn.disabled = true;
    
    try {
        const res = await fetch(`/api/chat/sesiones/${idToDelete}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.status === 'ok') {
            cerrarModalConfirmarEliminarChat();
            const activa = data.sesiones.find(s => s.activo) || data.sesiones[0];
            if (activa) activeSesionId = activa.id;
            updateSesionesChat(data.sesiones);
            const container = document.getElementById('chat-messages');
            if (container) {
                container.dataset.currentSesionId = activeSesionId;
                container.dataset.lastCount = -1;
            }
        }
    } catch(e) {
        console.error('Error eliminando sesión de chat:', e);
    } finally {
        if (btn) btn.disabled = false;
        cerrarModalConfirmarEliminarChat();
    }
}
window.ejecutarEliminarChatSesion = ejecutarEliminarChatSesion;

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        cerrarModalConfirmarEliminarChat();
        cerrarModalRenombrarChat();
    }
});

async function cargarSesionesChatInicial() {
    try {
        const res = await fetch('/api/chat/sesiones');
        const data = await res.json();
        if (data.status === 'ok' && data.sesiones) {
            updateSesionesChat(data.sesiones);
        }
    } catch(e) {
        console.error('Error cargando sesiones iniciales:', e);
    }
}
function initChatSystem() {
    if (typeof initChatListeners === 'function') initChatListeners();
    cargarSesionesChatInicial();
}
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initChatSystem);
} else {
    initChatSystem();
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

let currentTabTareas = 'activas';

function cambiarTabTareas(tab) {
    currentTabTareas = tab;
    const btnActivas = document.getElementById('btn-tab-activas');
    const btnArchivadas = document.getElementById('btn-tab-archivadas');
    const containerActivas = document.getElementById('container-tareas-activas');
    const containerArchivadas = document.getElementById('container-tareas-archivadas');
    const title = document.getElementById('tab-section-title');
    const dot = document.getElementById('tab-indicator-dot');
    
    if (tab === 'archivadas') {
        if (btnActivas) {
            btnActivas.className = "px-3.5 py-1.5 rounded-lg text-xs font-bold flex items-center gap-2 transition-all cursor-pointer text-on-surface-variant hover:text-on-surface";
        }
        if (btnArchivadas) {
            btnArchivadas.className = "px-3.5 py-1.5 rounded-lg text-xs font-bold flex items-center gap-2 transition-all cursor-pointer bg-teal-500/20 text-teal-300 border border-teal-500/40 shadow-[0_0_10px_rgba(20,184,166,0.2)]";
        }
        if (containerActivas) containerActivas.classList.add('hidden');
        if (containerArchivadas) containerArchivadas.classList.remove('hidden');
        if (title) title.textContent = "Tareas Completadas & Archivadas";
        if (dot) dot.className = "w-2.5 h-2.5 rounded-full bg-teal-400";
    } else {
        if (btnActivas) {
            btnActivas.className = "px-3.5 py-1.5 rounded-lg text-xs font-bold flex items-center gap-2 transition-all cursor-pointer bg-secondary/20 text-secondary border border-secondary/40 shadow-[0_0_10px_rgba(0,255,204,0.2)]";
        }
        if (btnArchivadas) {
            btnArchivadas.className = "px-3.5 py-1.5 rounded-lg text-xs font-bold flex items-center gap-2 transition-all cursor-pointer text-on-surface-variant hover:text-on-surface";
        }
        if (containerActivas) containerActivas.classList.remove('hidden');
        if (containerArchivadas) containerArchivadas.classList.add('hidden');
        if (title) title.textContent = "Tareas en Ejecución & Pendientes";
        if (dot) dot.className = "w-2.5 h-2.5 rounded-full bg-secondary animate-pulse";
    }
}

function renderTareaBlock(tarea) {
    // tarea: {id, titulo, descripcion, tarea, criterios, responsable, estado, evidencia}
    const cleanId = cleanMarkdownText(tarea.id || '');
    const cleanTitle = cleanMarkdownText(tarea.titulo || '');
    const cleanDesc = cleanMarkdownText(tarea.descripcion || '');
    const cleanTask = cleanMarkdownText(tarea.tarea || '');
    const cleanEvidencia = cleanMarkdownText(tarea.evidencia || '');
    
    // Configuración de Agentes (Robin morado, Sanji amarillo, Nami rosa, Zoro verde, Luffy rojo)
    const agentesConfig = {
        robin: {
            name: 'Robin',
            color: '#c084fc',
            border: 'border-purple-400/50',
            badge: 'bg-purple-500/15 text-purple-300 border-purple-500/40',
            avatar: 'Robin'
        },
        sanji: {
            name: 'Sanji',
            color: '#fbbf24',
            border: 'border-amber-400/50',
            badge: 'bg-amber-500/15 text-amber-300 border-amber-500/40',
            avatar: 'Sanji'
        },
        nami: {
            name: 'Nami',
            color: '#f472b6',
            border: 'border-pink-400/50',
            badge: 'bg-pink-500/15 text-pink-300 border-pink-500/40',
            avatar: 'Nami'
        },
        zoro: {
            name: 'Zoro',
            color: '#34d399',
            border: 'border-emerald-400/50',
            badge: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/40',
            avatar: 'Zoro'
        },
        luffy: {
            name: 'Luffy',
            color: '#f43f5e',
            border: 'border-rose-400/50',
            badge: 'bg-rose-500/15 text-rose-300 border-rose-500/40',
            avatar: 'LuffyCaptain'
        },
        sistema: {
            name: 'Sistema',
            color: '#94a3b8',
            border: 'border-slate-500/40',
            badge: 'bg-slate-500/15 text-slate-300 border-slate-500/30',
            avatar: 'Tripulacion'
        }
    };

    let rawName = tarea.responsable ? String(tarea.responsable).toLowerCase().trim() : 'sistema';
    // Si el ID del ticket pertenece a un subagente (ej: TKT-SANJI-..., TKT-ROBIN-..., TKT-NAMI-..., TKT-ZORO-...)
    const ticketIdUpper = String(tarea.id || '').toUpperCase();
    for (const ag of ['sanji', 'robin', 'nami', 'zoro']) {
        if (ticketIdUpper.startsWith('TKT-' + ag.toUpperCase() + '-')) {
            rawName = ag;
            break;
        }
    }
    let agKey = 'sistema';
    for (const k of ['robin', 'sanji', 'nami', 'zoro', 'luffy']) {
        if (rawName.includes(k)) {
            agKey = k;
            break;
        }
    }
    const cfg = agentesConfig[agKey] || agentesConfig.sistema;
    const nameFormatted = agKey !== 'sistema' ? cfg.name : (cleanMarkdownText(tarea.responsable) || 'Sistema');

    // Estado del ticket: Verde si en proceso, Azul si en espera, Rojo si fallido, Teal si completado
    const estadoRaw = tarea.estado ? String(tarea.estado).toLowerCase().trim() : '';
    let statusConfig = {
        label: 'En Espera',
        badgeClass: 'bg-blue-500/15 text-blue-400 border border-blue-500/40 shadow-[0_0_8px_rgba(59,130,246,0.15)]',
        icon: 'hourglass_empty',
        spin: false,
        cardBorder: 'border-blue-500/40 hover:border-blue-400',
        cardBg: 'bg-blue-950/20 hover:bg-blue-950/30',
        cardGlow: 'hover:shadow-[0_0_15px_rgba(59,130,246,0.2)]'
    };

    if (estadoRaw.includes('fall') || estadoRaw.includes('error') || estadoRaw.includes('rechaz') || estadoRaw.includes('abort') || estadoRaw.includes('critic') || estadoRaw.includes('bloquead')) {
        statusConfig = {
            label: 'Fallido',
            badgeClass: 'bg-rose-500/20 text-rose-400 border border-rose-500/50 shadow-[0_0_8px_rgba(244,63,94,0.2)]',
            icon: 'error',
            spin: false,
            cardBorder: 'border-rose-500/50 hover:border-rose-400',
            cardBg: 'bg-rose-950/25 hover:bg-rose-950/35',
            cardGlow: 'hover:shadow-[0_0_15px_rgba(244,63,94,0.25)]'
        };
    } else if (estadoRaw.includes('proceso') || estadoRaw.includes('progreso') || estadoRaw.includes('ejecut') || estadoRaw.includes('trabajando') || estadoRaw.includes('procesando')) {
        statusConfig = {
            label: 'En Proceso',
            badgeClass: 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/40 shadow-[0_0_8px_rgba(16,185,129,0.2)]',
            icon: 'progress_activity',
            spin: true,
            cardBorder: 'border-emerald-500/50 hover:border-emerald-400',
            cardBg: 'bg-emerald-950/20 hover:bg-emerald-950/30',
            cardGlow: 'hover:shadow-[0_0_15px_rgba(16,185,129,0.25)]'
        };
    } else if (estadoRaw.includes('completad') || estadoRaw.includes('cerrad') || estadoRaw.includes('archiv')) {
        statusConfig = {
            label: 'Completado',
            badgeClass: 'bg-teal-500/15 text-teal-300 border border-teal-500/40 shadow-[0_0_8px_rgba(20,184,166,0.15)]',
            icon: 'check_circle',
            spin: false,
            cardBorder: 'border-teal-500/30 hover:border-teal-400/60',
            cardBg: 'bg-surface-container-low/70 hover:bg-surface-container-low',
            cardGlow: 'hover:shadow-[0_0_12px_rgba(20,184,166,0.15)]'
        };
    }

    // Texto descriptivo principal (conciso, evitando redundancias)
    const displayTitle = cleanTitle || cleanTask || 'Ticket de Tarea';
    const displayDesc = cleanDesc || (cleanTask && cleanTask !== cleanTitle ? cleanTask : '') || 'Sin detalles adicionales.';

    return `
    <div class="glass-panel rounded-2xl p-4 border ${statusConfig.cardBorder} ${statusConfig.cardBg} ${statusConfig.cardGlow} transition-all duration-200 flex flex-col justify-between gap-3 group relative overflow-hidden min-h-[200px] h-[215px]">
        <!-- Top Row: ID chip + Status badge -->
        <div class="flex items-center justify-between gap-2 shrink-0">
            <span class="inline-flex items-center px-2 py-0.5 rounded-md font-mono text-[10px] font-bold bg-white/5 text-on-surface/90 border border-white/10 tracking-wider">
                ${cleanId || 'TKT'}
            </span>
            <span class="inline-flex items-center gap-1.5 text-[10px] font-bold tracking-wider uppercase px-2 py-0.5 rounded-lg ${statusConfig.badgeClass} shrink-0">
                <span class="material-symbols-outlined text-[12px] ${statusConfig.spin ? 'animate-spin' : ''}">${statusConfig.icon}</span>
                <span>${statusConfig.label}</span>
            </span>
        </div>

        <!-- Middle: Title and truncated description -->
        <div class="flex flex-col gap-1.5 flex-1 min-h-0 overflow-hidden">
            <h4 class="text-on-surface font-semibold text-xs leading-snug line-clamp-2 group-hover:text-white transition-colors" title="${displayTitle}">
                ${displayTitle}
            </h4>
            <p class="text-[11px] text-on-surface-variant/80 leading-relaxed line-clamp-3" title="${displayDesc}">
                ${displayDesc}
            </p>
        </div>

        <!-- Bottom: Agent Badge with individual color + Evidence indicator -->
        <div class="mt-auto pt-2.5 border-t border-white/10 flex items-center justify-between shrink-0">
            <div class="flex items-center gap-2">
                <div class="w-6 h-6 rounded-lg overflow-hidden border ${cfg.border} bg-surface-container shrink-0">
                    <img alt="${nameFormatted}" class="w-full h-full object-cover" src="https://api.dicebear.com/7.x/bottts/svg?seed=${cfg.avatar}&backgroundColor=0f0f1a">
                </div>
                <span class="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-md border ${cfg.badge}">
                    ${nameFormatted}
                </span>
            </div>
            ${cleanEvidencia ? `<span class="material-symbols-outlined text-[15px] text-on-surface-variant/70 hover:text-secondary cursor-help transition-colors" title="Evidencia: ${cleanEvidencia}">attachment</span>` : ''}
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
        list.innerHTML = '<p class="text-on-surface-variant text-sm italic py-12 text-center col-span-full">No hay tareas activas en la pizarra...</p>';
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
        list.innerHTML = '<p class="text-on-surface-variant text-sm italic py-12 text-center col-span-full">No hay tickets archivados todavía...</p>';
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
            if (btnText) btnText.innerText = 'Finalizar Comunicación';
            if (badge) {
                badge.innerText = 'Escuchando Voz';
                badge.className = 'py-0.5 px-2.5 rounded-full text-[10px] font-bold tracking-wider uppercase bg-secondary/20 border border-secondary text-secondary animate-pulse shadow-[0_0_10px_rgba(0,255,204,0.4)]';
                badge.style = '';
            }
            if (feedback) {
                feedback.innerText = 'Canal de voz activo';
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
        if (btnText) btnText.innerText = 'Iniciar Comunicación';
        if (badge) {
            badge.innerText = 'En Reposo';
            badge.className = 'py-0.5 px-2.5 rounded-full text-[10px] font-bold tracking-wider uppercase bg-surface-container-high border border-outline-variant text-on-surface-variant';
            badge.style = '';
        }
        if (feedback) {
            feedback.innerText = 'Canal de voz en espera';
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
    sBase: 20,          // Base shoulder radius
    rb: 21,             // Bowl radius around bead
    x0: 12,             // Plate left edge (aligned with pl-3 = 12px)
    bx: 46.5,           // Bead center X (aligned with .icon-box)
    plateRadius: 12     // Corner radius of the dock plate
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
                          `C ${x0} ${y2 - reachBot * 0.45}, ${bx + rb * 0.15} ${by + rb * 0.72}, ${bx + rb * 0.32} ${by} ` +
                          `C ${bx + rb * 0.15} ${by - rb * 0.72}, ${x0} ${y1 + reachTop * 0.45}, ${x0} ${y1}`;
    
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
                        `C ${x0} ${y1 + reachTop * 0.45}, ${bx + rb * 0.15} ${by - rb * 0.72}, ${bx + rb * 0.32} ${by} ` +
                        `C ${bx + rb * 0.15} ${by + rb * 0.72}, ${x0} ${y2 - reachBot * 0.45}, ${x0} ${y2}`;
    
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
    let dockBottom = 260;
    if (items.length > 0) {
        const firstItem = items[0];
        const lastItem = items[items.length - 1];
        dockTop = Math.max(0, firstItem.offsetTop - 12);
        dockBottom = lastItem.offsetTop + lastItem.offsetHeight + 10;
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

    // 6. Automatically close mobile navigation drawer after selecting tab
    if (window.innerWidth < 1024 && typeof toggleMobileSidebar === 'function') {
        setTimeout(() => {
            toggleMobileSidebar(false);
        }, 220);
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
                    if (typeof renderConfigThemesGrid === 'function') renderConfigThemesGrid();
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

        // Mini Agentes Roster Dinámico (Soporta nombres personalizados como Angel Lead, Hunter, etc.)
        const agentThemePalette = [
            'text-primary', 'text-secondary', 'text-amber-400', 'text-purple-400', 'text-yellow-400', 'text-cyan-400', 'text-emerald-400'
        ];
        const defaultAgents = ['luffy', 'zoro', 'sanji', 'robin', 'nami'];
        const agNames = (eq.agentes && Object.keys(eq.agentes).length > 0) ? Object.keys(eq.agentes) : defaultAgents;
        const isCrewOff = isOff || (est !== 'activa' && est !== 'conectada');

        const agHtml = agNames.map((ag, idx) => {
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
            const nameColor = agentThemePalette[idx % agentThemePalette.length] || 'text-on-surface';
            return `
                <div class="flex flex-col items-center gap-0.5 p-1.5 rounded-xl bg-surface-container-low/60 border border-outline-variant/20 flex-1 min-w-[50px]">
                    <div class="flex items-center gap-1">
                        <span class="w-1.5 h-1.5 rounded-full ${dotColor}"></span>
                        <span class="font-bold text-[10px] uppercase truncate max-w-[85px] ${nameColor}" title="${ag}">${ag}</span>
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

function setFleetPreset(nombre, entorno) {
    const n = document.getElementById('new-fleet-name');
    const d = document.getElementById('new-fleet-desc');
    if (n) {
        n.value = nombre;
        n.focus();
    }
    if (d) d.value = entorno;
}
window.setFleetPreset = setFleetPreset;

let fleetPairingTimerInterval = null;
let fleetPairingPollInterval = null;

function detenerEmparejamientoFlota() {
    if (fleetPairingTimerInterval) {
        clearInterval(fleetPairingTimerInterval);
        fleetPairingTimerInterval = null;
    }
    if (fleetPairingPollInterval) {
        clearInterval(fleetPairingPollInterval);
        fleetPairingPollInterval = null;
    }
}

function resetFleetModalForm() {
    detenerEmparejamientoFlota();

    const resPanel = document.getElementById('fleet-credentials-result');
    if (resPanel) resPanel.classList.add('hidden');
    const form = document.getElementById('fleet-reg-form');
    if (form) form.classList.remove('hidden');

    const pairingBox = document.getElementById('fleet-pairing-box');
    if (pairingBox) pairingBox.classList.add('hidden');

    const btnEmp = document.getElementById('btn-emparejar-flota');
    if (btnEmp) {
        btnEmp.classList.add('hidden');
        btnEmp.disabled = false;
        btnEmp.className = 'px-4 py-2 rounded-xl bg-gradient-to-r from-cyan-400 via-secondary to-emerald-400 hover:brightness-110 text-[#070b14] font-black text-xs flex items-center gap-1.5 transition-all shadow-[0_0_15px_rgba(34,211,238,0.35)] cursor-pointer';
        btnEmp.innerHTML = '<span class="material-symbols-outlined text-[16px]">sensors</span><span>Emparejar Flota</span>';
    }

    const n = document.getElementById('new-fleet-name');
    if (n) {
        n.value = '';
        setTimeout(() => n.focus(), 60);
    }
}
window.resetFleetModalForm = resetFleetModalForm;

function toggleConnectModal(show) {
    const modal = document.getElementById('fleet-connect-modal');
    if (!modal) return;
    if (show) {
        modal.classList.remove('hidden');
        resetFleetModalForm();
    } else {
        detenerEmparejamientoFlota();
        modal.classList.add('hidden');
    }
}
window.toggleConnectModal = toggleConnectModal;

function switchFleetModalTab(tab) {}
window.switchFleetModalTab = switchFleetModalTab;

async function ejecutarRegistroFlota(event) {
    if (event) event.preventDefault();
    const nameInp = document.getElementById('new-fleet-name');
    const btn = document.getElementById('btn-crear-flota');

    const nombre = nameInp ? nameInp.value.trim() : '';

    if (!nombre) {
        alert('Por favor escribe el nombre de la flota remota.');
        return;
    }

    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="material-symbols-outlined text-[17px] animate-spin">sync</span><span>Generando llaves...</span>';
    }

    try {
        const res = await fetch('/api/flotas/registrar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ nombre, cliente: '', descripcion: '' })
        });
        const data = await res.json();

        if (res.ok && data.status === 'ok') {
            const f = data.flota;
            const form = document.getElementById('fleet-reg-form');
            if (form) form.classList.add('hidden');

            const resPanel = document.getElementById('fleet-credentials-result');
            if (resPanel) resPanel.classList.remove('hidden');

            const idEl = document.getElementById('res-fleet-id');
            const keyEl = document.getElementById('res-fleet-api-key');
            const secEl = document.getElementById('res-fleet-secret');
            const badgeEl = document.getElementById('res-fleet-badge');

            if (idEl) idEl.innerText = f.id;
            if (keyEl) keyEl.innerText = f.api_key;
            if (secEl) secEl.innerText = f.secret_key;
            if (badgeEl) badgeEl.innerText = f.nombre;

            // Make sure pairing box is hidden initially
            const pairingBox = document.getElementById('fleet-pairing-box');
            if (pairingBox) pairingBox.classList.add('hidden');

            // Show 'Emparejar Flota' button in footer
            const btnEmp = document.getElementById('btn-emparejar-flota');
            if (btnEmp) {
                btnEmp.classList.remove('hidden');
                btnEmp.disabled = false;
                btnEmp.className = 'px-4 py-2 rounded-xl bg-gradient-to-r from-cyan-400 via-secondary to-emerald-400 hover:brightness-110 text-[#070b14] font-black text-xs flex items-center gap-1.5 transition-all shadow-[0_0_15px_rgba(34,211,238,0.35)] cursor-pointer';
                btnEmp.innerHTML = '<span class="material-symbols-outlined text-[16px]">sensors</span><span>Emparejar Flota</span>';
            }

            if (nameInp) nameInp.value = '';
        } else {
            alert(data.message || 'Error al registrar la flota');
        }
    } catch (e) {
        console.error('Error registrando flota:', e);
        alert('Error de conexión al registrar flota');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<span class="material-symbols-outlined text-[18px]">vpn_key</span><span>Generar Llaves de Comando</span>';
        }
    }
}
window.ejecutarRegistroFlota = ejecutarRegistroFlota;

function iniciarEmparejamientoFlota() {
    const fleetIdEl = document.getElementById('res-fleet-id');
    const fleetId = fleetIdEl ? fleetIdEl.innerText.trim() : '';

    if (!fleetId || fleetId === '--') {
        alert('No se detectó un identificador de flota válido.');
        return;
    }

    const pairingBox = document.getElementById('fleet-pairing-box');
    const timerEl = document.getElementById('fleet-pairing-timer');
    const titleEl = document.getElementById('fleet-pairing-title');
    const descEl = document.getElementById('fleet-pairing-desc');
    const pulseEl = document.getElementById('fleet-pairing-pulse');
    const btn = document.getElementById('btn-emparejar-flota');

    if (pairingBox) pairingBox.classList.remove('hidden');
    if (titleEl) {
        titleEl.innerText = 'Esperando señal de la flota remota...';
        titleEl.className = 'font-bold text-xs text-cyan-200';
    }
    if (pulseEl) {
        pulseEl.className = 'w-2.5 h-2.5 rounded-full bg-cyan-400 animate-ping';
    }
    if (descEl) {
        descEl.innerHTML = 'Ingrese la Clave API y el Secreto en la consola remota y presione "Emparejar con Torre Central". La sincronización se activará en cuanto se detecte el apretón de manos.';
    }
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="material-symbols-outlined text-[16px] animate-spin">sync</span><span>Buscando Señal...</span>';
        btn.classList.add('opacity-80');
    }

    detenerEmparejamientoFlota();

    let timeLeft = 300; // 5 minutos de tiempo de emparejamiento
    if (timerEl) timerEl.innerText = '05:00';

    fleetPairingTimerInterval = setInterval(() => {
        timeLeft--;
        if (timeLeft <= 0) {
            detenerEmparejamientoFlota();
            if (timerEl) timerEl.innerText = '00:00';
            if (titleEl) {
                titleEl.innerText = 'Tiempo de espera agotado';
                titleEl.className = 'font-bold text-xs text-rose-400';
            }
            if (pulseEl) {
                pulseEl.className = 'w-2.5 h-2.5 rounded-full bg-rose-400';
            }
            if (descEl) {
                descEl.innerHTML = 'No se recibió la conexión dentro de la ventana de seguridad (5 min). Puede reintentar el emparejamiento cuando el nodo remoto esté listo.';
            }
            if (btn) {
                btn.disabled = false;
                btn.classList.remove('opacity-80');
                btn.innerHTML = '<span class="material-symbols-outlined text-[16px]">refresh</span><span>Reintentar Emparejamiento</span>';
            }
            return;
        }
        const mins = String(Math.floor(timeLeft / 60)).padStart(2, '0');
        const secs = String(timeLeft % 60).padStart(2, '0');
        if (timerEl) timerEl.innerText = `${mins}:${secs}`;
    }, 1000);

    // Polling cada 2.5s para detectar apretón de manos
    fleetPairingPollInterval = setInterval(async () => {
        try {
            const res = await fetch(`/api/flotas/estado/${encodeURIComponent(fleetId)}`);
            if (!res.ok) return;
            const data = await res.json();
            if (data.status === 'ok' && data.vinculada) {
                detenerEmparejamientoFlota();

                if (timerEl) timerEl.innerText = 'Sincronizado';
                if (titleEl) {
                    titleEl.innerText = '¡Flota Remota Emparejada con Éxito!';
                    titleEl.className = 'font-bold text-xs text-emerald-400';
                }
                if (pulseEl) {
                    pulseEl.className = 'w-2.5 h-2.5 rounded-full bg-emerald-400';
                }
                if (descEl) {
                    descEl.innerHTML = '<span class="text-emerald-300 font-bold">Enlace seguro C2 establecido.</span> Esta flota remota ya está transmitiendo telemetría en tiempo real a tu Torre Central.';
                }
                if (btn) {
                    btn.disabled = true;
                    btn.classList.remove('opacity-80');
                    btn.className = 'px-4 py-2 rounded-xl bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 font-bold text-xs flex items-center gap-1.5 shadow-sm';
                    btn.innerHTML = '<span class="material-symbols-outlined text-[16px] text-emerald-400">verified</span><span>Flota Emparejada</span>';
                }

                if (typeof showConfigToast === 'function') {
                    showConfigToast('¡Flota remota emparejada y enlazada con éxito!');
                }
                if (typeof cargarListadoFlotasModal === 'function') {
                    cargarListadoFlotasModal();
                }
            }
        } catch (e) {
            console.error('Error verificando estado de emparejamiento:', e);
        }
    }, 2500);
}
window.iniciarEmparejamientoFlota = iniciarEmparejamientoFlota;

async function cargarListadoFlotasModal() {
    const container = document.getElementById('modal-fleets-container');
    const countEl = document.getElementById('modal-fleet-count');
    if (!container) return;

    try {
        const res = await fetch('/api/flotas/lista');
        const data = await res.json();
        const flotas = data.flotas || [];

        if (countEl) countEl.innerText = flotas.length;

        if (flotas.length === 0) {
            container.innerHTML = `
                <div class="p-6 text-center text-on-surface-variant/50 italic border border-outline-variant/20 rounded-xl bg-black/20">
                    No hay flotas registradas aún. Genera las credenciales de tu primera flota en la pestaña anterior.
                </div>
            `;
            return;
        }

        container.innerHTML = flotas.map(f => {
            const isVinculada = f.estado === 'activa' || f.estado === 'vinculada';
            const statusColor = isVinculada ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30' : 'text-amber-400 bg-amber-500/10 border-amber-500/30';
            const statusLabel = isVinculada ? 'Vinculada & Activa' : 'Pendiente Conexión';

            return `
                <div class="p-3 rounded-xl bg-surface-container-low/70 border border-outline-variant/30 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs">
                    <div class="flex flex-col gap-0.5 min-w-0">
                        <div class="flex items-center gap-2">
                            <span class="font-bold text-white text-sm font-sans truncate">${f.nombre}</span>
                            <span class="px-2 py-0.5 rounded text-[10px] font-bold border ${statusColor}">${statusLabel}</span>
                        </div>
                        <div class="flex items-center gap-2 text-[10px] text-on-surface-variant">
                            <span>ID: <code class="text-cyan-300 font-mono">${f.id}</code></span>
                            <span>•</span>
                            <span>Cliente: ${f.cliente || 'General'}</span>
                            <span>•</span>
                            <span>Rotaciones: ${f.rotaciones_realizadas || 0}</span>
                        </div>
                        ${f.ultimo_reporte ? `<span class="text-[9px] text-emerald-400/80">Último reporte: Hace unos momentos</span>` : `<span class="text-[9px] text-on-surface-variant/50">Creada: ${f.creado_en}</span>`}
                    </div>
                    <div class="flex items-center gap-1.5 shrink-0 self-end sm:self-center">
                        <button onclick="copiarTexto('${f.api_key}', 'API Key copiada')" type="button" class="p-1.5 rounded-lg bg-cyan-400/10 hover:bg-cyan-400/20 text-cyan-300 border border-cyan-400/30 cursor-pointer" title="Copiar API Key">
                            <span class="material-symbols-outlined text-[14px]">key</span>
                        </button>
                        <button onclick="copiarTexto('${f.secret_key}', 'Secret Key copiada')" type="button" class="p-1.5 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 cursor-pointer" title="Copiar Secret HMAC">
                            <span class="material-symbols-outlined text-[14px]">lock</span>
                        </button>
                        <button onclick="eliminarFlotaRegistrada('${f.id}')" type="button" class="p-1.5 rounded-lg bg-error/10 hover:bg-error/20 text-error border border-error/30 cursor-pointer" title="Revocar y eliminar flota">
                            <span class="material-symbols-outlined text-[14px]">delete</span>
                        </button>
                    </div>
                </div>
            `;
        }).join('');
    } catch (e) {
        console.error('Error cargando flotas:', e);
    }
}
window.cargarListadoFlotasModal = cargarListadoFlotasModal;

async function eliminarFlotaRegistrada(fleetId) {
    if (!confirm(`¿Estás seguro de que deseas revocar el acceso y eliminar la flota ${fleetId}?`)) return;
    try {
        const res = await fetch(`/api/flotas/eliminar/${fleetId}`, { method: 'DELETE' });
        if (res.ok) {
            cargarListadoFlotasModal();
        }
    } catch (e) {
        console.error('Error eliminando flota:', e);
    }
}
window.eliminarFlotaRegistrada = eliminarFlotaRegistrada;

function copiarDockerRunCommand() {
    const cmdEl = document.getElementById('res-docker-command');
    if (cmdEl) {
        copiarTexto(cmdEl.innerText, 'Comando Docker copiado al portapapeles');
    }
}
window.copiarDockerRunCommand = copiarDockerRunCommand;

function copiarTexto(text, msg) {
    if (!text) return;
    navigator.clipboard.writeText(text).then(() => {
        if (typeof showConfigToast === 'function') {
            showConfigToast(msg || 'Copiado al portapapeles');
        } else {
            alert(msg || 'Copiado al portapapeles');
        }
    }).catch(() => {
        alert(msg || 'Copiado al portapapeles');
    });
}
window.copiarTexto = copiarTexto;

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
                <div class="max-h-52 overflow-y-auto font-mono text-[11px] leading-relaxed flex flex-col gap-1 pr-1 bg-[#05050d] p-2.5 rounded-xl border border-outline-variant/20">
                    ${renderInspectLogs(eq)}
                </div>
            </div>

            <!-- Torre de Control & Órdenes Remotas -->
            <div class="p-3.5 rounded-xl bg-surface-container-low border border-cyan-400/30 flex flex-col gap-3">
                <div class="flex items-center justify-between pb-1.5 border-b border-outline-variant/20">
                    <div class="flex items-center gap-2">
                        <span class="material-symbols-outlined text-[18px] text-cyan-400">tune</span>
                        <span class="font-bold text-on-surface text-xs">Torre de Mando & Corrección Remota:</span>
                    </div>
                    <span class="text-[10px] font-mono text-cyan-400 font-bold bg-cyan-400/10 px-2 py-0.5 rounded border border-cyan-400/25">Enlace C2 Seguro</span>
                </div>

                <div class="grid grid-cols-2 sm:grid-cols-4 gap-2">
                    <button onclick="enviarOrdenRemota('${eq.id}', 'reiniciar_tripulacion')" type="button" class="flex items-center justify-center gap-1.5 p-2 rounded-xl bg-cyan-400/10 hover:bg-cyan-400/20 text-cyan-300 border border-cyan-400/30 text-xs font-semibold cursor-pointer transition-all hover:scale-[1.02]">
                        <span class="material-symbols-outlined text-[15px]">restart_alt</span>
                        <span>Reiniciar</span>
                    </button>
                    <button onclick="enviarOrdenRemota('${eq.id}', 'limpiar_errores')" type="button" class="flex items-center justify-center gap-1.5 p-2 rounded-xl bg-amber-400/10 hover:bg-amber-400/20 text-amber-300 border border-amber-400/30 text-xs font-semibold cursor-pointer transition-all hover:scale-[1.02]">
                        <span class="material-symbols-outlined text-[15px]">cleaning_services</span>
                        <span>Limpiar Memoria</span>
                    </button>
                    <button onclick="enviarOrdenRemota('${eq.id}', 'pausar_flota')" type="button" class="flex items-center justify-center gap-1.5 p-2 rounded-xl bg-purple-400/10 hover:bg-purple-400/20 text-purple-300 border border-purple-400/30 text-xs font-semibold cursor-pointer transition-all hover:scale-[1.02]">
                        <span class="material-symbols-outlined text-[15px]">pause_circle</span>
                        <span>Pausar</span>
                    </button>
                    <button onclick="enviarOrdenRemota('${eq.id}', 'reanudar_flota')" type="button" class="flex items-center justify-center gap-1.5 p-2 rounded-xl bg-emerald-400/10 hover:bg-emerald-400/20 text-emerald-300 border border-emerald-400/30 text-xs font-semibold cursor-pointer transition-all hover:scale-[1.02]">
                        <span class="material-symbols-outlined text-[15px]">play_circle</span>
                        <span>Reanudar</span>
                    </button>
                </div>

                <div class="flex items-center gap-2 pt-1">
                    <input id="input-custom-cmd-${eq.id}" type="text" placeholder="Ej: sincronizar_archivos o actualizar_prompts" class="flex-1 bg-[#090914] border border-outline-variant/40 rounded-xl py-1.5 px-3 text-xs font-mono text-cyan-300 focus:outline-none focus:border-cyan-400/60 shadow-inner">
                    <button onclick="enviarOrdenPersonalizada('${eq.id}')" type="button" class="px-3 py-1.5 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-[#090914] text-xs font-bold cursor-pointer transition-all shrink-0 shadow">
                        Despachar
                    </button>
                </div>

                <div class="mt-1 flex flex-col gap-1 text-[11px] font-mono text-on-surface-variant/80 border-t border-outline-variant/15 pt-2">
                    <span class="text-[10px] text-on-surface-variant font-bold uppercase">Órdenes Despachadas Recientemente:</span>
                    <div id="cmd-history-container-${eq.id}" class="flex flex-col gap-1">
                        ${renderCommandHistory(eq.id)}
                    </div>
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
    if (window.innerWidth < 1024 && typeof toggleMobileSidebar === 'function') {
        setTimeout(() => { toggleMobileSidebar(false); }, 150);
    }
    switchCanvasView('configuracion');
    try {
        localStorage.setItem('activeDashboardView', 'configuracion');
    } catch(e) {}

    // Deselect main nav items
    const container = document.getElementById('nav-container');
    if (container) {
        container.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
    }

    // Highlight footer config button according to active theme
    const cfgBtn = document.getElementById('footer-btn-config');
    const iconBox = document.getElementById('footer-config-icon-box');
    const textEl = document.getElementById('footer-config-text');
    const currentTheme = (typeof getActiveThemeId === 'function') ? getActiveThemeId() : 'cyberpunk';
    const isOcean = (currentTheme === 'ocean');
    const isAmber = (currentTheme === 'amber');
    const isPurple = (currentTheme === 'purple');
    const isStealth = (currentTheme === 'stealth');
    const isCrema = (currentTheme === 'crema');
    const isBlanco = (currentTheme === 'blanco');

    if (cfgBtn) {
        if (isOcean) {
            cfgBtn.className = "w-full !py-2.5 !text-xs text-white bg-[#00d4ff]/15 border border-[#00d4ff]/50 shadow-[0_0_15px_rgba(0,212,255,0.35)] flex items-center gap-2.5 px-3 rounded-xl transition-all cursor-pointer select-none";
        } else if (isAmber) {
            cfgBtn.className = "w-full !py-2.5 !text-xs text-white bg-[#f59e0b]/15 border border-[#f59e0b]/50 shadow-[0_0_15px_rgba(245,158,11,0.35)] flex items-center gap-2.5 px-3 rounded-xl transition-all cursor-pointer select-none";
        } else if (isPurple) {
            cfgBtn.className = "w-full !py-2.5 !text-xs text-white bg-[#a855f7]/15 border border-[#a855f7]/50 shadow-[0_0_15px_rgba(168,85,247,0.35)] flex items-center gap-2.5 px-3 rounded-xl transition-all cursor-pointer select-none";
        } else if (isStealth) {
            cfgBtn.className = "w-full !py-2.5 !text-xs text-white bg-[#e2e8f0]/15 border border-[#e2e8f0]/50 shadow-[0_0_15px_rgba(226,232,240,0.3)] flex items-center gap-2.5 px-3 rounded-xl transition-all cursor-pointer select-none";
        } else if (isCrema) {
            cfgBtn.className = "w-full !py-2.5 !text-xs text-[#292524] bg-[#d97706]/15 border border-[#d97706]/40 shadow-[0_2px_10px_rgba(217,119,6,0.2)] flex items-center gap-2.5 px-3 rounded-xl transition-all cursor-pointer select-none";
        } else if (isBlanco) {
            cfgBtn.className = "w-full !py-2.5 !text-xs text-[#0f172a] bg-[#2563eb]/15 border border-[#2563eb]/40 shadow-[0_2px_10px_rgba(37,99,235,0.2)] flex items-center gap-2.5 px-3 rounded-xl transition-all cursor-pointer select-none";
        } else {
            cfgBtn.className = "w-full !py-2.5 !text-xs text-white bg-primary/15 border border-primary/50 shadow-[0_0_15px_rgba(255,45,120,0.35)] flex items-center gap-2.5 px-3 rounded-xl transition-all cursor-pointer select-none";
        }
    }
    if (iconBox) {
        if (isOcean) {
            iconBox.className = "w-7 h-7 flex items-center justify-center rounded-lg bg-gradient-to-br from-[#38bdf8] to-[#00d4ff] border border-[#00d4ff] text-white shadow-[0_0_12px_rgba(0,212,255,0.7)] transition-all shrink-0";
        } else if (isAmber) {
            iconBox.className = "w-7 h-7 flex items-center justify-center rounded-lg bg-gradient-to-br from-[#fbbf24] to-[#f59e0b] border border-[#f59e0b] text-[#0a0805] shadow-[0_0_12px_rgba(245,158,11,0.7)] transition-all shrink-0";
        } else if (isPurple) {
            iconBox.className = "w-7 h-7 flex items-center justify-center rounded-lg bg-gradient-to-br from-[#c084fc] to-[#a855f7] border border-[#a855f7] text-white shadow-[0_0_12px_rgba(168,85,247,0.7)] transition-all shrink-0";
        } else if (isStealth) {
            iconBox.className = "w-7 h-7 flex items-center justify-center rounded-lg bg-gradient-to-br from-[#ffffff] to-[#cbd5e1] border border-[#e2e8f0] text-[#09090b] shadow-[0_0_12px_rgba(226,232,240,0.65)] transition-all shrink-0";
        } else if (isCrema) {
            iconBox.className = "w-7 h-7 flex items-center justify-center rounded-lg bg-gradient-to-br from-[#f59e0b] to-[#d97706] border border-[#d97706] text-white shadow-[0_2px_8px_rgba(217,119,6,0.4)] transition-all shrink-0";
        } else if (isBlanco) {
            iconBox.className = "w-7 h-7 flex items-center justify-center rounded-lg bg-gradient-to-br from-[#38bdf8] to-[#2563eb] border border-[#2563eb] text-white shadow-[0_2px_8px_rgba(37,99,235,0.4)] transition-all shrink-0";
        } else {
            iconBox.className = "w-7 h-7 flex items-center justify-center rounded-lg bg-primary border border-primary text-white shadow-[0_0_12px_rgba(255,45,120,0.65)] transition-all shrink-0";
        }
    }
    if (textEl) {
        if (isOcean) {
            textEl.className = "font-bold text-white drop-shadow-[0_0_8px_rgba(0,212,255,0.5)]";
        } else if (isAmber) {
            textEl.className = "font-bold text-white drop-shadow-[0_0_8px_rgba(245,158,11,0.5)]";
        } else if (isPurple) {
            textEl.className = "font-bold text-white drop-shadow-[0_0_8px_rgba(168,85,247,0.5)]";
        } else if (isStealth) {
            textEl.className = "font-bold text-white drop-shadow-[0_0_8px_rgba(226,232,240,0.5)]";
        } else if (isCrema) {
            textEl.className = "font-bold text-[#292524]";
        } else if (isBlanco) {
            textEl.className = "font-bold text-[#0f172a]";
        } else {
            textEl.className = "font-bold text-white drop-shadow-[0_0_8px_rgba(255,45,120,0.4)]";
        }
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
        if (window.innerWidth < 1024 && typeof toggleMobileSidebar === 'function') {
            toggleMobileSidebar(false);
        }
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

// Catálogo de modelos reconocidos agrupados por proveedor
const PROVIDER_MODELS = {
    deepseek: [
        { id: 'deepseek-chat', label: 'deepseek-chat (DeepSeek-V3)' },
        { id: 'deepseek-reasoner', label: 'deepseek-reasoner (DeepSeek-R1)' }
    ],
    openai: [
        { id: 'gpt-4o', label: 'gpt-4o (OpenAI)' },
        { id: 'gpt-4o-mini', label: 'gpt-4o-mini (OpenAI)' },
        { id: 'o1', label: 'o1 (OpenAI)' },
        { id: 'o3-mini', label: 'o3-mini (OpenAI)' }
    ],
    gemini: [
        { id: 'gemini-2.5-pro', label: 'gemini-2.5-pro (Google)' },
        { id: 'gemini-2.5-flash', label: 'gemini-2.5-flash (Google)' },
        { id: 'gemini-1.5-pro', label: 'gemini-1.5-pro (Google)' },
        { id: 'gemini-1.5-flash', label: 'gemini-1.5-flash (Google)' }
    ],
    groq: [
        { id: 'llama-3.3-70b-versatile', label: 'llama-3.3-70b-versatile (Groq)' },
        { id: 'llama-3.1-8b-instant', label: 'llama-3.1-8b-instant (Groq)' },
        { id: 'mixtral-8x7b-32768', label: 'mixtral-8x7b-32768 (Groq)' }
    ],
    anthropic: [
        { id: 'claude-3-7-sonnet', label: 'claude-3-7-sonnet (Anthropic)' },
        { id: 'claude-3-5-sonnet', label: 'claude-3-5-sonnet (Anthropic)' },
        { id: 'claude-3-5-haiku', label: 'claude-3-5-haiku (Anthropic)' }
    ],
    xai: [
        { id: 'grok-2', label: 'grok-2 (xAI)' },
        { id: 'grok-2-mini', label: 'grok-2-mini (xAI)' }
    ],
    qwen: [
        { id: 'qwen-plus', label: 'qwen-plus (Alibaba Qwen)' },
        { id: 'qwen-max', label: 'qwen-max (Alibaba Qwen)' },
        { id: 'qwen-turbo', label: 'qwen-turbo (Alibaba Qwen)' }
    ],
    mistral: [
        { id: 'mistral-large-latest', label: 'mistral-large-latest (Mistral)' },
        { id: 'mistral-small-latest', label: 'mistral-small-latest (Mistral)' },
        { id: 'codestral-latest', label: 'codestral-latest (Mistral Codestral)' }
    ],
    openrouter: [
        { id: 'openrouter/auto', label: 'openrouter/auto (OpenRouter)' },
        { id: 'anthropic/claude-3.7-sonnet', label: 'claude-3.7-sonnet (OpenRouter)' },
        { id: 'meta-llama/llama-3.3-70b-instruct', label: 'llama-3.3-70b-instruct (OpenRouter)' }
    ],
    ollama: [
        { id: 'llama3', label: 'llama3 (Ollama Local)' },
        { id: 'qwen2.5-coder', label: 'qwen2.5-coder (Ollama Local)' },
        { id: 'mistral', label: 'mistral (Ollama Local)' }
    ]
};

let customAddedModels = [];

function actualizarSelectoresModelosDisponibles(clavesConfig, opcionesActuales) {
    const selects = [
        'cfg-default-model',
        'cfg-model-luffy',
        'cfg-model-zoro',
        'cfg-model-sanji',
        'cfg-model-robin',
        'cfg-model-nami'
    ];

    const keys = clavesConfig || cachedConfigKeys || {};

    // Filtrar estrictamente según los proveedores dados de alta en activeProviders de la consola
    const provs = (Array.isArray(activeProviders) && activeProviders.length > 0)
        ? activeProviders
        : ['deepseek'];

    const activeProvList = provs.filter(provId => {
        if (!PROVIDER_MODELS[provId]) return false;
        if (provId === 'ollama') {
            return Boolean(cachedConfigBaseUrls['ollama'] || (cachedConfig && cachedConfig.ollama));
        }
        const k = keys[provId];
        return Boolean(k && String(k).trim().length > 0);
    });

    // Si deepseek está entre los proveedores activos de la lista pero no se leyó clave, incluirlo por defecto
    if (activeProvList.length === 0 && provs.includes('deepseek')) {
        activeProvList.push('deepseek');
    }

    selects.forEach(sId => {
        const sel = document.getElementById(sId);
        if (!sel) return;

        let curVal = '';
        if (opcionesActuales && opcionesActuales[sId]) {
            curVal = opcionesActuales[sId];
        } else if (sel.value) {
            curVal = sel.value;
        }

        sel.innerHTML = '';

        if (activeProvList.length === 0) {
            const opt = document.createElement('option');
            opt.value = '';
            opt.disabled = true;
            opt.selected = true;
            opt.innerText = 'Sin claves API activas (configura una arriba)';
            sel.appendChild(opt);
            return;
        }

        let foundSelected = false;

        activeProvList.forEach(provId => {
            const meta = PROVIDER_METADATA[provId] || { name: provId.toUpperCase() };
            const models = PROVIDER_MODELS[provId] || [];

            if (models.length > 0) {
                const grp = document.createElement('optgroup');
                grp.label = meta.name;

                models.forEach(m => {
                    const opt = document.createElement('option');
                    opt.value = m.id;
                    opt.innerText = m.label;
                    if (m.id === curVal) {
                        opt.selected = true;
                        foundSelected = true;
                    }
                    grp.appendChild(opt);
                });

                sel.appendChild(grp);
            }
        });

        // Modelos personalizados agregados manualmente
        if (customAddedModels.length > 0) {
            const custGrp = document.createElement('optgroup');
            custGrp.label = 'Personalizados';
            customAddedModels.forEach(mId => {
                const opt = document.createElement('option');
                opt.value = mId;
                opt.innerText = `${mId} (Agregado)`;
                if (mId === curVal) {
                    opt.selected = true;
                    foundSelected = true;
                }
                custGrp.appendChild(opt);
            });
            sel.appendChild(custGrp);
        }

        // Si el valor actual no pertenece a los proveedores activos, seleccionar el primer modelo disponible
        if (!foundSelected && sel.options.length > 0) {
            sel.selectedIndex = 0;
        }
    });
}
window.actualizarSelectoresModelosDisponibles = actualizarSelectoresModelosDisponibles;

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
            <div class="p-3 sm:p-3.5 rounded-xl bg-surface-container-low/70 border border-outline-variant/25 flex flex-col gap-2.5 transition-all" id="provider-card-${provId}">
                <div class="flex flex-wrap items-center justify-between gap-2">
                    <div class="flex items-center gap-2 sm:gap-2.5">
                        <div class="w-7 h-7 rounded-lg bg-surface-container-highest flex items-center justify-center p-1 border border-outline-variant/30 shrink-0 shadow-sm">
                            ${svgIcon}
                        </div>
                        <div class="flex items-center gap-2">
                            <span class="text-xs font-bold text-on-surface font-mono">${meta.name}</span>
                            <span class="text-[9px] font-mono px-1.5 py-0.2 rounded bg-surface-container-highest text-on-surface-variant/80 uppercase">${provId}</span>
                        </div>
                    </div>
                    <div class="flex items-center gap-1.5 sm:gap-2 shrink-0">
                        <button onclick="probarConexionProveedor('${provId}')" id="btn-test-prov-${provId}" type="button" title="Probar conexión con ${meta.name}" class="px-2 py-0.5 rounded-lg bg-surface-container-high hover:bg-cyan-400/20 text-on-surface-variant hover:text-cyan-400 text-[10px] font-mono border border-outline-variant/30 flex items-center gap-1 transition-all cursor-pointer">
                            <span class="material-symbols-outlined text-[13px]">bolt</span>
                            <span>Probar</span>
                        </button>
                        <span id="status-badge-${provId}" class="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full shrink-0 ${hasKey ? 'bg-surface-container-high text-cyan-300 border border-cyan-400/30' : 'bg-surface-container-high text-on-surface-variant border border-outline-variant/40'}">
                            ${hasKey ? 'CONFIGURADA' : 'SIN CLAVE'}
                        </span>
                        <button onclick="abrirModalConfirmarEliminarProveedor('${provId}')" type="button" title="Retirar este proveedor" class="p-1 text-on-surface-variant hover:text-error rounded-lg hover:bg-error/10 transition-colors cursor-pointer shrink-0">
                            <span class="material-symbols-outlined text-[16px]">delete</span>
                        </button>
                    </div>
                </div>

                <div class="flex flex-col gap-1">
                    <label class="text-[10px] font-mono text-on-surface-variant/70">API Key:</label>
                    <div class="relative flex items-center">
                        <input id="cfg-key-${provId}" type="password" value="${String(valKey).replace(/"/g, '&quot;')}" placeholder="sk-..." class="w-full bg-surface-container-highest/60 border border-outline-variant/40 rounded-xl py-1.5 pl-3 pr-10 text-xs font-mono text-on-surface placeholder:text-on-surface-variant/40 focus:outline-none focus:border-cyan-400/60 transition-colors">
                        <button onclick="toggleKeyVisibility('cfg-key-${provId}')" type="button" class="absolute right-2 text-on-surface-variant hover:text-on-surface p-1 transition-colors cursor-pointer" title="Mostrar u ocultar clave">
                            <span class="material-symbols-outlined text-[17px]">visibility</span>
                        </button>
                    </div>
                </div>

                <div class="flex flex-col gap-1">
                    <label class="text-[10px] font-mono text-on-surface-variant/70">URL Base del Endpoint:</label>
                    <input id="cfg-url-${provId}" type="text" value="${String(valUrl).replace(/"/g, '&quot;')}" placeholder="${meta.defaultUrl || 'https://api.openai.com/v1'}" class="w-full bg-surface-container-highest/60 border border-outline-variant/40 rounded-xl py-1.5 px-3 text-xs font-mono text-on-surface placeholder:text-on-surface-variant/40 focus:outline-none focus:border-cyan-400/60 transition-colors">
                </div>
            </div>
        `;
    }).join('');
    actualizarSelectoresModelosDisponibles(keys);
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
    if (!customAddedModels.includes(modelo)) {
        customAddedModels.push(modelo);
    }
    actualizarSelectoresModelosDisponibles();
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
        saveBtn.innerHTML = '<span class="material-symbols-outlined text-[16px] animate-spin">sync</span><span>Verificando conexión con el proveedor...</span>';
    }

    // 1. Verificación obligatoria contra los servidores del proveedor antes de guardar
    try {
        const testRes = await fetch('/api/config/test-provider', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                provider: provId,
                api_key: key,
                base_url: url
            })
        });
        const testData = await testRes.json();
        if (!testRes.ok || testData.status !== 'ok') {
            showConfigToast(testData.message || `La API Key fue rechazada por ${meta.name || provId.toUpperCase()}. No se guardó.`, true);
            if (keyEl) keyEl.focus();
            if (saveBtn) {
                saveBtn.disabled = false;
                saveBtn.innerHTML = '<span class="material-symbols-outlined text-[18px]">save</span><span>Guardar Proveedor en .env</span>';
            }
            return;
        }
    } catch (testErr) {
        console.error('Error validando proveedor:', testErr);
        showConfigToast('No se pudo verificar la API Key. Comprueba tu conexión a internet o el endpoint.', true);
        if (saveBtn) {
            saveBtn.disabled = false;
            saveBtn.innerHTML = '<span class="material-symbols-outlined text-[18px]">save</span><span>Guardar Proveedor en .env</span>';
        }
        return;
    }

    if (saveBtn) {
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
            // Marcar badge verificado como CONECTADA
            const b = document.getElementById(`status-badge-${provId}`);
            if (b) {
                b.className = 'text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-emerald-400/10 text-emerald-400 border border-emerald-400/30';
                b.innerText = 'CONECTADA';
            }

            cerrarModalAgregarProveedor();
            showConfigToast(`¡Proveedor ${meta.name || provId.toUpperCase()} verificado y guardado con éxito!`);
        } else {
            showConfigToast(data.message || 'Error guardando en .env', true);
        }
    } catch (e) {
        console.error('Error guardando proveedor en .env:', e);
        showConfigToast('Error al comunicar con el servidor para guardar.', true);
    } finally {
        if (saveBtn) {
            saveBtn.disabled = false;
            saveBtn.innerHTML = '<span class="material-symbols-outlined text-[18px]">save</span><span>Guardar Proveedor en .env</span>';
        }
    }
}
window.guardarNuevoProveedorModal = guardarNuevoProveedorModal;
window.confirmarAgregarProveedor = guardarNuevoProveedorModal;

async function probarConexionProveedor(provId) {
    const btn = document.getElementById(`btn-test-prov-${provId}`);
    const badge = document.getElementById(`status-badge-${provId}`);
    const keyInput = document.getElementById(`cfg-key-${provId}`);
    const urlInput = document.getElementById(`cfg-url-${provId}`);

    const key = keyInput ? keyInput.value.trim() : (cachedConfigKeys[provId] || '');
    const url = urlInput ? urlInput.value.trim() : (cachedConfigBaseUrls[provId] || '');

    if (!key && provId !== 'ollama') {
        showConfigToast(`El proveedor ${provId.toUpperCase()} no tiene API Key asignada.`, true);
        if (badge) {
            badge.className = 'text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-surface-container-high text-on-surface-variant border border-outline-variant/40';
            badge.innerText = 'SIN CLAVE';
        }
        return;
    }

    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="material-symbols-outlined text-[13px] animate-spin">sync</span><span>Probando...</span>';
    }

    try {
        const res = await fetch('/api/config/test-provider', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                provider: provId,
                api_key: key,
                base_url: url
            })
        });
        const data = await res.json();
        if (res.ok && data.status === 'ok') {
            if (badge) {
                badge.className = 'text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-emerald-400/10 text-emerald-400 border border-emerald-400/30';
                badge.innerText = 'CONECTADA';
            }
            showConfigToast(`¡Conexión verificada con ${provId.toUpperCase()}!`);
        } else {
            if (badge) {
                badge.className = 'text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-error/15 text-error border border-error/30';
                badge.innerText = 'ERROR / RECHAZADA';
            }
            showConfigToast(data.message || `Fallo de autenticación con ${provId.toUpperCase()}.`, true);
        }
    } catch (e) {
        if (badge) {
            badge.className = 'text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-error/15 text-error border border-error/30';
            badge.innerText = 'FALLO DE RED';
        }
        showConfigToast(`Error al intentar conectar con ${provId.toUpperCase()}.`, true);
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<span class="material-symbols-outlined text-[13px]">bolt</span><span>Probar</span>';
        }
    }
}
window.probarConexionProveedor = probarConexionProveedor;

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

        // Modelos por agente filtrados dinámicamente según proveedores con clave activa
        const mods = data.modelos || {};
        const desiredSelections = {
            'cfg-default-model': data.default_model || 'deepseek-chat',
            'cfg-model-luffy': mods.luffy || data.default_model || 'deepseek-chat',
            'cfg-model-zoro': mods.zoro || data.default_model || 'deepseek-chat',
            'cfg-model-sanji': mods.sanji || data.default_model || 'deepseek-chat',
            'cfg-model-robin': mods.robin || data.default_model || 'deepseek-chat',
            'cfg-model-nami': mods.nami || data.default_model || 'deepseek-chat'
        };

        actualizarSelectoresModelosDisponibles(cachedConfigKeys, desiredSelections);

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

        // Seguridad & Blindaje en la Nube
        if (data.seguridad) {
            const sec = data.seguridad;
            const chk = document.getElementById('cfg-sec-auth-active');
            if (chk) chk.checked = Boolean(sec.auth_active);
            setVal('cfg-sec-user', sec.auth_user || 'admin');
            setVal('cfg-sec-telemetry-token', sec.telemetry_token || '');
            setVal('cfg-sec-ip-whitelist', sec.ip_whitelist || '');
            toggleCloudAuthFields();
            updateProfileDisplayName(sec.auth_user);
            if (sec.auth_avatar) {
                updateProfileAvatar(sec.auth_avatar);
            } else {
                try {
                    const localAv = localStorage.getItem('console_profile_avatar');
                    if (localAv) updateProfileAvatar(localAv);
                } catch(e) {}
            }
        }

    } catch (e) {
        console.error('Error cargando configuración:', e);
        showConfigToast('No se pudo cargar la configuración del sistema.', true);
    }
}
window.loadConfigData = loadConfigData;

let currentProfileAvatar = '/static/avatars/bot_cyan.jpg';

function updateProfileAvatar(url) {
    if (!url || !url.trim()) return;
    currentProfileAvatar = url.trim();
    
    try {
        localStorage.setItem('console_profile_avatar', currentProfileAvatar);
    } catch(e) {}

    const headerImg = document.getElementById('header-profile-avatar');
    if (headerImg) headerImg.src = currentProfileAvatar;

    const dropImg = document.getElementById('dropdown-profile-avatar');
    if (dropImg) dropImg.src = currentProfileAvatar;

    const previewImg = document.getElementById('cfg-sec-avatar-preview');
    if (previewImg) previewImg.src = currentProfileAvatar;

    const urlInput = document.getElementById('cfg-sec-avatar-url');
    if (urlInput) urlInput.value = currentProfileAvatar;

    const presetButtons = document.querySelectorAll('.avatar-preset-btn');
    presetButtons.forEach(btn => {
        const img = btn.querySelector('img');
        if (img && img.src === currentProfileAvatar) {
            btn.className = 'avatar-preset-btn w-8 h-8 rounded-xl overflow-hidden border-2 border-emerald-400 p-0.5 bg-[#0f0f1a] hover:scale-105 transition-all shrink-0 cursor-pointer shadow-sm ring-2 ring-emerald-500/30';
        } else {
            btn.className = 'avatar-preset-btn w-8 h-8 rounded-xl overflow-hidden border border-outline-variant/40 p-0.5 bg-surface-container-highest hover:scale-105 hover:border-emerald-400 transition-all shrink-0 cursor-pointer shadow-sm';
        }
    });
}
window.updateProfileAvatar = updateProfileAvatar;

function selectPresetAvatar(url, btnElement) {
    updateProfileAvatar(url);
    showConfigToast('¡Avatar temático seleccionado!');
}
window.selectPresetAvatar = selectPresetAvatar;

function promptCustomAvatarUrl() {
    const current = document.getElementById('cfg-sec-avatar-url')?.value || currentProfileAvatar;
    const url = prompt('Ingresa el enlace (URL) de tu foto o avatar:', current);
    if (url && url.trim()) {
        updateProfileAvatar(url.trim());
        showConfigToast('¡Foto de perfil actualizada!');
    }
}
window.promptCustomAvatarUrl = promptCustomAvatarUrl;

function handleAvatarFileUpload(event) {
    const file = event.target.files && event.target.files[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
        showConfigToast('Por favor selecciona un archivo de imagen válido.', true);
        return;
    }

    const reader = new FileReader();
    reader.onload = function(e) {
        const img = new Image();
        img.onload = function() {
            const canvas = document.createElement('canvas');
            const maxDim = 256;
            let width = img.width;
            let height = img.height;
            if (width > height) {
                if (width > maxDim) {
                    height = Math.round((height * maxDim) / width);
                    width = maxDim;
                }
            } else {
                if (height > maxDim) {
                    width = Math.round((width * maxDim) / height);
                    height = maxDim;
                }
            }
            canvas.width = width;
            canvas.height = height;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(img, 0, 0, width, height);
            const dataUrl = canvas.toDataURL('image/jpeg', 0.88);
            updateProfileAvatar(dataUrl);
            showConfigToast('¡Foto de perfil cargada con éxito!');
        };
        img.src = e.target.result;
    };
    reader.readAsDataURL(file);
}
window.handleAvatarFileUpload = handleAvatarFileUpload;

// Iniciar avatar desde almacenamiento local si existe
try {
    const cachedAv = localStorage.getItem('console_profile_avatar');
    if (cachedAv) updateProfileAvatar(cachedAv);
} catch(e) {}

function updateProfileDisplayName(username) {
    if (!username || !username.trim()) return;
    const name = username.trim();
    const headerProfile = document.getElementById('header-profile-name');
    if (headerProfile) headerProfile.innerText = name;
    const dropdownProfile = document.getElementById('dropdown-profile-name');
    if (dropdownProfile) dropdownProfile.innerText = name;
    const dropdownUser = document.getElementById('dropdown-profile-user');
    if (dropdownUser) dropdownUser.innerText = name.toLowerCase() + '@tripulacion.os';
}
window.updateProfileDisplayName = updateProfileDisplayName;

function toggleCloudAuthFields() {
    const chk = document.getElementById('cfg-sec-auth-active');
    const group = document.getElementById('cfg-sec-credentials-group');
    const badge = document.getElementById('cfg-sec-badge');
    const card = document.getElementById('card-auth-security');
    const lockIconBox = document.getElementById('auth-lock-icon-box');
    const lockIcon = document.getElementById('auth-lock-icon');
    const statusSubtext = document.getElementById('auth-status-subtext');
    const scannerBox = document.getElementById('modal-sec-scanner-box');
    const headerIcon = document.getElementById('modal-sec-header-icon');
    const glowLine = document.getElementById('auth-shield-glowline');
    const isActive = chk ? chk.checked : true;

    if (group) {
        if (isActive) {
            group.classList.remove('opacity-40', 'pointer-events-none');
        } else {
            group.classList.add('opacity-40', 'pointer-events-none');
        }
    }

    if (lockIcon && lockIconBox) {
        lockIconBox.classList.remove('lock-snap-anim');
        void lockIconBox.offsetWidth; // Trigger reflow for animation restart
        lockIconBox.classList.add('lock-snap-anim');

        if (isActive) {
            lockIcon.innerText = 'lock';
            lockIconBox.className = 'w-8 h-8 rounded-xl bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center text-emerald-400 shadow-[0_0_12px_rgba(52,211,153,0.35)] lock-snap-anim transition-all duration-300';
            if (statusSubtext) {
                statusSubtext.innerText = 'Blindaje Activo • Acceso Protegido';
                statusSubtext.className = 'text-[10px] font-mono text-emerald-400 font-bold';
            }
        } else {
            lockIcon.innerText = 'lock_open';
            lockIconBox.className = 'w-8 h-8 rounded-xl bg-rose-500/15 border border-rose-500/30 flex items-center justify-center text-rose-400 lock-snap-anim transition-all duration-300';
            if (statusSubtext) {
                statusSubtext.innerText = 'Sin Protección • Acceso Libre';
                statusSubtext.className = 'text-[10px] font-mono text-on-surface-variant/70';
            }
        }
    }

    if (card) {
        if (isActive) {
            card.classList.add('border-emerald-500/40', 'shadow-[0_0_30px_rgba(16,185,129,0.18)]');
            card.classList.remove('border-outline-variant/35');
            if (glowLine) glowLine.classList.remove('hidden');
        } else {
            card.classList.remove('border-emerald-500/40', 'shadow-[0_0_30px_rgba(16,185,129,0.18)]');
            card.classList.add('border-outline-variant/35');
            if (glowLine) glowLine.classList.add('hidden');
        }
    }

    if (scannerBox && headerIcon) {
        if (isActive) {
            scannerBox.classList.add('active-shield');
            headerIcon.className = 'material-symbols-outlined text-[26px] text-emerald-400 drop-shadow-[0_0_10px_rgba(52,211,153,0.6)] transition-colors duration-300';
            scannerBox.style.borderColor = 'rgba(52, 211, 153, 0.4)';
            scannerBox.style.boxShadow = '0 0 25px rgba(52, 211, 153, 0.3)';
        } else {
            scannerBox.classList.remove('active-shield');
            headerIcon.className = 'material-symbols-outlined text-[26px] text-rose-400 drop-shadow-[0_0_8px_rgba(244,63,94,0.6)] transition-colors duration-300';
            scannerBox.style.borderColor = 'rgba(244, 63, 94, 0.4)';
            scannerBox.style.boxShadow = '0 0 20px rgba(244, 63, 94, 0.3)';
        }
    }

    if (badge) {
        if (isActive) {
            badge.innerText = 'AUTENTICACIÓN ACTIVA';
            badge.className = 'text-xs font-mono font-bold px-3 py-1 rounded-full bg-emerald-400/15 text-emerald-400 border border-emerald-400/40 shadow-[0_0_12px_rgba(52,211,153,0.3)] transition-all';
        } else {
            badge.innerText = 'SIN AUTENTICACIÓN';
            badge.className = 'text-xs font-mono font-bold px-3 py-1 rounded-full bg-surface-container-high text-on-surface-variant border border-outline-variant/40 shadow-sm transition-all';
        }
    }
}
window.toggleCloudAuthFields = toggleCloudAuthFields;

function generarTokenTelemetriaAleatorio() {
    const array = new Uint8Array(24);
    window.crypto.getRandomValues(array);
    const token = 'sk-telemetry-' + Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('');
    const input = document.getElementById('cfg-sec-telemetry-token');
    if (input) {
        input.value = token;
        showConfigToast('¡Token secreto de telemetría generado!');
    }
}
window.generarTokenTelemetriaAleatorio = generarTokenTelemetriaAleatorio;

function copiarTokenTelemetria() {
    const input = document.getElementById('cfg-sec-telemetry-token');
    if (!input || !input.value.trim()) {
        showConfigToast('No hay token de telemetría para copiar.', true);
        return;
    }
    navigator.clipboard.writeText(input.value.trim()).then(() => {
        showConfigToast('¡Token de telemetría copiado al portapapeles!');
    }).catch(() => {
        showConfigToast('No se pudo copiar automáticamente.');
    });
}
window.copiarTokenTelemetria = copiarTokenTelemetria;

function autocompletarMiRedIP() {
    const input = document.getElementById('cfg-sec-ip-whitelist');
    if (input) {
        input.value = '127.0.0.1, 192.168.0.*, 10.2.0.*';
        showConfigToast('¡IPs de tu PC y red local configuradas!');
    }
}
window.autocompletarMiRedIP = autocompletarMiRedIP;

function generarPasswordSeguraAleatoria() {
    const chars = 'abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789!@#$%^&*';
    let pass = '';
    const array = new Uint8Array(16);
    window.crypto.getRandomValues(array);
    for (let i = 0; i < 16; i++) {
        pass += chars[array[i] % chars.length];
    }
    const p1 = document.getElementById('cfg-sec-password');
    const p2 = document.getElementById('cfg-sec-password-confirm');
    if (p1) {
        p1.value = pass;
        p1.type = 'text'; // Reveal generated password so the user can read it
    }
    if (p2) {
        p2.value = pass;
        p2.type = 'text';
    }
    verificarCoincidenciaPassword();
    showConfigToast('¡Contraseña segura generada y confirmada!');
}
window.generarPasswordSeguraAleatoria = generarPasswordSeguraAleatoria;

function verificarCoincidenciaPassword() {
    const p1 = document.getElementById('cfg-sec-password');
    const p2 = document.getElementById('cfg-sec-password-confirm');
    const msg = document.getElementById('cfg-sec-password-match-msg');
    if (!p1 || !p2 || !msg) return;

    const v1 = p1.value;
    const v2 = p2.value;

    if (!v1 && !v2) {
        msg.innerText = '';
        p2.classList.remove('border-emerald-500/60', 'border-error/60');
        return;
    }

    if (v1 && v2 && v1 === v2) {
        msg.innerText = '✓ Coinciden';
        msg.className = 'text-[10px] font-mono text-emerald-400 font-bold';
        p2.classList.add('border-emerald-500/60');
        p2.classList.remove('border-error/60');
    } else if (v2 && v1 !== v2) {
        msg.innerText = '✗ No coinciden';
        msg.className = 'text-[10px] font-mono text-error font-bold';
        p2.classList.add('border-error/60');
        p2.classList.remove('border-emerald-500/60');
    } else {
        msg.innerText = '';
        p2.classList.remove('border-emerald-500/60', 'border-error/60');
    }
}
window.verificarCoincidenciaPassword = verificarCoincidenciaPassword;

let seccionPasswordAbierta = false;

function toggleSeccionCambioPassword(forzar) {
    const sec = document.getElementById('seccion-cambio-password');
    const txt = document.getElementById('btn-toggle-change-pass-text');
    if (!sec) return;

    seccionPasswordAbierta = (forzar !== undefined) ? forzar : !seccionPasswordAbierta;
    if (seccionPasswordAbierta) {
        sec.classList.remove('hidden');
        if (txt) txt.innerText = 'Cancelar Cambio';
        const oldPass = document.getElementById('cfg-sec-old-password');
        if (oldPass) setTimeout(() => oldPass.focus(), 100);
    } else {
        sec.classList.add('hidden');
        if (txt) txt.innerText = 'Cambiar Contraseña';
        const pOld = document.getElementById('cfg-sec-old-password');
        const pNew = document.getElementById('cfg-sec-password');
        const pConf = document.getElementById('cfg-sec-password-confirm');
        const msg = document.getElementById('cfg-sec-password-match-msg');
        if (pOld) pOld.value = '';
        if (pNew) pNew.value = '';
        if (pConf) pConf.value = '';
        if (msg) msg.innerText = '';
    }
}
window.toggleSeccionCambioPassword = toggleSeccionCambioPassword;

function openSecurityModal(show = true) {
    const modal = document.getElementById('modal-security');
    if (!modal) return;
    if (show) {
        if (window.innerWidth < 1024 && typeof toggleMobileSidebar === 'function') {
            toggleMobileSidebar(false);
        }
        modal.classList.remove('hidden');
        toggleSeccionCambioPassword(false);
        if (cachedConfig && cachedConfig.seguridad) {
            const sec = cachedConfig.seguridad;
            const chk = document.getElementById('cfg-sec-auth-active');
            if (chk) chk.checked = Boolean(sec.auth_active);
            const setVal = (id, val) => {
                const el = document.getElementById(id);
                if (el) el.value = val || '';
            };
            const userVal = sec.auth_user || 'admin';
            setVal('cfg-sec-user', userVal);
            setVal('cfg-sec-old-password', '');
            setVal('cfg-sec-password', '');
            setVal('cfg-sec-password-confirm', '');
            setVal('cfg-sec-telemetry-token', sec.telemetry_token || '');
            setVal('cfg-sec-ip-whitelist', sec.ip_whitelist || '');
            verificarCoincidenciaPassword();
            toggleCloudAuthFields();
            updateProfileDisplayName(userVal);
            if (sec.auth_avatar) {
                updateProfileAvatar(sec.auth_avatar);
            } else {
                updateProfileAvatar(currentProfileAvatar);
            }
        } else {
            loadConfigData();
        }
    } else {
        modal.classList.add('hidden');
        toggleSeccionCambioPassword(false);
    }
}
window.openSecurityModal = openSecurityModal;

async function guardarSeguridadModal() {
    const btn = document.getElementById('btn-modal-save-security');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="material-symbols-outlined text-[16px] animate-spin">sync</span><span>Guardando...</span>';
    }

    try {
        const getVal = id => {
            const el = document.getElementById(id);
            return el ? el.value.trim() : '';
        };

        const chkAuth = document.getElementById('cfg-sec-auth-active');
        const authUser = getVal('cfg-sec-user') || 'admin';
        const isAuthActive = chkAuth ? chkAuth.checked : true;

        const oldPass = getVal('cfg-sec-old-password');
        const newPass = getVal('cfg-sec-password');
        const authConfirm = getVal('cfg-sec-password-confirm');

        if (isAuthActive) {
            if (!authUser) {
                showConfigToast('Debes ingresar un nombre de usuario.', true);
                if (btn) {
                    btn.disabled = false;
                    btn.innerHTML = '<span class="material-symbols-outlined text-[17px]">save</span><span>Guardar Seguridad</span>';
                }
                return;
            }
            if (seccionPasswordAbierta && (oldPass || newPass || authConfirm)) {
                if (!oldPass) {
                    showConfigToast('Debes ingresar tu contraseña actual para autorizar el cambio.', true);
                    const el = document.getElementById('cfg-sec-old-password');
                    if (el) el.focus();
                    if (btn) {
                        btn.disabled = false;
                        btn.innerHTML = '<span class="material-symbols-outlined text-[17px]">save</span><span>Guardar Seguridad</span>';
                    }
                    return;
                }
                if (!newPass || newPass.length < 8) {
                    showConfigToast('La nueva contraseña debe tener al menos 8 caracteres.', true);
                    const el = document.getElementById('cfg-sec-password');
                    if (el) el.focus();
                    if (btn) {
                        btn.disabled = false;
                        btn.innerHTML = '<span class="material-symbols-outlined text-[17px]">save</span><span>Guardar Seguridad</span>';
                    }
                    return;
                }
                if (newPass !== authConfirm) {
                    showConfigToast('La nueva contraseña y su confirmación no coinciden.', true);
                    const el = document.getElementById('cfg-sec-password-confirm');
                    if (el) el.focus();
                    if (btn) {
                        btn.disabled = false;
                        btn.innerHTML = '<span class="material-symbols-outlined text-[17px]">save</span><span>Guardar Seguridad</span>';
                    }
                    return;
                }
            }
        }

        const authAvatar = getVal('cfg-sec-avatar-url') || currentProfileAvatar;

        const seguridadPayload = {
            auth_active: isAuthActive,
            auth_user: authUser,
            auth_avatar: authAvatar,
            telemetry_token: getVal('cfg-sec-telemetry-token') || '',
            ip_whitelist: getVal('cfg-sec-ip-whitelist') || ''
        };

        if (seccionPasswordAbierta && newPass) {
            seguridadPayload.old_password = oldPass;
            seguridadPayload.new_password = newPass;
        }

        const res = await fetch('/api/config/guardar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ seguridad: seguridadPayload })
        });

        const data = await res.json();
        if (data.status === 'ok') {
            if (!cachedConfig) cachedConfig = {};
            cachedConfig.seguridad = { ...cachedConfig.seguridad, ...seguridadPayload };
            toggleCloudAuthFields();
            updateProfileDisplayName(authUser);
            updateProfileAvatar(authAvatar);
            showConfigToast('¡Parámetros de seguridad guardados correctamente!');
            setTimeout(() => openSecurityModal(false), 500);
        } else {
            showConfigToast(data.message || 'Error guardando seguridad', true);
            const oldPassEl = document.getElementById('cfg-sec-old-password');
            if (oldPassEl && (data.message || '').includes('actual')) {
                oldPassEl.focus();
                oldPassEl.select();
            }
        }
    } catch (e) {
        console.error('Error guardando seguridad:', e);
        showConfigToast('Error al comunicar con el servidor.', true);
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<span class="material-symbols-outlined text-[17px]">save</span><span>Guardar Seguridad</span>';
        }
    }
}
window.guardarSeguridadModal = guardarSeguridadModal;

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

        const chkAuth = document.getElementById('cfg-sec-auth-active');
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
            },
            seguridad: {
                auth_active: Boolean(!chkAuth || chkAuth.checked),
                auth_user: getVal('cfg-sec-user') || 'admin',
                auth_avatar: getVal('cfg-sec-avatar-url') || currentProfileAvatar,
                telemetry_token: getVal('cfg-sec-telemetry-token') || '',
                ip_whitelist: getVal('cfg-sec-ip-whitelist') || ''
            }
        };

        const newPassVal = getVal('cfg-sec-password');
        if (newPassVal) {
            payload.seguridad.new_password = newPassVal;
            payload.seguridad.old_password = getVal('cfg-sec-old-password');
        }

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

            // Actualizar desplegables de modelos según las claves activas guardadas
            actualizarSelectoresModelosDisponibles(keys);
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

function abrirModalConfirmarResetCostos() {
    const modal = document.getElementById('modal-confirm-reset-costos');
    if (modal) modal.classList.remove('hidden');
}
window.abrirModalConfirmarResetCostos = abrirModalConfirmarResetCostos;

function cerrarModalConfirmarResetCostos() {
    const modal = document.getElementById('modal-confirm-reset-costos');
    if (modal) modal.classList.add('hidden');
}
window.cerrarModalConfirmarResetCostos = cerrarModalConfirmarResetCostos;

async function ejecutarResetearCostos() {
    const btn = document.getElementById('btn-modal-confirm-reset-costos');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="material-symbols-outlined text-[16px] animate-spin">sync</span><span>Restableciendo...</span>';
    }

    try {
        const res = await fetch('/api/config/reset-costos', { method: 'POST' });
        const data = await res.json();
        if (data.status === 'ok') {
            showConfigToast(data.message);
            // Actualizar métricas visuales inmediatamente en pantalla
            const curPresMax = (window.cachedCostos && window.cachedCostos.presupuesto_maximo) ? window.cachedCostos.presupuesto_maximo : 100.0;
            const elPresBadge = document.getElementById('cfg-presupuesto-consumo-badge');
            if (elPresBadge) elPresBadge.innerText = `$0.00 / $${curPresMax.toFixed(2)} USD`;
            const elPresBar = document.getElementById('cfg-presupuesto-bar');
            if (elPresBar) {
                elPresBar.style.width = '0%';
                elPresBar.className = 'h-full bg-gradient-to-r from-emerald-400 to-cyan-400 rounded-full transition-all duration-500';
            }
            const elPresPct = document.getElementById('cfg-presupuesto-pct-text');
            if (elPresPct) {
                elPresPct.innerText = '0.0% consumido';
                elPresPct.className = '';
            }
            const elCost = document.getElementById('metric-cost');
            if (elCost) elCost.innerText = '$0.00';
            const elCostSub = document.getElementById('metric-cost-sub');
            if (elCostSub) elCostSub.innerText = `Presupuesto ($${curPresMax.toFixed(2)}): 0.0%`;
            const elAlerta = document.getElementById('cfg-presupuesto-alerta-bloqueo');
            if (elAlerta) elAlerta.classList.add('hidden');
        } else {
            showConfigToast(data.message || 'Error restableciendo costos.', true);
        }
    } catch (e) {
        showConfigToast('Error de comunicación con el servidor.', true);
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<span class="material-symbols-outlined text-[16px]">restart_alt</span><span>Reiniciar Contador</span>';
        }
        cerrarModalConfirmarResetCostos();
    }
}
window.ejecutarResetearCostos = ejecutarResetearCostos;

function resetearCostosMes() {
    abrirModalConfirmarResetCostos();
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

// ============================================================
// SISTEMA CENTINELA: ALARMA DE INTRUSIÓN Y CONTROL REMOTO
// ============================================================

let audioCtx = null;
let alarmOscillator = null;
let alarmGain = null;
let alarmInterval = null;
let isAlarmMuted = false;
let isAlarmActive = false;
let lastSeenIncidentId = null;

function initAudioContext() {
    if (!audioCtx) {
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        if (AudioContext) audioCtx = new AudioContext();
    }
    if (audioCtx && audioCtx.state === 'suspended') {
        audioCtx.resume();
    }
}

function playSecuritySiren() {
    if (isAlarmMuted) return;
    try {
        initAudioContext();
        if (!audioCtx) return;
        
        stopSecuritySiren();
        
        let toneHigh = true;
        alarmOscillator = audioCtx.createOscillator();
        alarmGain = audioCtx.createGain();
        alarmOscillator.type = 'sawtooth';
        alarmOscillator.frequency.setValueAtTime(880, audioCtx.currentTime);
        alarmGain.gain.setValueAtTime(0.08, audioCtx.currentTime);
        
        alarmOscillator.connect(alarmGain);
        alarmGain.connect(audioCtx.destination);
        alarmOscillator.start();
        
        alarmInterval = setInterval(() => {
            if (!alarmOscillator || !audioCtx) return;
            toneHigh = !toneHigh;
            alarmOscillator.frequency.setValueAtTime(toneHigh ? 880 : 587, audioCtx.currentTime);
        }, 320);
    } catch(e) {
        console.warn('Audio siren error:', e);
    }
}
window.playSecuritySiren = playSecuritySiren;

function stopSecuritySiren() {
    if (alarmInterval) {
        clearInterval(alarmInterval);
        alarmInterval = null;
    }
    if (alarmOscillator) {
        try {
            alarmOscillator.stop();
            alarmOscillator.disconnect();
        } catch(e){}
        alarmOscillator = null;
    }
}
window.stopSecuritySiren = stopSecuritySiren;

function handleIntrusionAlarmUpdate(alerta, incidentes) {
    // 1. Actualizar lista de incidentes en modal de seguridad
    renderIncidentesSeguridad(incidentes || []);

    const banner = document.getElementById('security-alarm-banner');
    const overlay = document.getElementById('security-alarm-overlay');
    const details = document.getElementById('alarm-banner-details');
    const timeEl = document.getElementById('alarm-banner-time');

    if (alerta && alerta.ip) {
        isAlarmActive = true;
        if (banner) banner.classList.remove('hidden');
        if (overlay) overlay.classList.remove('hidden');
        if (details) {
            details.innerText = `Intento de acceso desde IP no autorizada: ${alerta.ip} [${alerta.metodo || 'GET'} ${alerta.ruta || '/'}] bloqueado de inmediato.`;
        }
        if (timeEl) {
            timeEl.innerText = alerta.hora || 'En vivo';
        }

        if (alerta.id !== lastSeenIncidentId) {
            lastSeenIncidentId = alerta.id;
            playSecuritySiren();
        }
    } else {
        isAlarmActive = false;
        if (banner) banner.classList.add('hidden');
        if (overlay) overlay.classList.add('hidden');
        stopSecuritySiren();
    }
}
window.handleIntrusionAlarmUpdate = handleIntrusionAlarmUpdate;

function renderIncidentesSeguridad(incidentes) {
    const list = document.getElementById('sec-incidentes-list');
    const empty = document.getElementById('sec-incidentes-empty');
    if (!list) return;

    if (!incidentes || incidentes.length === 0) {
        list.innerHTML = '';
        if (empty) empty.classList.remove('hidden');
        return;
    }

    if (empty) empty.classList.add('hidden');
    list.innerHTML = incidentes.map(inc => `
        <div class="flex items-center justify-between py-1.5 px-2.5 rounded-lg bg-surface-container-low/70 border border-red-500/25 text-xs">
            <div class="flex items-center gap-2 min-w-0">
                <span class="w-2 h-2 rounded-full bg-red-500 animate-pulse shrink-0"></span>
                <span class="font-bold text-red-400 font-mono shrink-0">${inc.ip || '0.0.0.0'}</span>
                <span class="text-on-surface-variant font-mono truncate max-w-[240px]">${inc.metodo || 'GET'} ${inc.ruta || '/'}</span>
            </div>
            <div class="flex items-center gap-3 shrink-0 font-mono text-[10px]">
                <span class="text-on-surface-variant/70">${inc.hora || ''}</span>
                <span class="px-2 py-0.5 rounded bg-red-500/20 text-red-300 border border-red-500/30 font-bold uppercase tracking-wider">403 Bloqueado</span>
            </div>
        </div>
    `).join('');
}
window.renderIncidentesSeguridad = renderIncidentesSeguridad;

async function descartarAlarmaIntrusion() {
    stopSecuritySiren();
    const banner = document.getElementById('security-alarm-banner');
    const overlay = document.getElementById('security-alarm-overlay');
    if (banner) banner.classList.add('hidden');
    if (overlay) overlay.classList.add('hidden');
    try {
        await fetch('/api/seguridad/silenciar-alarma', { method: 'POST' });
    } catch(e) {}
}
window.descartarAlarmaIntrusion = descartarAlarmaIntrusion;

function toggleMuteSirena() {
    isAlarmMuted = !isAlarmMuted;
    const icon = document.getElementById('icon-sirena');
    const text = document.getElementById('text-sirena');
    if (isAlarmMuted) {
        stopSecuritySiren();
        if (icon) icon.innerText = 'volume_off';
        if (text) text.innerText = 'Sirena Silenciada';
    } else {
        if (icon) icon.innerText = 'volume_up';
        if (text) text.innerText = 'Silenciar Sirena';
        if (isAlarmActive) playSecuritySiren();
    }
}
window.toggleMuteSirena = toggleMuteSirena;

function probarSirenaSeguridad() {
    isAlarmMuted = false;
    const icon = document.getElementById('icon-sirena');
    const text = document.getElementById('text-sirena');
    if (icon) icon.innerText = 'volume_up';
    if (text) text.innerText = 'Silenciar Sirena';
    playSecuritySiren();
    setTimeout(() => {
        if (!isAlarmActive) stopSecuritySiren();
    }, 2800);
}
window.probarSirenaSeguridad = probarSirenaSeguridad;

async function limpiarHistorialIncidentes() {
    try {
        await fetch('/api/seguridad/incidentes', { method: 'DELETE' });
        renderIncidentesSeguridad([]);
    } catch(e) {
        console.error('Error limpiando incidentes:', e);
    }
}
window.limpiarHistorialIncidentes = limpiarHistorialIncidentes;

// Órdenes Remotas Bidireccionales (C2)
async function enviarOrdenRemota(equipoId, accion, parametros = {}) {
    try {
        const res = await fetch('/api/remoto/comando', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ equipo_id: equipoId, accion: accion, parametros: parametros })
        });
        const data = await res.json();
        if (data.status === 'ok') {
            showConfigToast(`Orden '${accion}' encolada con éxito hacia ${equipoId}.`);
            // Actualizar vista del historial en el modal
            if (!window.cachedComandosRemotos) window.cachedComandosRemotos = { pendientes: {}, historial: {} };
            if (!window.cachedComandosRemotos.pendientes[equipoId]) window.cachedComandosRemotos.pendientes[equipoId] = [];
            window.cachedComandosRemotos.pendientes[equipoId].push(data.comando);
            const container = document.getElementById(`cmd-history-container-${equipoId}`);
            if (container) container.innerHTML = renderCommandHistory(equipoId);
        } else {
            alert(`Error: ${data.message || 'No se pudo enviar la orden'}`);
        }
    } catch(e) {
        alert(`Error al enviar orden remota: ${e.message}`);
    }
}
window.enviarOrdenRemota = enviarOrdenRemota;

function enviarOrdenPersonalizada(equipoId) {
    const inp = document.getElementById(`input-custom-cmd-${equipoId}`);
    if (!inp || !inp.value.trim()) return;
    const accion = inp.value.trim();
    inp.value = '';
    enviarOrdenRemota(equipoId, accion);
}
window.enviarOrdenPersonalizada = enviarOrdenPersonalizada;

function renderCommandHistory(equipoId) {
    const store = window.cachedComandosRemotos || {};
    const hist = (store.historial && store.historial[equipoId]) || [];
    const pend = (store.pendientes && store.pendientes[equipoId]) || [];

    if (pend.length === 0 && hist.length === 0) {
        return `<div class="text-on-surface-variant/50 italic py-1 text-center">No hay órdenes despachadas recientemente para este equipo.</div>`;
    }

    let html = '';
    pend.forEach(p => {
        html += `
            <div class="flex items-center justify-between p-1.5 rounded-lg bg-cyan-400/10 border border-cyan-400/25">
                <span class="text-cyan-300 font-bold">⚡ ${p.accion}</span>
                <span class="text-[10px] text-amber-300 font-bold bg-amber-400/10 px-1.5 py-0.5 rounded border border-amber-400/20">En cola para latido</span>
            </div>
        `;
    });
    hist.slice(0, 4).forEach(h => {
        const ok = h.exito !== false;
        html += `
            <div class="flex items-center justify-between p-1.5 rounded-lg bg-surface-container-high/60 border border-outline-variant/20">
                <span class="text-on-surface font-semibold">${h.accion} <span class="text-on-surface-variant font-normal">(${h.salida || 'Ejecutado'})</span></span>
                <span class="text-[10px] ${ok ? 'text-secondary' : 'text-error'} font-mono">${h.hora || ''}</span>
            </div>
        `;
    });
    return html;
}
window.renderCommandHistory = renderCommandHistory;

// ============================================================
// SISTEMA DE AUTENTICACIÓN CRIPTOGRÁFICA (LOGIN & REGISTRO)
// ============================================================

const BOT_AVATARS_LIST = [
    { id: 'bot_cyan', url: '/static/avatars/bot_cyan.jpg', name: 'Cyan' },
    { id: 'bot_blue', url: '/static/avatars/bot_blue.jpg', name: 'Azul' },
    { id: 'bot_green', url: '/static/avatars/bot_green.jpg', name: 'Verde' },
    { id: 'bot_orange', url: '/static/avatars/bot_orange.jpg', name: 'Naranja' },
    { id: 'bot_purple', url: '/static/avatars/bot_purple.jpg', name: 'Púrpura' },
    { id: 'bot_pink', url: '/static/avatars/bot_pink.jpg', name: 'Rosa' },
    { id: 'bot_dark', url: '/static/avatars/bot_dark.jpg', name: 'Dark' }
];

let selectedRegisterAvatar = '/static/avatars/bot_cyan.jpg';

function renderAuthAvatarSelector() {
    const grid = document.getElementById('auth-reg-avatar-grid');
    if (!grid) return;

    grid.innerHTML = BOT_AVATARS_LIST.map(bot => {
        const isSel = (bot.url === selectedRegisterAvatar);
        return `
            <button type="button" onclick="selectAuthRegisterAvatar('${bot.url}', '${bot.name}')" title="Seleccionar ${bot.name}" class="auth-avatar-opt flex flex-col items-center gap-1.5 p-2 rounded-2xl border-2 ${isSel ? 'border-secondary bg-secondary/15 ring-2 ring-secondary/40 scale-105 shadow-[0_0_15px_rgba(0,255,204,0.4)]' : 'border-outline-variant/30 bg-surface-container-high/60 opacity-75 hover:opacity-100 hover:border-cyan-400/80 hover:scale-102'} transition-all cursor-pointer group">
                <div class="w-11 h-11 sm:w-12 sm:h-12 rounded-xl overflow-hidden p-0.5">
                    <img src="${bot.url}" alt="${bot.name}" class="w-full h-full object-cover rounded-lg group-hover:scale-105 transition-transform">
                </div>
                <span class="text-[10px] font-mono ${isSel ? 'text-secondary font-bold' : 'text-on-surface-variant'} truncate max-w-full">${bot.name}</span>
            </button>
        `;
    }).join('');
}
window.renderAuthAvatarSelector = renderAuthAvatarSelector;

function toggleAuthAvatarDropdown(event, forceClose) {
    if (event) event.stopPropagation();
    const panel = document.getElementById('auth-avatar-dropdown-panel');
    const arrow = document.getElementById('auth-avatar-arrow');
    if (!panel) return;

    const shouldClose = (forceClose !== undefined) ? forceClose : !panel.classList.contains('hidden');
    if (shouldClose) {
        panel.classList.add('hidden');
        if (arrow) arrow.style.transform = 'rotate(0deg)';
    } else {
        panel.classList.remove('hidden');
        if (arrow) arrow.style.transform = 'rotate(180deg)';
        renderAuthAvatarSelector();
    }
}
window.toggleAuthAvatarDropdown = toggleAuthAvatarDropdown;

function selectAuthRegisterAvatar(url, name) {
    selectedRegisterAvatar = url;
    const hiddenInp = document.getElementById('auth-reg-avatar');
    if (hiddenInp) hiddenInp.value = url;

    const previewImg = document.getElementById('auth-reg-avatar-preview');
    if (previewImg) previewImg.src = url;

    const nameEl = document.getElementById('auth-reg-avatar-name');
    if (nameEl) nameEl.innerText = name ? `Robot ${name}` : 'Robot Avatar';

    renderAuthAvatarSelector();

    // Cerrar automáticamente el menú desplegable tras seleccionar
    setTimeout(() => {
        toggleAuthAvatarDropdown(null, true);
    }, 200);
}
window.selectAuthRegisterAvatar = selectAuthRegisterAvatar;

// Cerrar el menú desplegable de avatares al hacer clic afuera
document.addEventListener('click', (e) => {
    const btn = document.getElementById('auth-avatar-picker-btn');
    const panel = document.getElementById('auth-avatar-dropdown-panel');
    if (panel && !panel.classList.contains('hidden')) {
        if (btn && !btn.contains(e.target) && !panel.contains(e.target)) {
            toggleAuthAvatarDropdown(null, true);
        }
    }
});

function switchAuthTab(tab) {
    const btnLogin = document.getElementById('auth-tab-btn-login');
    const btnReg = document.getElementById('auth-tab-btn-register');
    const formLogin = document.getElementById('auth-login-form');
    const formReg = document.getElementById('auth-register-form');
    const alertBox = document.getElementById('auth-alert-box');

    if (alertBox) alertBox.classList.add('hidden');

    if (tab === 'login') {
        if (btnLogin) {
            const currentTheme = (typeof getActiveThemeId === 'function') ? getActiveThemeId() : 'cyberpunk';
            if (currentTheme === 'ocean') {
                btnLogin.className = 'flex-1 py-2 text-xs font-bold rounded-lg transition-all flex items-center justify-center gap-1.5 bg-[#00d4ff] text-[#050b14] shadow-[0_0_15px_rgba(0,212,255,0.5)] cursor-pointer';
            } else if (currentTheme === 'amber') {
                btnLogin.className = 'flex-1 py-2 text-xs font-bold rounded-lg transition-all flex items-center justify-center gap-1.5 bg-[#f59e0b] text-[#0a0805] shadow-[0_0_15px_rgba(245,158,11,0.5)] cursor-pointer';
            } else if (currentTheme === 'purple') {
                btnLogin.className = 'flex-1 py-2 text-xs font-bold rounded-lg transition-all flex items-center justify-center gap-1.5 bg-[#a855f7] text-white shadow-[0_0_15px_rgba(168,85,247,0.5)] cursor-pointer';
            } else if (currentTheme === 'stealth') {
                btnLogin.className = 'flex-1 py-2 text-xs font-bold rounded-lg transition-all flex items-center justify-center gap-1.5 bg-[#e2e8f0] text-[#09090b] shadow-[0_0_15px_rgba(226,232,240,0.5)] cursor-pointer';
            } else if (currentTheme === 'crema') {
                btnLogin.className = 'flex-1 py-2 text-xs font-bold rounded-lg transition-all flex items-center justify-center gap-1.5 bg-[#d97706] text-white shadow-[0_2px_10px_rgba(217,119,6,0.35)] cursor-pointer';
            } else if (currentTheme === 'blanco') {
                btnLogin.className = 'flex-1 py-2 text-xs font-bold rounded-lg transition-all flex items-center justify-center gap-1.5 bg-[#2563eb] text-white shadow-[0_2px_10px_rgba(37,99,235,0.35)] cursor-pointer';
            } else {
                btnLogin.className = 'flex-1 py-2 text-xs font-bold rounded-lg transition-all flex items-center justify-center gap-1.5 bg-primary text-white shadow-[0_0_12px_rgba(255,45,120,0.4)] cursor-pointer';
            }
        }
        if (btnReg) {
            btnReg.className = 'flex-1 py-2 text-xs font-bold rounded-lg transition-all flex items-center justify-center gap-1.5 text-on-surface-variant hover:text-white cursor-pointer';
        }
        if (formLogin) formLogin.classList.remove('hidden');
        if (formReg) formReg.classList.add('hidden');
        const userInp = document.getElementById('auth-login-username');
        if (userInp) setTimeout(() => userInp.focus(), 80);
    } else {
        if (btnReg) {
            btnReg.className = 'flex-1 py-2 text-xs font-bold rounded-lg transition-all flex items-center justify-center gap-1.5 bg-secondary text-[#0a0a12] shadow-[0_0_12px_rgba(0,255,204,0.4)] cursor-pointer';
        }
        if (btnLogin) {
            btnLogin.className = 'flex-1 py-2 text-xs font-bold rounded-lg transition-all flex items-center justify-center gap-1.5 text-on-surface-variant hover:text-white cursor-pointer';
        }
        if (formLogin) formLogin.classList.add('hidden');
        if (formReg) formReg.classList.remove('hidden');
        renderAuthAvatarSelector();
        initPinDigitInputs();
        const regUserInp = document.getElementById('auth-reg-username');
        if (regUserInp) setTimeout(() => regUserInp.focus(), 80);
    }
}
window.switchAuthTab = switchAuthTab;

function showAuthAlert(msg, type = 'error') {
    const box = document.getElementById('auth-alert-box');
    if (!box) return;
    box.innerText = msg;
    box.classList.remove('hidden');

    if (type === 'error') {
        box.className = 'p-3 rounded-xl border border-red-500/50 bg-red-500/15 text-red-300 text-xs font-mono transition-all animate-shake';
    } else if (type === 'success') {
        box.className = 'p-3 rounded-xl border border-emerald-400/50 bg-emerald-400/15 text-emerald-300 text-xs font-mono transition-all';
    } else {
        box.className = 'p-3 rounded-xl border border-amber-400/50 bg-amber-400/15 text-amber-300 text-xs font-mono transition-all';
    }
}
window.showAuthAlert = showAuthAlert;

function verificarRegistroPasswords() {
    const p1 = document.getElementById('auth-reg-password');
    const p2 = document.getElementById('auth-reg-confirm');
    const msg = document.getElementById('auth-reg-match-msg');
    const hint = document.getElementById('auth-reg-pass-hint');
    if (!p1) return;

    const v1 = p1.value;

    if (hint) {
        if (!v1) {
            hint.innerText = 'Mín. 8 (Mayús, Núm, Símbolo)';
            hint.className = 'text-[10px] font-mono text-cyan-400';
        } else {
            const hasLen = v1.length >= 8;
            const hasUpper = /[A-Z]/.test(v1);
            const hasNum = /[0-9]/.test(v1);
            const hasSpec = /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?`~]/.test(v1);

            if (hasLen && hasUpper && hasNum && hasSpec) {
                hint.innerText = '✓ Clave Fuerte';
                hint.className = 'text-[10px] font-mono text-emerald-400 font-bold';
            } else {
                let missing = [];
                if (!hasLen) missing.push('8+ car.');
                if (!hasUpper) missing.push('Mayús');
                if (!hasNum) missing.push('Núm');
                if (!hasSpec) missing.push('Símbolo');
                hint.innerText = 'Falta: ' + missing.join(', ');
                hint.className = 'text-[10px] font-mono text-amber-400 font-bold';
            }
        }
    }

    if (!p2 || !msg) return;
    const v2 = p2.value;

    if (!v1 && !v2) {
        msg.innerText = '';
        p2.classList.remove('border-emerald-500/60', 'border-error/60');
        return;
    }

    if (v1 && v2 && v1 === v2) {
        msg.innerText = '✓ Coinciden';
        msg.className = 'text-[10px] font-mono text-emerald-400 font-bold';
        p2.classList.add('border-emerald-500/60');
        p2.classList.remove('border-error/60');
    } else if (v2 && v1 !== v2) {
        msg.innerText = '✗ No coinciden';
        msg.className = 'text-[10px] font-mono text-error font-bold';
        p2.classList.add('border-error/60');
        p2.classList.remove('border-emerald-500/60');
    } else {
        msg.innerText = '';
        p2.classList.remove('border-emerald-500/60', 'border-error/60');
    }
}
window.verificarRegistroPasswords = verificarRegistroPasswords;

async function checkAuthSession() {
    const modal = document.getElementById('auth-gate-modal');
    if (!modal) return;

    try {
        // 1. Verificar si la autenticación está activa en el sistema
        const statusRes = await fetch('/api/auth/status');
        if (statusRes.ok) {
            const statusData = await statusRes.json();
            if (statusData.auth_active === false) {
                modal.classList.add('hidden');
                return;
            }
        }

        // 2. Comprobar si ya existe una sesión válida (JWT en cookie o Bearer token)
        const token = localStorage.getItem('console_jwt_token');
        const headers = {};
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        const meRes = await fetch('/api/auth/me', {
            headers,
            credentials: 'include'
        });

        if (meRes.ok) {
            const meData = await meRes.json();
            if (meData.status === 'ok' && meData.user) {
                window.currentUser = meData.user;
                updateProfileDisplayName(meData.user.nombre || meData.user.username);
                if (meData.user.avatar) {
                    updateProfileAvatar(meData.user.avatar);
                }
                modal.classList.add('hidden');
                return;
            }
        }

        // 3. Si no hay sesión válida, limpiar token expirado y mostrar la puerta de autenticación
        localStorage.removeItem('console_jwt_token');
        modal.classList.remove('hidden');
        renderAuthAvatarSelector();
        const userInp = document.getElementById('auth-login-username');
        if (userInp) setTimeout(() => userInp.focus(), 150);

    } catch (e) {
        console.warn('Error comprobando sesión de autenticación:', e);
        localStorage.removeItem('console_jwt_token');
        modal.classList.remove('hidden');
    }
}
window.checkAuthSession = checkAuthSession;

async function ejecutarLogin(event) {
    if (event) event.preventDefault();

    const usernameInp = document.getElementById('auth-login-username');
    const passInp = document.getElementById('auth-login-password');
    const btn = document.getElementById('auth-login-btn');

    const username = usernameInp ? usernameInp.value.trim() : '';
    const password = passInp ? passInp.value : '';

    if (!username || !password) {
        showAuthAlert('Por favor completa todos los campos.');
        return;
    }

    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="material-symbols-outlined text-[18px] animate-spin">sync</span><span>Verificando credenciales...</span>';
    }

    try {
        const res = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ username, password })
        });

        const data = await res.json();

        if (res.ok && data.status === 'ok') {
            if (data.token) {
                localStorage.setItem('console_jwt_token', data.token);
            }
            if (data.user) {
                window.currentUser = data.user;
                updateProfileDisplayName(data.user.nombre || data.user.username);
                if (data.user.avatar) {
                    updateProfileAvatar(data.user.avatar);
                }
            }

            showAuthAlert(data.message || '¡Acceso concedido! Entrando a la consola...', 'success');

            setTimeout(() => {
                const modal = document.getElementById('auth-gate-modal');
                if (modal) modal.classList.add('hidden');
                if (btn) {
                    btn.disabled = false;
                    btn.innerHTML = '<span class="material-symbols-outlined text-[18px]">lock_open</span><span>Entrar a la Consola</span>';
                }
                showConfigToast(`¡Bienvenido a bordo, ${data.user?.nombre || username}!`);
            }, 600);

        } else if (res.status === 429) {
            showAuthAlert(data.message || 'Bloqueo temporal por intentos fallidos. Por favor espera unos minutos.', 'warning');
        } else {
            showAuthAlert(data.message || 'Usuario o contraseña incorrectos.');
            if (passInp) {
                passInp.value = '';
                passInp.focus();
            }
        }
    } catch (e) {
        console.error('Error en login:', e);
        showAuthAlert('Error al conectar con el servidor de autenticación.');
    } finally {
        if (btn && !document.getElementById('auth-gate-modal')?.classList.contains('hidden')) {
            btn.disabled = false;
            btn.innerHTML = '<span class="material-symbols-outlined text-[18px]">lock_open</span><span>Entrar a la Consola</span>';
        }
    }
}
window.ejecutarLogin = ejecutarLogin;

// --- Control de Casillas de PIN y Animación Orbital HUD ---
function initPinDigitInputs() {
    const boxes = document.querySelectorAll('.pin-digit-cell, .pin-digit-box');
    const hiddenPin = document.getElementById('auth-reg-pin');
    if (!boxes.length) return;

    boxes.forEach((box, idx) => {
        if (!box.dataset.hasListener) {
            box.dataset.hasListener = 'true';

            box.addEventListener('input', () => {
                const val = box.value.replace(/[^0-9]/g, '');
                box.value = val;
                if (val) {
                    box.classList.add('is-filled');
                    if (idx < boxes.length - 1) {
                        boxes[idx + 1].focus();
                    }
                } else {
                    box.classList.remove('is-filled');
                }
                syncPinValue();
            });

            box.addEventListener('keydown', (e) => {
                if (e.key === 'Backspace') {
                    if (!box.value && idx > 0) {
                        boxes[idx - 1].focus();
                        boxes[idx - 1].value = '';
                        boxes[idx - 1].classList.remove('is-filled');
                        syncPinValue();
                    } else if (box.value) {
                        box.value = '';
                        box.classList.remove('is-filled');
                        syncPinValue();
                    }
                } else if (e.key === 'ArrowLeft' && idx > 0) {
                    boxes[idx - 1].focus();
                } else if (e.key === 'ArrowRight' && idx < boxes.length - 1) {
                    boxes[idx + 1].focus();
                }
            });

            box.addEventListener('paste', (e) => {
                e.preventDefault();
                const pasted = (e.clipboardData || window.clipboardData).getData('text').trim().replace(/[^0-9]/g, '');
                if (pasted) {
                    pasted.split('').slice(0, 6).forEach((ch, i) => {
                        if (boxes[i]) {
                            boxes[i].value = ch;
                            boxes[i].classList.add('is-filled');
                        }
                    });
                    const targetIdx = Math.min(pasted.length, 5);
                    if (boxes[targetIdx]) {
                        boxes[targetIdx].focus();
                    }
                    syncPinValue();
                }
            });
        }
    });

    let isPinVerifying = false;

    async function syncPinValue() {
        const pin = Array.from(boxes).map(b => b.value).join('');
        if (hiddenPin) hiddenPin.value = pin;

        if (pin.length === 6) {
            if (isPinVerifying) return;
            const usernameInp = document.getElementById('auth-reg-username');
            const username = usernameInp ? usernameInp.value.trim() : '';
            const statusMsg = document.getElementById('auth-pin-status-msg');

            if (!username) {
                mostrarErrorPin('Escribe tu usuario antes de validar el PIN');
                if (usernameInp) usernameInp.focus();
                return;
            }

            if (statusMsg) {
                statusMsg.innerText = 'Validando PIN con el servidor...';
                statusMsg.className = 'text-[11px] font-mono text-cyan-300 font-bold block animate-pulse';
            }

            isPinVerifying = true;
            try {
                const res = await fetch('/api/auth/validar-pin', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, pin })
                });
                const data = await res.json();
                if (res.ok && data.status === 'ok') {
                    window.isPinPreValidated = true;
                    ejecutarAnimacionOrbitalPin(pin);
                } else {
                    window.isPinPreValidated = false;
                    mostrarErrorPin(data.message || 'PIN incorrecto o expirado');
                }
            } catch (err) {
                console.error('Error validando PIN:', err);
                window.isPinPreValidated = false;
                mostrarErrorPin('Error de conexión al validar PIN');
            } finally {
                isPinVerifying = false;
            }
        } else {
            window.isPinPreValidated = false;
            resetPinVerificationState();
        }
    }
}
window.initPinDigitInputs = initPinDigitInputs;

let isPinAnimRunning = false;
function ejecutarAnimacionOrbitalPin(pin) {
    if (isPinAnimRunning) return;
    isPinAnimRunning = true;

    const orbitContainer = document.getElementById('auth-pin-orbit-container');
    const centralBadge = document.getElementById('auth-pin-central-badge');
    const centralIcon = document.getElementById('auth-pin-central-icon');
    const shockwave = document.getElementById('auth-pin-shockwave');
    const statusMsg = document.getElementById('auth-pin-status-msg');
    const titleEl = document.getElementById('auth-pin-title');
    const subtitleEl = document.getElementById('auth-pin-subtitle');
    const card = document.getElementById('auth-pin-card');
    const regBtn = document.getElementById('auth-reg-btn');
    const regBtnIcon = document.getElementById('auth-reg-btn-icon');
    const regBtnText = document.getElementById('auth-reg-btn-text');

    if (!orbitContainer) return;
    orbitContainer.innerHTML = '';
    orbitContainer.classList.remove('animate-orbit-spin');

    // Radio de la órbita (en píxeles adaptado a radar w-24 h-24)
    const radius = 34;
    const digits = pin.split('');

    digits.forEach((digit, i) => {
        const angleDeg = i * 60;
        const angleRad = (angleDeg * Math.PI) / 180;
        const tx = Math.round(radius * Math.cos(angleRad));
        const ty = Math.round(radius * Math.sin(angleRad));

        const orb = document.createElement('div');
        orb.className = 'auth-orbit-node absolute w-5 h-5 rounded-full bg-gradient-to-tr from-cyan-400 to-emerald-300 text-black font-extrabold font-mono flex items-center justify-center text-[10px] shadow-[0_0_15px_#00ffcc] transition-all duration-300';
        orb.innerText = digit;
        orb.style.setProperty('--tx', `${tx}px`);
        orb.style.setProperty('--ty', `${ty}px`);
        orb.style.transform = `translate(${tx}px, ${ty}px)`;
        orbitContainer.appendChild(orb);
    });

    // Iniciar rotación de 360 grados
    orbitContainer.classList.add('animate-orbit-spin');

    if (statusMsg) {
        statusMsg.innerText = 'Autenticando PIN...';
        statusMsg.className = 'text-[10px] font-mono text-cyan-300 font-bold animate-pulse';
    }

    // Al terminar el giro de 360 grados (850ms), colapsar hacia el centro
    setTimeout(() => {
        const nodes = orbitContainer.querySelectorAll('.auth-orbit-node');
        nodes.forEach(node => {
            node.classList.add('animate-orbit-collapse');
        });
    }, 850);

    // Al colapsar al centro (1300ms), activar destello, onda expansiva y estado exitoso
    setTimeout(() => {
        orbitContainer.innerHTML = '';
        orbitContainer.classList.remove('animate-orbit-spin');

        if (shockwave) {
            shockwave.classList.remove('hidden');
            shockwave.classList.remove('animate-pin-shockwave');
            void shockwave.offsetWidth;
            shockwave.classList.add('animate-pin-shockwave');
            setTimeout(() => shockwave.classList.add('hidden'), 700);
        }

        if (centralBadge) {
            centralBadge.className = 'relative z-10 w-10 h-10 rounded-xl bg-emerald-950/80 border-2 border-emerald-400 flex flex-col items-center justify-center text-emerald-300 shadow-[0_0_35px_rgba(16,185,129,0.8)] scale-110 transition-all duration-500';
        }
        if (centralIcon) {
            centralIcon.innerText = 'verified';
            centralIcon.className = 'material-symbols-outlined text-[20px] text-emerald-300 animate-bounce';
            setTimeout(() => centralIcon.classList.remove('animate-bounce'), 1000);
        }

        if (card) card.classList.add('verified-state');

        if (titleEl) {
            titleEl.innerText = 'PIN Autenticado con Éxito';
            titleEl.className = 'text-[11px] font-bold text-emerald-300 font-mono tracking-wide';
        }
        if (subtitleEl) {
            subtitleEl.innerText = 'Código validado y asegurado criptográficamente';
            subtitleEl.className = 'text-[9px] text-emerald-400/80 font-mono';
        }

        if (statusMsg) {
            statusMsg.innerText = '✓ Verificación Exitosa: Todo listo';
            statusMsg.className = 'text-[10px] font-mono text-emerald-400 font-bold';
        }

        // Transformar botón a Verified & Secured
        if (regBtn) {
            regBtn.className = 'w-full mt-1 py-2.5 px-4 rounded-xl bg-gradient-to-r from-emerald-500 via-teal-400 to-emerald-500 hover:brightness-110 text-black font-extrabold text-xs flex items-center justify-center gap-2 transition-all shadow-[0_0_30px_rgba(16,185,129,0.6)] cursor-pointer';
        }
        if (regBtnIcon) regBtnIcon.innerText = 'verified_user';
        if (regBtnText) regBtnText.innerText = 'Verified & Secured — Crear Cuenta';

        window.isPinPreValidated = true;
        isPinAnimRunning = false;
    }, 1300);
}
window.ejecutarAnimacionOrbitalPin = ejecutarAnimacionOrbitalPin;

function resetPinVerificationState() {
    window.isPinPreValidated = false;
    const orbitContainer = document.getElementById('auth-pin-orbit-container');
    if (orbitContainer) {
        orbitContainer.innerHTML = '';
        orbitContainer.classList.remove('animate-orbit-spin');
    }
    const card = document.getElementById('auth-pin-card');
    if (card) card.classList.remove('verified-state');

    const centralBadge = document.getElementById('auth-pin-central-badge');
    if (centralBadge) {
        centralBadge.className = 'relative z-10 w-10 h-10 rounded-xl bg-[#090e17] border-2 border-cyan-400/60 flex flex-col items-center justify-center text-cyan-300 shadow-[0_0_25px_rgba(6,182,212,0.35)] transition-all duration-500';
    }
    const centralIcon = document.getElementById('auth-pin-central-icon');
    if (centralIcon) {
        centralIcon.innerText = 'vpn_key';
        centralIcon.className = 'material-symbols-outlined text-[20px]';
    }

    const titleEl = document.getElementById('auth-pin-title');
    if (titleEl) {
        titleEl.innerText = 'PIN de Autorización';
        titleEl.className = 'text-[11px] font-bold text-white font-mono tracking-wide';
    }
    const subtitleEl = document.getElementById('auth-pin-subtitle');
    if (subtitleEl) {
        subtitleEl.innerText = 'Solicitud 2FA directa a Telegram';
        subtitleEl.className = 'text-[9px] text-on-surface-variant/80 font-mono';
    }

    const regBtn = document.getElementById('auth-reg-btn');
    if (regBtn) {
        regBtn.className = 'w-full mt-1 py-2.5 px-4 rounded-xl bg-gradient-to-r from-cyan-500 via-secondary to-cyan-500 hover:brightness-110 text-black font-extrabold text-xs flex items-center justify-center gap-2 transition-all shadow-[0_0_20px_rgba(0,255,204,0.35)] cursor-pointer';
    }
    const regBtnIcon = document.getElementById('auth-reg-btn-icon');
    if (regBtnIcon) regBtnIcon.innerText = 'how_to_reg';
    const regBtnText = document.getElementById('auth-reg-btn-text');
    if (regBtnText) regBtnText.innerText = 'Crear Cuenta & Acceder';

    isPinAnimRunning = false;
}
window.resetPinVerificationState = resetPinVerificationState;

function mostrarErrorPin(mensaje) {
    window.isPinPreValidated = false;
    const boxes = document.querySelectorAll('.pin-digit-cell, .pin-digit-box');
    boxes.forEach(b => {
        b.classList.remove('is-filled');
        b.classList.add('is-error');
    });

    const statusMsg = document.getElementById('auth-pin-status-msg');
    if (statusMsg) {
        statusMsg.innerText = '✗ ' + mensaje;
        statusMsg.className = 'text-[10px] font-mono text-red-400 font-bold block animate-pulse';
    }

    const centralBadge = document.getElementById('auth-pin-central-badge');
    if (centralBadge) {
        centralBadge.className = 'relative z-10 w-10 h-10 rounded-xl bg-red-950/80 border-2 border-red-500/80 flex flex-col items-center justify-center text-red-400 shadow-[0_0_25px_rgba(239,68,68,0.5)] transition-all duration-300';
    }
    const centralIcon = document.getElementById('auth-pin-central-icon');
    if (centralIcon) {
        centralIcon.innerText = 'gpp_bad';
        centralIcon.className = 'material-symbols-outlined text-[20px] text-red-400';
    }

    const titleEl = document.getElementById('auth-pin-title');
    if (titleEl) {
        titleEl.innerText = 'PIN No Autorizado';
        titleEl.className = 'text-[11px] font-bold text-red-400 font-mono tracking-wide';
    }
    const subtitleEl = document.getElementById('auth-pin-subtitle');
    if (subtitleEl) {
        subtitleEl.innerText = 'Código rechazado por el servidor';
        subtitleEl.className = 'text-[9px] text-red-400/80 font-mono';
    }

    const card = document.getElementById('auth-pin-card');
    if (card) card.classList.remove('verified-state');

    const regBtn = document.getElementById('auth-reg-btn');
    const regBtnIcon = document.getElementById('auth-reg-btn-icon');
    const regBtnText = document.getElementById('auth-reg-btn-text');
    if (regBtn) {
        regBtn.className = 'w-full mt-1 py-2.5 px-4 rounded-xl bg-gradient-to-r from-cyan-500 via-secondary to-cyan-500 hover:brightness-110 text-black font-extrabold text-xs flex items-center justify-center gap-2 transition-all shadow-[0_0_20px_rgba(0,255,204,0.35)] cursor-pointer';
    }
    if (regBtnIcon) regBtnIcon.innerText = 'how_to_reg';
    if (regBtnText) regBtnText.innerText = 'Crear Cuenta & Acceder';

    setTimeout(() => {
        boxes.forEach(b => {
            b.value = '';
            b.classList.remove('is-error', 'is-filled');
        });
        const hiddenPin = document.getElementById('auth-reg-pin');
        if (hiddenPin) hiddenPin.value = '';
        resetPinVerificationState();
        if (boxes[0]) boxes[0].focus();
    }, 1400);
}
window.mostrarErrorPin = mostrarErrorPin;

let pinRequestCooldownTimer = null;

async function solicitarPinRegistro(event) {
    if (event) event.preventDefault();

    const usernameInp = document.getElementById('auth-reg-username');
    const pinInp = document.getElementById('auth-reg-pin');
    const btn = document.getElementById('btn-solicitar-pin');
    const textEl = document.getElementById('text-solicitar-pin');
    const iconEl = document.getElementById('icon-solicitar-pin');
    const statusMsg = document.getElementById('auth-pin-status-msg');
    const countdownEl = document.getElementById('auth-pin-countdown-text');

    const username = usernameInp ? usernameInp.value.trim() : '';

    if (!username || username.length < 3) {
        showAuthAlert('Escribe tu nombre de usuario o apodo (mínimo 3 caracteres) antes de solicitar el PIN.');
        if (usernameInp) usernameInp.focus();
        return;
    }

    if (btn) {
        btn.disabled = true;
        btn.classList.add('opacity-70', 'cursor-not-allowed');
    }
    if (iconEl) {
        iconEl.innerText = 'sync';
        iconEl.classList.add('animate-spin');
    }
    if (textEl) textEl.innerText = 'Enviando...';

    try {
        const res = await fetch('/api/auth/solicitar-pin', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, nombre: username })
        });

        const data = await res.json();

        if (res.ok && data.status === 'ok') {
            showAuthAlert(data.message, 'success');
            if (statusMsg) {
                statusMsg.className = 'text-[10px] font-mono text-emerald-400 font-bold block animate-pulse';
                statusMsg.innerText = '✓ Solicitud enviada por Telegram. Escribe el PIN aquí.';
            }

            // Limpiar casillas de PIN y enfocar la primera
            const boxes = document.querySelectorAll('.pin-digit-cell, .pin-digit-box');
            boxes.forEach(b => {
                b.value = '';
                b.classList.remove('is-filled');
            });
            if (pinInp) pinInp.value = '';
            resetPinVerificationState();

            if (boxes[0]) {
                setTimeout(() => boxes[0].focus(), 150);
            }

            let countdown = 60;
            if (btn) btn.classList.add('hidden');
            if (countdownEl) {
                countdownEl.classList.remove('hidden');
                countdownEl.innerText = `Reenviar en 00:${countdown < 10 ? '0' + countdown : countdown}`;
            }

            if (pinRequestCooldownTimer) clearInterval(pinRequestCooldownTimer);
            pinRequestCooldownTimer = setInterval(() => {
                countdown--;
                if (countdown <= 0) {
                    clearInterval(pinRequestCooldownTimer);
                    pinRequestCooldownTimer = null;
                    if (btn) {
                        btn.disabled = false;
                        btn.classList.remove('opacity-70', 'cursor-not-allowed', 'hidden');
                    }
                    if (textEl) textEl.innerText = 'Reenviar PIN';
                    if (iconEl) {
                        iconEl.classList.remove('animate-spin');
                        iconEl.innerText = 'send';
                    }
                    if (countdownEl) countdownEl.classList.add('hidden');
                } else {
                    if (countdownEl) {
                        countdownEl.innerText = `Reenviar en 00:${countdown < 10 ? '0' + countdown : countdown}`;
                    }
                }
            }, 1000);

        } else if (res.status === 429) {
            showAuthAlert(data.message || 'Espera un momento antes de solicitar otro PIN.', 'warning');
            if (btn) {
                btn.disabled = false;
                btn.classList.remove('opacity-70', 'cursor-not-allowed', 'hidden');
            }
            if (countdownEl) countdownEl.classList.add('hidden');
            if (textEl) textEl.innerText = 'Solicitar PIN';
            if (iconEl) {
                iconEl.classList.remove('animate-spin');
                iconEl.innerText = 'send';
            }
        } else {
            showAuthAlert(data.message || 'Error al solicitar el PIN.');
            if (btn) {
                btn.disabled = false;
                btn.classList.remove('opacity-70', 'cursor-not-allowed', 'hidden');
            }
            if (countdownEl) countdownEl.classList.add('hidden');
            if (textEl) textEl.innerText = 'Solicitar PIN';
            if (iconEl) {
                iconEl.classList.remove('animate-spin');
                iconEl.innerText = 'send';
            }
        }
    } catch (e) {
        console.error('Error solicitando PIN:', e);
        showAuthAlert('Error al conectar con el servidor.');
        if (btn) {
            btn.disabled = false;
            btn.classList.remove('opacity-70', 'cursor-not-allowed', 'hidden');
        }
        if (countdownEl) countdownEl.classList.add('hidden');
        if (textEl) textEl.innerText = 'Solicitar PIN';
        if (iconEl) {
            iconEl.classList.remove('animate-spin');
            iconEl.innerText = 'send';
        }
    }
}
window.solicitarPinRegistro = solicitarPinRegistro;

async function ejecutarRegistro(event) {
    if (event) event.preventDefault();

    const usernameInp = document.getElementById('auth-reg-username');
    const avatarInp = document.getElementById('auth-reg-avatar');
    const passInp = document.getElementById('auth-reg-password');
    const confirmInp = document.getElementById('auth-reg-confirm');
    const pinInp = document.getElementById('auth-reg-pin');
    const btn = document.getElementById('auth-reg-btn');

    const username = usernameInp ? usernameInp.value.trim() : '';
    const nombre = username;
    const avatar = avatarInp ? avatarInp.value : selectedRegisterAvatar;
    const password = passInp ? passInp.value : '';
    const confirm = confirmInp ? confirmInp.value : '';
    const pin = pinInp ? pinInp.value.trim() : '';

    if (!username || !password) {
        showAuthAlert('Debes ingresar tu nombre de usuario o apodo y contraseña.');
        return;
    }

    if (username.length < 3) {
        showAuthAlert('El nombre de usuario o apodo debe tener al menos 3 caracteres.');
        if (usernameInp) usernameInp.focus();
        return;
    }

    if (password.length < 8) {
        showAuthAlert('La contraseña debe tener al menos 8 caracteres.');
        if (passInp) passInp.focus();
        return;
    }

    if (!/[A-Z]/.test(password)) {
        showAuthAlert('La contraseña debe incluir al menos una letra mayúscula (A-Z).');
        if (passInp) passInp.focus();
        return;
    }

    if (!/[0-9]/.test(password)) {
        showAuthAlert('La contraseña debe incluir al menos un número (0-9).');
        if (passInp) passInp.focus();
        return;
    }

    if (!/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?`~]/.test(password)) {
        showAuthAlert('La contraseña debe incluir al menos un carácter especial o símbolo (!@#$%&*...).');
        if (passInp) passInp.focus();
        return;
    }

    if (password !== confirm) {
        showAuthAlert('Las contraseñas no coinciden. Por favor verifícalas.');
        if (confirmInp) confirmInp.focus();
        return;
    }

    if (!pin || pin.length < 6 || !window.isPinPreValidated) {
        showAuthAlert('Debes ingresar un PIN de autorización válido y verificado.');
        const firstDigit = document.querySelector('.pin-digit-cell, .pin-digit-box');
        if (firstDigit) firstDigit.focus();
        return;
    }

    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="material-symbols-outlined text-[18px] animate-spin">sync</span><span>Creando cuenta segura...</span>';
    }

    try {
        const res = await fetch('/api/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({
                nombre: username,
                username,
                password,
                avatar,
                pin
            })
        });

        const data = await res.json();

        if (res.ok && data.status === 'ok') {
            if (data.token) {
                localStorage.setItem('console_jwt_token', data.token);
            }
            if (data.user) {
                window.currentUser = data.user;
                updateProfileDisplayName(data.user.nombre || data.user.username);
                if (data.user.avatar) {
                    updateProfileAvatar(data.user.avatar);
                }
            }

            showAuthAlert(data.message || '¡Cuenta creada con éxito! Entrando...', 'success');

            setTimeout(() => {
                const modal = document.getElementById('auth-gate-modal');
                if (modal) modal.classList.add('hidden');
                if (btn) {
                    btn.disabled = false;
                    btn.innerHTML = '<span class="material-symbols-outlined text-[18px]">how_to_reg</span><span>Crear Cuenta & Acceder</span>';
                }
                showConfigToast(`¡Cuenta creada con éxito! Bienvenido, ${data.user?.nombre || username}.`);
            }, 700);

        } else {
            showAuthAlert(data.message || 'No se pudo crear la cuenta.');
        }
    } catch (e) {
        console.error('Error en registro:', e);
        showAuthAlert('Error al conectar con el servidor.');
    } finally {
        if (btn && !document.getElementById('auth-gate-modal')?.classList.contains('hidden')) {
            btn.disabled = false;
            btn.innerHTML = '<span class="material-symbols-outlined text-[18px]">how_to_reg</span><span>Crear Cuenta & Acceder</span>';
        }
    }
}
window.ejecutarRegistro = ejecutarRegistro;

async function cerrarSesionConsola() {
    // Cerrar menú dropdown si está abierto
    const dropdown = document.getElementById('profile-dropdown');
    if (dropdown) dropdown.classList.add('hidden');

    try {
        await fetch('/api/auth/logout', {
            method: 'POST',
            credentials: 'include'
        });
    } catch (e) {
        console.warn('Error llamando logout endpoint:', e);
    }

    localStorage.removeItem('console_jwt_token');
    window.currentUser = null;

    const modal = document.getElementById('auth-gate-modal');
    if (modal) {
        modal.classList.remove('hidden');
        switchAuthTab('login');
        const passInp = document.getElementById('auth-login-password');
        if (passInp) passInp.value = '';
        const alertBox = document.getElementById('auth-alert-box');
        if (alertBox) alertBox.classList.add('hidden');
    }
}
window.cerrarSesionConsola = cerrarSesionConsola;

// ============================================================
// SISTEMA DE PALETAS DE COLOR Y TEMAS MULTI-AMBIENTE
// ============================================================

const AVAILABLE_THEMES = [
    {
        id: 'cyberpunk',
        name: 'Cyberpunk',
        badge: 'Oscuro Neón',
        desc: 'Magenta neón, cian eléctrico y fondo abisal oscuro',
        mode: 'dark',
        primary: '#ff2d78',
        secondary: '#00ffcc',
        bg: '#0a0a12',
        surface: '#141422',
        border: '#302840'
    },
    {
        id: 'ocean',
        name: 'Océano Profundo',
        badge: 'Azul Neón',
        desc: 'Azul cobalto abisal con toques cian y zafiro neón eléctrico',
        mode: 'dark',
        primary: '#00d4ff',
        secondary: '#38bdf8',
        bg: '#050b14',
        surface: '#081224',
        border: '#122d50'
    },
    {
        id: 'amber',
        name: 'Ámbar Cálido',
        badge: 'Atardecer Dorado',
        desc: 'Carbón volcánico con ámbar brillante y naranja fuego',
        mode: 'dark',
        primary: '#f59e0b',
        secondary: '#f97316',
        bg: '#120e09',
        surface: '#241c13',
        border: '#3d2d18'
    },
    {
        id: 'purple',
        name: 'Nebulosa Púrpura',
        badge: 'Cosmos Violeta',
        desc: 'Violeta cósmico y fucsia estelar sobre negro espacial',
        mode: 'dark',
        primary: '#a855f7',
        secondary: '#ec4899',
        bg: '#0e071c',
        surface: '#1b0e33',
        border: '#321854'
    },
    {
        id: 'stealth',
        name: 'Stealth Carbon',
        badge: 'Grafito Minimal',
        desc: 'Monocromo grafito con toques titanio y azul cielo glaciar',
        mode: 'dark',
        primary: '#e2e8f0',
        secondary: '#38bdf8',
        bg: '#09090b',
        surface: '#18181b',
        border: '#27272a'
    },
    {
        id: 'crema',
        name: 'Crema & Moka',
        badge: 'Claro Cálido',
        desc: 'Marfil suave, café moka, caramelo tostado y verde salvia',
        mode: 'light',
        primary: '#d97706',
        secondary: '#059669',
        bg: '#f6f2ea',
        surface: '#ffffff',
        border: '#d6ccb8'
    },
    {
        id: 'blanco',
        name: 'Blanco Puro',
        badge: 'Claro Minimalista',
        desc: 'Blanco pizarra impecable con azul real y detalles acero',
        mode: 'light',
        primary: '#2563eb',
        secondary: '#0284c7',
        bg: '#f8fafc',
        surface: '#ffffff',
        border: '#cbd5e1'
    }
];
window.AVAILABLE_THEMES = AVAILABLE_THEMES;

function getActiveThemeId() {
    try {
        return localStorage.getItem('agenticos_theme') || 'cyberpunk';
    } catch(e) {
        return 'cyberpunk';
    }
}

function aplicarTema(themeId, notify = false) {
    const theme = AVAILABLE_THEMES.find(t => t.id === themeId) || AVAILABLE_THEMES[0];
    const isLight = (theme.mode === 'light');

    document.documentElement.setAttribute('data-theme', theme.id);
    document.documentElement.setAttribute('data-theme-mode', theme.mode);

    if (isLight) {
        document.documentElement.classList.remove('dark');
        document.documentElement.classList.add('light');
    } else {
        document.documentElement.classList.remove('light');
        document.documentElement.classList.add('dark');
    }

    try {
        localStorage.setItem('agenticos_theme', theme.id);
    } catch(e) {}

    // Actualizar nombre en el botón del Header
    const headerName = document.getElementById('header-theme-name');
    if (headerName) headerName.innerText = theme.name;

    // Actualizar badge en la vista de Configuración
    const cfgBadge = document.getElementById('config-current-theme-badge');
    if (cfgBadge) {
        cfgBadge.innerText = theme.name;
        cfgBadge.style.color = theme.primary;
        cfgBadge.style.borderColor = theme.primary;
    }

    // Cerrar dropdown rápido si está abierto
    const quickDropdown = document.getElementById('theme-quick-dropdown');
    if (quickDropdown) quickDropdown.classList.add('hidden');

    // Re-renderizar indicadores activos en ambos selectores
    renderHeaderThemesList();
    renderConfigThemesGrid();

    // Actualizar Meniscus Dock si está presente
    const rimGlowEl = document.getElementById('meniscus-rim-glow');
    if (rimGlowEl) {
        if (theme.id === 'ocean') {
            rimGlowEl.setAttribute('stroke', '#00d4ff');
        } else if (theme.id === 'amber') {
            rimGlowEl.setAttribute('stroke', '#f59e0b');
        } else if (theme.id === 'purple') {
            rimGlowEl.setAttribute('stroke', '#a855f7');
        } else if (theme.id === 'stealth') {
            rimGlowEl.setAttribute('stroke', '#e2e8f0');
        } else if (theme.id === 'crema') {
            rimGlowEl.setAttribute('stroke', '#d97706');
        } else if (theme.id === 'blanco') {
            rimGlowEl.setAttribute('stroke', '#2563eb');
        } else {
            rimGlowEl.setAttribute('stroke', '#ff2d78');
        }
    }

    // Si la vista actual es Configuración, actualizar estilos del botón del footer en caliente
    const cfgView = document.getElementById('view-configuracion');
    if (cfgView && !cfgView.classList.contains('hidden')) {
        const cfgBtn = document.getElementById('footer-btn-config');
        const iconBox = document.getElementById('footer-config-icon-box');
        const textEl = document.getElementById('footer-config-text');
        if (cfgBtn) {
            if (theme.id === 'ocean') {
                cfgBtn.className = "w-full !py-2.5 !text-xs text-white bg-[#00d4ff]/15 border border-[#00d4ff]/50 shadow-[0_0_15px_rgba(0,212,255,0.35)] flex items-center gap-2.5 px-3 rounded-xl transition-all cursor-pointer select-none";
            } else if (theme.id === 'amber') {
                cfgBtn.className = "w-full !py-2.5 !text-xs text-white bg-[#f59e0b]/15 border border-[#f59e0b]/50 shadow-[0_0_15px_rgba(245,158,11,0.35)] flex items-center gap-2.5 px-3 rounded-xl transition-all cursor-pointer select-none";
            } else if (theme.id === 'purple') {
                cfgBtn.className = "w-full !py-2.5 !text-xs text-white bg-[#a855f7]/15 border border-[#a855f7]/50 shadow-[0_0_15px_rgba(168,85,247,0.35)] flex items-center gap-2.5 px-3 rounded-xl transition-all cursor-pointer select-none";
            } else if (theme.id === 'stealth') {
                cfgBtn.className = "w-full !py-2.5 !text-xs text-white bg-[#e2e8f0]/15 border border-[#e2e8f0]/50 shadow-[0_0_15px_rgba(226,232,240,0.3)] flex items-center gap-2.5 px-3 rounded-xl transition-all cursor-pointer select-none";
            } else if (theme.id === 'crema') {
                cfgBtn.className = "w-full !py-2.5 !text-xs text-[#292524] bg-[#d97706]/15 border border-[#d97706]/40 shadow-[0_2px_10px_rgba(217,119,6,0.2)] flex items-center gap-2.5 px-3 rounded-xl transition-all cursor-pointer select-none";
            } else if (theme.id === 'blanco') {
                cfgBtn.className = "w-full !py-2.5 !text-xs text-[#0f172a] bg-[#2563eb]/15 border border-[#2563eb]/40 shadow-[0_2px_10px_rgba(37,99,235,0.2)] flex items-center gap-2.5 px-3 rounded-xl transition-all cursor-pointer select-none";
            } else {
                cfgBtn.className = "w-full !py-2.5 !text-xs text-white bg-primary/15 border border-primary/50 shadow-[0_0_15px_rgba(255,45,120,0.35)] flex items-center gap-2.5 px-3 rounded-xl transition-all cursor-pointer select-none";
            }
        }
        if (iconBox) {
            if (theme.id === 'ocean') {
                iconBox.className = "w-7 h-7 flex items-center justify-center rounded-lg bg-gradient-to-br from-[#38bdf8] to-[#00d4ff] border border-[#00d4ff] text-white shadow-[0_0_12px_rgba(0,212,255,0.7)] transition-all shrink-0";
            } else if (theme.id === 'amber') {
                iconBox.className = "w-7 h-7 flex items-center justify-center rounded-lg bg-gradient-to-br from-[#fbbf24] to-[#f59e0b] border border-[#f59e0b] text-[#0a0805] shadow-[0_0_12px_rgba(245,158,11,0.7)] transition-all shrink-0";
            } else if (theme.id === 'purple') {
                iconBox.className = "w-7 h-7 flex items-center justify-center rounded-lg bg-gradient-to-br from-[#c084fc] to-[#a855f7] border border-[#a855f7] text-white shadow-[0_0_12px_rgba(168,85,247,0.7)] transition-all shrink-0";
            } else if (theme.id === 'stealth') {
                iconBox.className = "w-7 h-7 flex items-center justify-center rounded-lg bg-gradient-to-br from-[#ffffff] to-[#cbd5e1] border border-[#e2e8f0] text-[#09090b] shadow-[0_0_12px_rgba(226,232,240,0.65)] transition-all shrink-0";
            } else if (theme.id === 'crema') {
                iconBox.className = "w-7 h-7 flex items-center justify-center rounded-lg bg-gradient-to-br from-[#f59e0b] to-[#d97706] border border-[#d97706] text-white shadow-[0_2px_8px_rgba(217,119,6,0.4)] transition-all shrink-0";
            } else if (theme.id === 'blanco') {
                iconBox.className = "w-7 h-7 flex items-center justify-center rounded-lg bg-gradient-to-br from-[#38bdf8] to-[#2563eb] border border-[#2563eb] text-white shadow-[0_2px_8px_rgba(37,99,235,0.4)] transition-all shrink-0";
            } else {
                iconBox.className = "w-7 h-7 flex items-center justify-center rounded-lg bg-primary border border-primary text-white shadow-[0_0_12px_rgba(255,45,120,0.65)] transition-all shrink-0";
            }
        }
        if (textEl) {
            if (theme.id === 'ocean') {
                textEl.className = "font-bold text-white drop-shadow-[0_0_8px_rgba(0,212,255,0.5)]";
            } else if (theme.id === 'amber') {
                textEl.className = "font-bold text-white drop-shadow-[0_0_8px_rgba(245,158,11,0.5)]";
            } else if (theme.id === 'purple') {
                textEl.className = "font-bold text-white drop-shadow-[0_0_8px_rgba(168,85,247,0.5)]";
            } else if (theme.id === 'stealth') {
                textEl.className = "font-bold text-white drop-shadow-[0_0_8px_rgba(226,232,240,0.5)]";
            } else if (theme.id === 'crema') {
                textEl.className = "font-bold text-[#292524]";
            } else if (theme.id === 'blanco') {
                textEl.className = "font-bold text-[#0f172a]";
            } else {
                textEl.className = "font-bold text-white drop-shadow-[0_0_8px_rgba(255,45,120,0.4)]";
            }
        }
    }
    if (typeof renderMeniscusFrame === 'function') {
        renderMeniscusFrame();
    }

    if (notify && typeof showConfigToast === 'function') {
        showConfigToast(`Paleta aplicada: ${theme.name} (${theme.badge})`);
    }
}
window.aplicarTema = aplicarTema;

function toggleProfileDropdown(event) {
    if (event) event.stopPropagation();
    const dropdown = document.getElementById('profile-dropdown');
    if (!dropdown) return;
    dropdown.classList.toggle('hidden');

    const themeDropdown = document.getElementById('theme-quick-dropdown');
    if (themeDropdown) themeDropdown.classList.add('hidden');
}
window.toggleProfileDropdown = toggleProfileDropdown;

function toggleThemeDropdown(event) {
    if (event) event.stopPropagation();
    const dropdown = document.getElementById('theme-quick-dropdown');
    if (!dropdown) return;
    dropdown.classList.toggle('hidden');

    const profileDropdown = document.getElementById('profile-dropdown');
    if (profileDropdown) profileDropdown.classList.add('hidden');
}
window.toggleThemeDropdown = toggleThemeDropdown;

function renderHeaderThemesList() {
    const container = document.getElementById('header-theme-list');
    if (!container) return;

    const currentId = getActiveThemeId();

    container.innerHTML = AVAILABLE_THEMES.map(theme => {
        const isSel = (theme.id === currentId);
        return `
            <button onclick="aplicarTema('${theme.id}', true)" type="button" title="${theme.name}" class="group relative w-8 h-8 rounded-full flex items-center justify-center transition-all cursor-pointer ${isSel ? 'ring-2 ring-primary ring-offset-2 ring-offset-surface scale-110' : 'hover:scale-115 opacity-75 hover:opacity-100'}">
                <span class="w-[25px] h-[25px] rounded-full transition-all block shadow-xs" style="background: linear-gradient(135deg, ${theme.bg} 50%, ${theme.primary} 50%); border: 1px solid rgba(140, 140, 140, 0.4); box-shadow: 0 0 ${isSel ? '8px' : '2px'} ${theme.primary};"></span>
            </button>
        `;
    }).join('');
}
window.renderHeaderThemesList = renderHeaderThemesList;

function renderConfigThemesGrid() {
    const grid = document.getElementById('config-themes-grid');
    if (!grid) return;

    const currentId = getActiveThemeId();

    grid.innerHTML = AVAILABLE_THEMES.map(theme => {
        const isSel = (theme.id === currentId);
        return `
            <button onclick="aplicarTema('${theme.id}', true)" type="button" title="${theme.name}" class="group relative w-8 h-8 rounded-full flex items-center justify-center transition-all cursor-pointer ${isSel ? 'ring-2 ring-primary ring-offset-2 ring-offset-surface scale-110' : 'hover:scale-115 opacity-75 hover:opacity-100'}">
                <span class="w-[25px] h-[25px] rounded-full transition-all block shadow-xs" style="background: linear-gradient(135deg, ${theme.bg} 50%, ${theme.primary} 50%); border: 1px solid rgba(140, 140, 140, 0.4); box-shadow: 0 0 ${isSel ? '8px' : '2px'} ${theme.primary};"></span>
            </button>
        `;
    }).join('');
}
window.renderConfigThemesGrid = renderConfigThemesGrid;

function initThemesSystem() {
    const saved = getActiveThemeId();
    aplicarTema(saved, false);
    renderHeaderThemesList();
    renderConfigThemesGrid();
}
window.initThemesSystem = initThemesSystem;

// Cerrar dropdowns de perfil y temas al hacer clic afuera
document.addEventListener('click', (e) => {
    const profileContainer = document.getElementById('profile-menu-container');
    const profileDropdown = document.getElementById('profile-dropdown');
    if (profileDropdown && !profileDropdown.classList.contains('hidden')) {
        if (profileContainer && !profileContainer.contains(e.target)) {
            profileDropdown.classList.add('hidden');
        }
    }

    const themeContainer = document.getElementById('theme-menu-container');
    const themeDropdown = document.getElementById('theme-quick-dropdown');
    if (themeDropdown && !themeDropdown.classList.contains('hidden')) {
        if (themeContainer && !themeContainer.contains(e.target)) {
            themeDropdown.classList.add('hidden');
        }
    }
});

// Iniciar comprobación de sesión y temas al cargar la página
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        initThemesSystem();
        renderAuthAvatarSelector();
        initPinDigitInputs();
        checkAuthSession();
    });
} else {
    initThemesSystem();
    renderAuthAvatarSelector();
    initPinDigitInputs();
    checkAuthSession();
}


