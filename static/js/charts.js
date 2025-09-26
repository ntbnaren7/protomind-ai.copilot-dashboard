// ====== Config ======
const POLL_MS = 1000;
const HISTORY_MAX = 30; // compact history

// ====== State ======
let labels = [];
let sensorsHist = {
  temperature_c: [],
  pressure_bar:   [],
  load_pct:       [],
  throughput:     [],
  vibration:      [],
  humidity:       []
};
let riskHist = [];

// ====== Utils ======
function pushLimited(arr, v, max = HISTORY_MAX) {
  arr.push(v);
  if (arr.length > max) {
    arr.splice(0, arr.length - max); // HARD TRIM
  }
}
function fmt(v, d=2){ return (v===null||v===undefined||Number.isNaN(v)) ? "--" : Number(v).toFixed(d); }

// ====== KPI mount/update ======
function mountKPI(id, label, unit){
  const el = document.getElementById(id);
  if (!el) return;
  el.innerHTML = `
    <div class="kpi-card">
      <div class="kpi-value" id="${id}-value">--</div>
      <div class="kpi-label">${label} (${unit})</div>
    </div>`;
}
function setKPI(id, text){
  const el = document.getElementById(`${id}-value`);
  if (el) el.textContent = text;
}
window.addEventListener("DOMContentLoaded", ()=>{
  mountKPI("kpi-temperature","Temperature","°C");
  mountKPI("kpi-pressure","Pressure","bar");
  mountKPI("kpi-load","Load","%");
  mountKPI("kpi-throughput","Throughput","u/s");
  mountKPI("kpi-vibration","Vibration","mm/s");
  mountKPI("kpi-humidity","Humidity","%");
});

// ====== Charts ======
function makeSensorChart(ctx){
  return new Chart(ctx,{
    type:"line",
    data:{
      labels,
      datasets:[
        {label:"Temp (°C)", data:sensorsHist.temperature_c, borderColor:"#ff6b6b", backgroundColor:"#ff6b6b33", tension:.35, pointRadius:0, borderWidth:1.5},
        {label:"Pressure (bar)", data:sensorsHist.pressure_bar, borderColor:"#ffd166", backgroundColor:"#ffd16633", tension:.35, pointRadius:0, borderWidth:1.5},
        {label:"Load (%)", data:sensorsHist.load_pct, borderColor:"#4dabf7", backgroundColor:"#4dabf733", tension:.35, pointRadius:0, borderWidth:1.5},
        {label:"Throughput (u/s)", data:sensorsHist.throughput, borderColor:"#12b886", backgroundColor:"#12b88633", tension:.35, pointRadius:0, borderWidth:1.5},
        {label:"Vibration (mm/s)", data:sensorsHist.vibration, borderColor:"#e599f7", backgroundColor:"#e599f733", tension:.35, pointRadius:0, borderWidth:1.5},
        {label:"Humidity (%)", data:sensorsHist.humidity, borderColor:"#94d82d", backgroundColor:"#94d82d33", tension:.35, pointRadius:0, borderWidth:1.5}
      ]
    },
    options:{
      responsive:true, maintainAspectRatio:false,
      scales:{ x:{ticks:{color:"#9aa3ab"}}, y:{beginAtZero:true, ticks:{color:"#9aa3ab"}} },
      plugins:{ legend:{ display:false } } // minimal
    }
  });
}
function makeRiskChart(ctx){
  return new Chart(ctx,{
    type:"line",
    data:{ labels, datasets:[{label:"Risk", data:riskHist, borderColor:"#00d8ff", backgroundColor:"#00d8ff33", tension:.35, pointRadius:0, borderWidth:1.5}] },
    options:{
      responsive:true, maintainAspectRatio:false,
      scales:{ x:{ticks:{color:"#9aa3ab"}}, y:{min:0, max:1, ticks:{color:"#9aa3ab"}} },
      plugins:{ legend:{ display:false } }
    }
  });
}
let sensorChart, riskChart;
window.addEventListener("DOMContentLoaded", ()=>{
  sensorChart = makeSensorChart(document.getElementById("sensorChart"));
  riskChart   = makeRiskChart(document.getElementById("riskChart"));
});

