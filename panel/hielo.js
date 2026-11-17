/* El balance y ambas historias provienen de Python. */
(() => {
  const el = id => document.getElementById(id);
  const fmt = n => n.toLocaleString('es-CL', {maximumFractionDigits: 2});
  const form = el('iceForm');
  el('configurePage').querySelector('.page-heading').after(form);
  let job = null, busy = false, revision = 0, timer, reading = 0;

  function inputs() {
    const number = id => el(id).valueAsNumber;
    return {mode: el('iceMode').value, value: number('iceValue'), reference_C: number('iceRef'),
      water_kg_m3: number('iceWaterMass'), water_C: number('iceWater'), ice_C: number('iceTemp')};
  }
  async function api(url, body) {
    const opts = body === undefined ? {} : {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)};
    const res = await fetch(url, {cache:'no-store', ...opts});
    if (res.status === 404) throw Error('Reinicia servidor_therma.py para usar el ensayo de hielo.');
    const data = await res.json();
    if (!res.ok) throw Error(data.message || 'Error al consultar Python.');
    return data;
  }
  function preview() {
    const rev = ++revision;
    clearTimeout(timer);
    el('iceRun').disabled = true;
    el('icePreview').textContent = 'Calculando el balance…';
    timer = setTimeout(async () => {
      try {
        const m = await api('/api/ice-preview', inputs());
        if (rev !== revision) return;
        el('icePreview').textContent = fmt(m.dose_kg_m3)+' kg de hielo/m³ · '+fmt(m.total_t)+' t para '+fmt(m.volume_m3)+' m³. Quedan '+fmt(m.liquid_kg_m3)+' kg de agua líquida/m³. Reemplazo: '+fmt(m.replaced_pct)+' %. Colocación: '+fmt(m.placement_C)+' °C (reducción de '+fmt(m.reduction_C)+' °C).';
        el('iceRun').disabled = busy;
      } catch (e) { if (rev === revision) el('icePreview').textContent = e.message; }
    }, 140);
  }
  form.addEventListener('input', e => {
    if (e.target.id === 'iceMode') {
      const target = el('iceMode').value === 'target';
      el('iceValueLabel').textContent = target ? 'Colocación objetivo [°C]' : 'Dosis [kg de hielo/m³]';
      el('iceValue').value = target ? 8 : 60;
    }
    el('iceStatus').textContent = 'Entradas modificadas. Ejecuta el ensayo para obtener nuevos campos.';
    preview();
  });
  form.addEventListener('toggle', e => { if (e.target === form && form.open) preview(); });

  function plot(id, cases, col, limit) {
    const svg = el(id), svgNS = 'http://www.w3.org/2000/svg';
    svg.replaceChildren(); svg.setAttribute('viewBox','0 0 420 164'); svg.style.width='100%';
    const add = (tag, attrs, label) => {
      const node = document.createElementNS(svgNS,tag);
      for (const [key,v] of Object.entries(attrs)) node.setAttribute(key,v);
      if (label !== undefined) node.textContent=label;
      svg.append(node);
    };
    const maxH=Math.max(...cases.map(c=>c.series.at(-1)[0]));
    let top=limit, bottom=0;
    for (const c of cases) for (const row of c.series) {
      top=Math.max(top,row[col]); bottom=Math.min(bottom,row[col]);
    }
    top=Math.ceil((top+2)/5)*5; bottom=Math.floor(bottom/5)*5;
    const x=h=>35+355*h/maxH, y=v=>125-110*(v-bottom)/(top-bottom);
    const label=(x,y,t)=>add('text',{x,y,fill:'#c5d5e0','font-size':11},t);
    for(const v of [bottom,limit,top]){
      add('line',{x1:35,x2:390,y1:y(v),y2:y(v),stroke:v===limit?'#e0ae7e':'#536777','stroke-dasharray':v===limit?'4 4':'none'});
      label(5,y(v)+4,fmt(v));
    }
    for(const frac of [0,.25,.5,.75,1]) label(x(maxH*frac)-4,145,fmt(maxH*frac/24));
    label(190,160,'Días');
    cases.forEach((c,i)=>add('polyline',{fill:'none',stroke:['#f9af66','#4cdbd1'][i],'stroke-width':2,
      points:c.series.map(r=>x(r[0]).toFixed(2)+','+y(r[col]).toFixed(2)).join(' ')}));
  }
  function showResults() {
    window.ThermaNavigation.go('results');
    const drawer=el('iceResults').closest('details');if(drawer)drawer.open=true;
    el('iceResults').scrollIntoView({block:'start'});
  }
  async function load(id) {
    const token=++reading, url='/api/results/'+id+'/ice_study.json';
    const d=await api(url); if(token!==reading)return;
    const [a,b]=d.cases;
    el('iceRows').replaceChildren();
    for (const c of d.cases) {
      const row=el('iceRows').insertRow(), m=c.mix;
      for(const value of [c.label,fmt(m.dose_kg_m3),fmt(m.total_t),fmt(m.liquid_kg_m3),fmt(m.placement_C),
          fmt(c.Tmax_C)+' a '+fmt(c.peak_h)+' h',fmt(c.delta_C)+' a '+fmt(c.delta_h)+' h']) row.insertCell().textContent=value;
      const link=document.createElement('a');link.href='?result='+c.simulation_id;link.textContent='Abrir campo';row.insertCell().append(link);
    }
    const change=(before,after)=>after===before?'se mantuvo':(after<before?'bajó ':'subió ')+fmt(Math.abs(after-before))+' °C';
    el('iceFinding').textContent='Colocación continua de '+fmt(d.duration_h)+' h · M4_SS · 42 días. Con hielo, Tmax '+change(a.Tmax_C,b.Tmax_C)+' y el diferencial estimado '+change(a.delta_C,b.delta_C)+'. '+(b.delta_C>20?'El diferencial estimado supera 20 °C.':'El diferencial estimado queda dentro de 20 °C.')+
      (d.cases.every(c=>c.coverage_complete)?'':' Cobertura S25 parcial.');
    el('iceDownload').href=url;plot('iceTPlot',d.cases,1,70);plot('iceDPlot',d.cases,2,20);
    el('iceResults').hidden=false;el('iceCompareLink').hidden=false;
  }
  async function archive(preferred) {
    const {studies}=await api('/api/ice-studies');
    if(!studies.length)return;
    el('iceArchive').replaceChildren(...studies.map((id,i)=>new Option('Ensayo '+(studies.length-i)+' · '+id.slice(0,8),id)));
    el('iceArchive').value=preferred||studies[0];await load(el('iceArchive').value);
  }
  el('iceArchive').onchange=()=>load(el('iceArchive').value).catch(e=>el('iceFinding').textContent=e.message);
  el('iceCompareLink').onclick=showResults;
  el('iceCancel').onclick=async()=>{try{if(job)await api('/api/cancel/'+job,{});}catch(e){el('iceStatus').textContent=e.message;}};
  el('iceRun').onclick=async()=>{
    if(busy)return;
    busy=true;el('iceRun').disabled=true;
    const fields=[...form.querySelectorAll('input,select')];
    fields.forEach(f=>f.disabled=true);
    try{
      el('iceStatus').textContent='Enviando el ensayo a Python…';
      const task=await api('/api/ice-studies',inputs());job=task.simulation_id;el('iceCancel').hidden=false;
      while(true){
        const state=await api(task.status_url);
        if(state.status==='COMPLETED')break;
        if(state.status!=='RUNNING')throw Error(state.message||state.status);
        el('iceStatus').textContent=(state.progress<.5?'1 de 2 · Sin hielo':'2 de 2 · Con hielo')+' · '+Math.floor(100*state.progress)+' % del ensayo';
        await new Promise(resolve=>setTimeout(resolve,650));
      }
      await archive(job);el('iceStatus').textContent='Ambas corridas guardadas en 03 Simulaciones.';showResults();
    }catch(e){el('iceStatus').textContent=e.message;}
    finally{job=null;busy=false;el('iceCancel').hidden=true;fields.forEach(f=>f.disabled=false);preview();}
  };
  archive().catch(e=>el('iceStatus').textContent=e.message);
})();
