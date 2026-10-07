document.addEventListener("DOMContentLoaded", () => {
    loadConfig();
    checkStatus();
    startLogStream();
});

let evtSource = null;

async function loadConfig() {
    try {
        const response = await fetch('/api/config');
        
        if (!response.ok) {
            const errorData = await response.json();
            alert("Configuration Error: " + (errorData.error || "Failed to load config.json"));
            return;
        }

        const data = await response.json();
        
        if (data.credentials) {
            document.getElementById('username').value = data.credentials.username || '';
            document.getElementById('password').value = data.credentials.password || '';
        }
        if (data.cities) {
            const checkboxes = document.querySelectorAll('#citiesGroup input[type="checkbox"]');
            checkboxes.forEach(cb => {
                cb.checked = data.cities.includes(cb.value);
            });
            updateDropdownText();
        }
        if (data.dates && data.dates.length > 0) {
            document.getElementById('datesContainer').innerHTML = '';
            data.dates.forEach(d => addDateRow(d.year, d.month, d.range));
        } else {
            addDateRow(); // default empty row
        }
        if (data.proxies) {
            document.getElementById('proxies').value = data.proxies.join(', ');
        }
    } catch (e) {
        console.error("Failed to load config", e);
    }
}

async function saveConfig() {
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const checkedCities = Array.from(document.querySelectorAll('#citiesGroup input[type="checkbox"]:checked')).map(cb => cb.value);
    const proxiesStr = document.getElementById('proxies').value;
    
    const dateRows = document.querySelectorAll('.date-row');
    const dates = [];
    dateRows.forEach(row => {
        const year = row.querySelector('.year-select').value;
        const month = row.querySelector('.month-select').value;
        const range = row.querySelector('.range-input').value.trim();
        if (range) {
            dates.push({ year, month, range });
        }
    });
    
    // Original config is needed to preserve other fields (like security answers)
    const currentConfigReq = await fetch('/api/config');
    const config = await currentConfigReq.json();
    
    if (!config.credentials) config.credentials = {};
    config.credentials.username = username;
    config.credentials.password = password;
    
    config.cities = checkedCities;
    config.dates = dates;
    config.proxies = proxiesStr.split(',').map(p => p.trim()).filter(p => p);
    
    const btn = document.querySelector('.btn-save');
    btn.textContent = "Saving...";
    
    await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
    });
    
    setTimeout(() => {
        btn.textContent = "Save Configuration";
        btn.style.background = "var(--success)";
        setTimeout(() => { btn.style.background = ""; }, 1000);
    }, 500);
}

async function checkStatus() {
    try {
        const res = await fetch('/api/status');
        const data = await res.json();
        updateUIState(data.running);
    } catch(e) {}
}

function updateUIState(isRunning) {
    const badge = document.getElementById('statusBadge');
    const startBtn = document.getElementById('startBtn');
    const stopBtn = document.getElementById('stopBtn');
    
    if (isRunning) {
        badge.textContent = "Running";
        badge.className = "status-badge running";
        startBtn.disabled = true;
        stopBtn.disabled = false;
    } else {
        badge.textContent = "Stopped";
        badge.className = "status-badge stopped";
        startBtn.disabled = false;
        stopBtn.disabled = true;
    }
}

async function startBot() {
    const res = await fetch('/api/start', { method: 'POST' });
    const data = await res.json();
    if (data.status === 'success') {
        updateUIState(true);
        appendLog("System: Bot starting...", "sys-msg");
    } else {
        alert("Failed to start: " + data.message);
    }
}

async function stopBot() {
    const res = await fetch('/api/stop', { method: 'POST' });
    const data = await res.json();
    if (data.status === 'success') {
        updateUIState(false);
        appendLog("System: Stop signal sent to Bot.", "sys-msg");
    } else {
        alert("Failed to stop: " + data.message);
    }
}

function startLogStream() {
    if (evtSource) {
        evtSource.close();
    }
    
    evtSource = new EventSource("/api/logs");
    evtSource.onmessage = function(event) {
        if (event.data === "keepalive") return;
        
        // Parse basic log levels
        let cssClass = "log-entry";
        if (event.data.includes("INFO")) cssClass += " log-info";
        else if (event.data.includes("ERROR")) cssClass += " log-error";
        else if (event.data.includes("WARNING")) cssClass += " log-warn";
        
        appendLog(event.data, cssClass);
        checkStatus(); // Poll status periodically when logs arrive
    };
    
    evtSource.onerror = function(err) {
        console.error("EventSource failed:", err);
    };
}

function appendLog(msg, cssClass="log-entry") {
    const container = document.getElementById('logsContainer');
    const el = document.createElement('div');
    el.className = cssClass;
    el.innerHTML = msg; // Allows <br> from Python
    container.appendChild(el);
    container.scrollTop = container.scrollHeight;
}

function addDateRow(year="", month="", range="") {
    const container = document.getElementById('datesContainer');
    const row = document.createElement('div');
    row.className = 'date-row';
    
    // Generate Year Options
    let yearOptions = '';
    const currentYear = new Date().getFullYear();
    for(let i=0; i<3; i++) {
        const y = currentYear + i;
        yearOptions += `<option value="${y}" ${year == y ? 'selected' : ''}>${y}</option>`;
    }
    if(year && year < currentYear) yearOptions += `<option value="${year}" selected>${year}</option>`;

    // Generate Month Options
    const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    let monthOptions = '';
    for(let i=0; i<12; i++) {
        // config.json uses month index (0-11 or 1-12 depending on bot, original prompt showed "6" for July)
        // Actually original config showed "month": "7" for August or July? Usually 1-indexed in human config, but let's assume raw string value
        // The original script asked for numbers 0-11. We will use 0-11 as values.
        monthOptions += `<option value="${i}" ${month == i ? 'selected' : ''}>${months[i]}</option>`;
    }

    row.innerHTML = `
        <select class="year-select">${yearOptions}</select>
        <select class="month-select">${monthOptions}</select>
        <input type="text" class="range-input" placeholder="e.g. 10-25" value="${range}">
        <button type="button" class="btn-sm btn-remove" onclick="this.parentElement.remove()">X</button>
    `;
    
    container.appendChild(row);
}

// Dropdown Logic
function toggleDropdown() {
    document.getElementById("citiesGroup").classList.toggle("show");
}

function updateDropdownText() {
    const checkedBoxes = document.querySelectorAll('#citiesGroup input[type="checkbox"]:checked');
    const headerText = document.querySelector('.dropdown-header');
    
    if (checkedBoxes.length === 0) {
        headerText.textContent = "Choose the cities... ▼";
    } else {
        headerText.textContent = checkedBoxes.length + " cities selected ▼";
    }
}

// Close dropdown if clicked outside
window.onclick = function(event) {
    if (!event.target.matches('.dropdown-header') && !event.target.closest('.dropdown-content')) {
        var dropdowns = document.getElementsByClassName("dropdown-content");
        for (var i = 0; i < dropdowns.length; i++) {
            var openDropdown = dropdowns[i];
            if (openDropdown.classList.contains('show')) {
                openDropdown.classList.remove('show');
            }
        }
    }
}