// ====== Stress controls ======
async function triggerStress(seconds=30, intensity=0.9){
  try{ await fetch(`/stress/start?seconds=${seconds}&intensity=${intensity}`, {method:"POST"}); }
  catch(e){ console.error("stress start failed", e); }
}
async function stopStress(){
  try{ await fetch(`/stress/stop`, {method:"POST"}); }
  catch(e){ console.error("stress stop failed", e); }
}
window.addEventListener("DOMContentLoaded", ()=>{
  document.getElementById("btn-stress")?.addEventListener("click", ()=> triggerStress(30,0.9));
  document.getElementById("btn-stress-stop")?.addEventListener("click", ()=> stopStress());
});

// ====== Recommendation ======
function recommend(s, risk, d){
  if (d==null) return "Show the ArUco marker to enable precise distance monitoring.";
  if (risk>=0.7) return "CRITICAL — Auto-STOP active. Increase distance and lower load.";
  if (risk>=0.5){
    if (s.temperature_c>75 || s.pressure_bar>4.0) return "WARNING — Reduce speed/load to drop temperature/pressure.";
    return "WARNING — Maintain distance and monitor vibration levels.";
  }
  return "SAFE — Conditions nominal. Maintain current settings.";
}

// ====== Poll loop ======
async function tick(){
  try{
    const r = await fetch("/sensor_data");
    const data = await r.json();
    const s = data.sensors||{};
    const risk = Number(data.risk ?? 0);
    const dist = data.distance_m;

    const ts = new Date().toLocaleTimeString();
    pushLimited(labels, ts);
    pushLimited(sensorsHist.temperature_c, Number(s.temperature_c ?? 0));
    pushLimited(sensorsHist.pressure_bar,   Number(s.pressure_bar ?? 0));
    pushLimited(sensorsHist.load_pct,       Number(s.load_pct ?? 0));
    pushLimited(sensorsHist.throughput,     Number(s.throughput ?? 0));
    pushLimited(sensorsHist.vibration,      Number(s.vibration ?? 0));
    pushLimited(sensorsHist.humidity,       Number(s.humidity ?? 0));
    pushLimited(riskHist, risk);

    sensorChart?.update();
    riskChart?.update();

    setKPI("kpi-temperature", fmt(s.temperature_c,1));
    setKPI("kpi-pressure",    fmt(s.pressure_bar,2));
    setKPI("kpi-load",        fmt(s.load_pct,0));
    setKPI("kpi-throughput",  fmt(s.throughput,0));
    setKPI("kpi-vibration",   fmt(s.vibration,2));
    setKPI("kpi-humidity",    fmt(s.humidity,0));

    const stateEl = document.getElementById("system-state");
    if (stateEl){
      stateEl.textContent = data.system_state || "RUNNING";
      stateEl.classList.toggle("status-running", data.system_state==="RUNNING");
      stateEl.classList.toggle("status-stopped", data.system_state==="STOPPED");
      stateEl.style.transform="scale(1.04)";
      setTimeout(()=>stateEl.style.transform="scale(1.0)",120);
    }

    const stress = data.stress || {active:false,seconds_left:0};
    const banner = document.getElementById("stress-banner");
    const timer  = document.getElementById("stress-timer");
    if (banner && timer){
      if (stress.active){ banner.classList.remove("d-none"); timer.textContent = String(stress.seconds_left); }
      else { banner.classList.add("d-none"); }
    }

    const rec = document.getElementById("recommendation");
    if (rec) rec.textContent = recommend(s, risk, dist);

  }catch(e){ console.error("poll failed", e); }
}
setInterval(tick, POLL_MS);
tick();
