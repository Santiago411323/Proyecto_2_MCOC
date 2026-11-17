/* Compara historias guardadas en sus tiempos originales; no ejecuta el solver. */
(() => {
  const $=id=>document.getElementById(id),section=document.createElement('details');
  section.className='panel workflow-details';section.id='compareCurves';
  section.innerHTML='<summary>Comparar esta corrida con otra simulación</summary><div class="drawer-content"><label>Simulación B<select id="curveCompareSelect"><option value="">Elige una corrida guardada…</option></select></label><button type="button" id="curveRefresh" class="quiet">Actualizar lista</button><p id="curveCompareStatus" role="status"></p><div id="curveCompareMetrics" class="table-scroll"></div><div class="s25-chart-grid"><section><h3>Tmax activa [°C]</h3><canvas id="curveCompareT"></canvas></section><section><h3>ΔT S25 estimado [°C]</h3><canvas id="curveCompareD"></canvas></section></div><p class="hint">A cian · B naranja. Cada curva conserva los tiempos calculados por Python. El cursor sigue el timeline de A. El gráfico muestra el horizonte completo de ambas corridas.</p></div>';
  $('s25Results').after(section);
  let current=null,other=null,ticket=0,cache=new Map(),names=new Map();
  const fmt=v=>Number.isFinite(v)?v.toLocaleString('es-CL',{maximumFractionDigits:2}):'No disponible';
  async function json(url){const response=await fetch(url,{cache:'no-store'});if(!response.ok)throw Error('Resultado guardado no disponible.');return response.json();}
  function name(meta){
    const p=meta.config,temps=[...new Set(p.construction?.pours.map(v=>v.placement_C)||[p.initial])];
    return temps.map(fmt).join('/')+' °C · '+(p.construction?.curve?.column||p.construction?.model||p.source)+' · '+p.days+' días · '+meta.simulation_id.slice(0,8);
  }
  async function catalog(){
    const selected=$('curveCompareSelect').value,options=new Map();
    const results=await Promise.allSettled([json('/api/comparison-f02'),json('/api/simulation-catalog')]);
    if(results[0].status==='fulfilled')for(const c of results[0].value.cohorts)for(const p of c.plans)for(const r of p.runs){
      if(!r.simulation_id)continue;
      const label=p.name+' · '+r.source_id+' · '+r.days+' días · '+r.simulation_id.slice(0,8);
      options.set(r.simulation_id,label);
    }
    if(results[1].status==='fulfilled')for(const r of results[1].value.simulations)if(!options.has(r.simulation_id))
      options.set(r.simulation_id,'Corrida local · '+r.days+' días · '+r.simulation_id.slice(0,8));
    names=options;const list=$('curveCompareSelect');list.replaceChildren(new Option('Elige una corrida guardada…',''));
    for(const [id,label] of options)if(id!==current?.simulation_id)list.add(new Option(label,id));
    if(options.has(selected)&&selected!==current?.simulation_id)list.value=selected;
  }
  function draw(id,key,limit){
    const cv=$(id),w=Math.max(300,cv.clientWidth||550),h=235,dpr=Math.min(devicePixelRatio,2);
    cv.width=w*dpr;cv.height=h*dpr;cv.style.width='100%';cv.style.height=h+'px';const g=cv.getContext('2d');g.scale(dpr,dpr);
    const pair=[current,other].filter(Boolean),end=Math.max(1,...pair.map(m=>m.config.days*24));
    let low=0,high=limit+5;
    for(const m of pair)for(const row of m.s25_ifc?.history||[])if(Number.isFinite(row[key])){high=Math.max(high,row[key]+3);low=Math.min(low,row[key]-2);}
    const L=43,R=w-15,T=28,B=h-38,X=t=>L+t/end*(R-L),Y=t=>B-(t-low)/(high-low)*(B-T);
    g.font='11px Segoe UI';for(let j=0;j<5;j++){const value=low+(high-low)*j/4;g.strokeStyle='#304558';g.beginPath();g.moveTo(L,Y(value));g.lineTo(R,Y(value));g.stroke();g.fillStyle='#b5c7d3';g.fillText(fmt(value),3,Y(value)+3);g.fillText(fmt(end*j/4),L+(R-L)*j/4-12,h-19);}
    g.fillText('Tiempo desde t0 [h]',L,h-3);
    g.strokeStyle='#e7ad81';g.setLineDash([4,4]);g.beginPath();g.moveTo(L,Y(limit));g.lineTo(R,Y(limit));g.stroke();g.setLineDash([]);g.fillText('Límite '+limit+' °C',R-95,Y(limit)-6);
    pair.forEach((m,j)=>{g.strokeStyle=['#63dac5','#ffb274'][j];g.lineWidth=2;g.beginPath();let pen=false;for(const row of m.s25_ifc?.history||[]){
      const v=row[key];if(!Number.isFinite(v)){pen=false;continue;}if(pen)g.lineTo(X(row.time_s/3600),Y(v));else g.moveTo(X(row.time_s/3600),Y(v));pen=true;
    }g.stroke();});
    const r=window.therma.getResult();g.strokeStyle='#c9dce7';g.beginPath();g.moveTo(X(r.frameTimes[window.therma.state.frame]/3600),T);g.lineTo(X(r.frameTimes[window.therma.state.frame]/3600),B);g.stroke();
  }
  function render(){
    if(!current||!section.open)return;
    $('curveCompareMetrics').replaceChildren();
    const table=document.createElement('table');table.className='plan-table';
    const head=table.createTHead().insertRow();for(const label of ['Corrida','Tmax global [°C]','ΔT máximo estimado [°C]']){const th=document.createElement('th');th.textContent=label;head.append(th);}
    const body=table.createTBody();[current,other].filter(Boolean).forEach((m,j)=>{
      const row=body.insertRow();for(const text of [(j?'B · ':'A · ')+(names.get(m.simulation_id)||name(m)),fmt(m.metrics.maxField),fmt(m.s25_ifc?.peak_estimate?.DeltaT_estimate_C)])row.insertCell().textContent=text;
    });$('curveCompareMetrics').append(table);
    draw('curveCompareT','Tmax_C',70);draw('curveCompareD','DeltaT_estimate_C',20);
  }
  async function select(){
    const id=$('curveCompareSelect').value,request=++ticket;other=null;render();if(!id)return;
    $('curveCompareStatus').textContent='Cargando la corrida B…';
    try{
      const meta=cache.get(id)||await json('/api/results/'+id+'/metadata.json');
      if(request!==ticket)return;if(!meta.s25_ifc)throw Error('Esta corrida no contiene historia S25. Elige otra simulación.');
      cache.set(id,meta);other=meta;
      $('curveCompareStatus').textContent='Comparación cargada. A es la corrida abierta en el visor. S25 estimado en ambas.';
      render();
    }catch(e){if(request===ticket)$('curveCompareStatus').textContent=e.message;}
  }
  function update(){
    const r=window.therma?.getResult();if(!r?.metadata?.s25_ifc){section.hidden=true;return;}section.hidden=false;
    if(current!==r.metadata){current=r.metadata;ticket++;other=null;$('curveCompareSelect').value='';$('curveCompareStatus').textContent='Selecciona B para compararla con la corrida actual A.';catalog().catch(()=>{});}
    render();
  }
  section.addEventListener('toggle',update);$('curveCompareSelect').onchange=select;
  $('curveRefresh').onclick=()=>catalog().catch(e=>$('curveCompareStatus').textContent=e.message);
  window.addEventListener('therma:frame',update);window.addEventListener('resize',render);
  new MutationObserver(update).observe($('executionState'),{childList:true,subtree:true,characterData:true});
  update();
})();
