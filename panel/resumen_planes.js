// Vistas del comparador. Las probabilidades y los indicadores proceden del catálogo Python.
function changeView(view) {
  for (const [key,id] of Object.entries({plans:'f02PlansView',runs:'f02RunsView',sources:'f02SourcesView'})) {
    $(id).hidden=key!==view;
    document.querySelector('[data-f02="'+key+'"]').setAttribute('aria-pressed',String(key===view));
  }
  if(view==='plans') drawRisk();
  if(view==='runs' && plan) {drawScenarioPeaks();drawEvidence();}
}
document.querySelectorAll('[data-f02]').forEach(b=>b.onclick=()=>changeView(b.dataset.f02));
$('f02RunDrawer').addEventListener('toggle',()=>{if($('f02RunDrawer').open)drawEvidence();});

function inspectPlan(p,uid) {
  changeView('runs');
  choose(p.id,uid);
  $('f02RunDrawer').open=!!uid;
}
function decision(plans) {
  const study=cohort.mesh_study;
  $('f02Convergence').hidden=!study;
  $('f02ConvergenceTable').replaceChildren();
  if(study){
    $('f02Convergence').open=true;
    $('f02ConvergenceNote').textContent='Caso M4_SS de cada plan · criterio del estudio: cambios espaciales ≤'+fmt(study.spatial_tolerance_C)+' °C y temporales ≤'+fmt(study.temporal_tolerance_C)+' °C. '+study.note+' '+study.assessments.map(a=>'Tcol '+a.temperature_C+' °C: '+(a.status==='SENSITIVITY_WITHIN_DECLARED_TOLERANCES'?'cambios dentro de tolerancias':'tolerancias pendientes de demostrar')).join(' · ');
    $('f02ConvergenceTable').append(table(['Tcol [°C]','Malla','Celdas totales / activas','Voxel [mm]','Δt [s]','Tmax [°C]','ΔT est. [°C]','S25 sin soporte','Error volumen IFC','Duración real [s]'],study.rows.filter(r=>r.source_id==='fv_M4_SS').map(r=>[
      r.temperature_C,r.shape.join(' × '),r.cells_total+' / '+r.cells_active,r.spacing_m.map(v=>fmt(v*1000)).join(' × '),r.dt_s,fmt(r.Tmax_C),fmt(r.Delta_C),r.unknown,fmt(r.volume_error_pct)+' %',fmt(r.runtime_s)
    ])));
  }
  const meshRows=plans.flatMap(p=>(p.parameters?.mesh_comparison||[]).map(r=>[
    p.name,r.source,r.cells_total,r.cells_active,r.spacing_m.map(v=>fmt(v*1000)).join(' × '),
    fmt(r.volume_error_pct)+' %',fmt(r.Tmax_change_C),fmt(r.Delta_change_C),
    r.missing_S25,fmt(r.coverage*100)+' %'
  ]));
  $('f02MeshReport').hidden=!meshRows.length;
  $('f02MeshReport').open=!!meshRows.length;
  $('f02MeshTable').replaceChildren();
  if(meshRows.length)$('f02MeshTable').append(table(['Plan','Fuente','Celdas totales','Celdas activas finales','Voxel [mm]','Error de volumen IFC','Cambio Tmax [°C]','Cambio ΔT est. [°C]','S25 sin cobertura','Área aire reconstruida'],meshRows));
  const pass=plans.filter(p=>riskOf(p).compliance==='CUMPLE').sort((a,b)=>(a.D_h??Infinity)-(b.D_h??Infinity));
  const unknown=plans.filter(p=>riskOf(p).compliance==='INDETERMINADO').length;
  const completed=plans.reduce((count,p)=>count+p.runs.filter(r=>r.status==='COMPLETED').length,0);
  const expected=cohort.expected||[];
  const sources=new Set(expected.map(s=>s.source_id).filter(Boolean)).size;
  const climates=new Set(expected.map(s=>s.climate_id).filter(Boolean)).size;
  const population=[plans.length+(plans.length===1?' plan':' planes'),
    completed+(completed===1?' corrida disponible':' corridas disponibles'),
    expected.length?expected.length+(expected.length===1?' escenario por plan':' escenarios por plan'):'Sin catálogo probabilístico',
    sources? sources+(sources===1?' fuente de calor':' fuentes de calor'):'',
    climates? climates+(climates===1?' clima':' climas'):''];
  $('f02Population').textContent=population.filter(Boolean).join(' · ')+
    (expected.length===1?'. Conjunto exploratorio de un solo escenario.':'.');
  const durations=pass.map(p=>p.D_h).filter(Number.isFinite);
  const fastest=Math.min(...durations);
  const ties=pass.filter(p=>p.D_h===fastest);
  $('f02DecisionTitle').textContent=estimated()?'Planes dentro del criterio estimado':'Planes con cumplimiento formal';
  $('f02Conclusion').textContent=pass.length
    ? pass.length+' de '+plans.length+' planes quedan en o bajo el 5 % de riesgo conjunto en el conjunto seleccionado. '+
      (ties.length?(ties.length===1?'Menor duración entre ellos: ':ties.length+' planes comparten la menor duración: ')+fmt(fastest)+' h. ':'')+
      (estimated()?'S25 estimado a 25 mm del IFC.':'')
    : unknown?'Cumplimiento indeterminado. Hay '+unknown+' planes sin evidencia suficiente para decidir.':
      'Ningún plan evaluado en este conjunto cumple el criterio del 5 %.';
  const list=$('f02Shortlist');list.replaceChildren();
  if(pass.length)list.append(table(['Plan','Duración [h]','Tmax [°C]','ΔT S25 est. [°C]','Margen a 20 °C','Riesgo conjunto [%]','Corridas'],pass.map(p=>{
    const b=E('button','Ver '+p.evaluated+(p.evaluated===1?' corrida':' corridas'),'secondary');b.onclick=()=>inspectPlan(p);
    return [p.name,fmt(p.D_h),fmt(p.Tmax_C),fmt(p.Delta_estimate_C),Number.isFinite(p.Delta_estimate_C)?fmt(20-p.Delta_estimate_C)+' °C':'—',pct(riskOf(p).P_f),b];
  })));
  $('f02FullPlans').open=!pass.length;
  return ties[0]||pass[0];
}
function scenarioRows() {
  const runs=plan.runs, risk=riskOf(plan);
  const criteria=[
    ['Tmax > 70 °C','I_T',risk.P_T],
    ['ΔT > 20 °C'+(estimated()?' · estimado':''),estimated()?'I_Delta_estimated':'I_Delta',risk.P_Delta],
    ['Al menos uno',estimated()?'I_F_estimated':'I_F',risk.P_f]
  ];
  $('f02Frequency').replaceChildren(table(['Criterio','Superan / evaluables','Escenarios previstos','Excedencia ponderada'],criteria.map(([label,key,prob])=>{
    const known=runs.filter(r=>typeof r[key]==='boolean');
    return [label,known.filter(r=>r[key]).length+' / '+known.length,plan.expected||'Sin catálogo',Number.isFinite(prob)?pct(prob)+' %':'Indeterminada'];
  })));
  const source=r=>r.source_id.replace(/^fv_/,'');
  const temps=Array.from(new Set(plan.parameters?.placement||[])).map(v=>fmt(v,1)).join(' / ')||'—';
  $('f02Individual').replaceChildren(table(['Fuente','Clima','Peso','Tcol [°C]','Tmax [°C]','ΔT S25 est. [°C]','Qué supera','Campo y curvas'],runs.map(r=>{
    const t=r.I_T,d=r[criteria[1][1]];
    const state=t&&d?'Ambos límites':t===true?'Tmax'+(d==null?' · ΔT pendiente':''):d===true?'ΔT'+(t==null?' · Tmax pendiente':''):
      t===false&&d===false?'Ninguno':'Indeterminado';
    const b=E('button','Explorar','quiet');b.onclick=()=>{inspectPlan(plan,r.uid);$('f02RunDrawer').scrollIntoView({block:'start'});};
    return [source(r),r.climate_id,r.weight??'—',temps,fmt(r.Tmax_C),fmt(r.Delta_estimate_C),state,b];
  })));
  drawScenarioPeaks();
}
function drawScenarioPeaks() {
  if(!plan||$('f02RunsView').hidden)return;
  for(const [id,key,limit] of [['f02ScatterT','Tmax_C',70],['f02ScatterD','Delta_estimate_C',20]]) {
    const {g,w,h}=box($(id),205),runs=plan.runs;
    const vals=runs.map(r=>r[key]).filter(Number.isFinite);
    const high=Math.ceil((Math.max(limit,...vals)+4)/10)*10,low=Math.floor(Math.min(0,...vals)/10)*10;
    const y=v=>h-50-(v-low)/(high-low)*(h-80);
    for(const tick of new Set([low,limit,high])) {
      g.strokeStyle=tick===limit?'#efac7e':'#38516a';g.setLineDash(tick===limit?[5,4]:[]);
      g.beginPath();g.moveTo(40,y(tick));g.lineTo(w-15,y(tick));g.stroke();
      g.fillStyle='#c2d1de';g.fillText(tick+'°',7,y(tick)+3);
    }
    g.setLineDash([]);
    runs.forEach((r,i)=>{
      const x=40+(i+.5)*(w-55)/runs.length;
      g.fillStyle='#b1c5d7';g.textAlign='center';g.fillText(String(i+1),x,h-29);
      if(Number.isFinite(r[key])){g.fillStyle=r[key]>limit?'#f9af78':'#65d9c6';g.beginPath();g.arc(x,y(r[key]),4,0,2*Math.PI);g.fill();}
      g.textAlign='left';
    });
    g.fillStyle='#bdd1df';g.fillText('Corrida · orden de la tabla',40,h-7);
  }
}
