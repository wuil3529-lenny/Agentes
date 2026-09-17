let recognition = null;
let isDictating = false;

function initSpeechRecognition() {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        console.warn("API de reconocimiento de voz no soportada en este navegador.");
        return false;
    }
    
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = 'es-ES';
    
    recognition.onstart = function() {
        isDictating = true;
        const btn = document.getElementById('voice-dictation-btn');
        const pulse = document.getElementById('dictation-pulse');
        const title = document.getElementById('voice-status-title');
        const text = document.getElementById('voice-status-text');
        
        if (btn) btn.classList.add('text-primary', 'border-primary', 'shadow-[0_0_20px_rgba(255,45,120,0.5)]');
        if (pulse) pulse.classList.remove('hidden');
        if (title) title.innerText = 'ESCUCHANDO...';
        if (title) title.classList.add('text-primary', 'animate-pulse');
        if (text) text.innerText = 'Habla ahora. Tus comandos serán transcritos automáticamente.';
    };
    
    recognition.onresult = function(event) {
        let interimTranscript = '';
        let finalTranscript = '';
        
        for (let i = event.resultIndex; i < event.results.length; ++i) {
            if (event.results[i].isFinal) {
                finalTranscript += event.results[i][0].transcript;
            } else {
                interimTranscript += event.results[i][0].transcript;
            }
        }
        
        const inputField = document.getElementById('chat-input');
        if (inputField) {
            if (finalTranscript) {
                inputField.value = (inputField.value + ' ' + finalTranscript).trim();
            }
        }
        
        const textObj = document.getElementById('voice-status-text');
        if (textObj && interimTranscript) {
            textObj.innerText = `"${interimTranscript}..."`;
        }
    };
    
    recognition.onerror = function(event) {
        console.error("Error en reconocimiento de voz: ", event.error);
        stopDictation();
    };
    
    recognition.onend = function() {
        stopDictation();
    };
    
    return true;
}

function stopDictation() {
    isDictating = false;
    const btn = document.getElementById('voice-dictation-btn');
    const pulse = document.getElementById('dictation-pulse');
    const title = document.getElementById('voice-status-title');
    const text = document.getElementById('voice-status-text');
    
    if (btn) btn.classList.remove('text-primary', 'border-primary', 'shadow-[0_0_20px_rgba(255,45,120,0.5)]');
    if (pulse) pulse.classList.add('hidden');
    if (title) {
        title.innerText = 'ESCUCHA DESACTIVADA';
        title.classList.remove('text-primary', 'animate-pulse');
    }
    if (text) text.innerText = 'Pulsa el micrófono para dictar tus comandos a la tripulación.';
    
    const inputField = document.getElementById('chat-input');
    if (inputField && inputField.value.trim() !== '') {
        const sidebar = document.getElementById('chat-sidebar');
        if (sidebar && sidebar.style.display === 'none') {
            toggleChat(); // Abre el chat si está oculto
        }
        inputField.focus();
    }
}

function toggleDictation() {
    if (!recognition) {
        const supported = initSpeechRecognition();
        if (!supported) {
            alert("Tu navegador no soporta reconocimiento de voz (Usa Chrome o Edge).");
            return;
        }
    }
    
    if (isDictating) {
        recognition.stop();
    } else {
        try {
            recognition.start();
        } catch(e) {
            console.error(e);
        }
    }
}
