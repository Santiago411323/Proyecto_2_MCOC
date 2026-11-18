/* Guía y catálogo: muestra resultados reales, no contiene un solver. */
(function(root){'use strict';
function facts(r){const p=r.config,c=p.construction,fmt=v=>Number.isFinite(v)?Number(v.toFixed(3)).toLocaleString('es-CL'):'—';return [
 ['Dominio',p.geometry==='foundation'?'Fundación IFC'+(p.foundation_parameters?' · variante geométrica':''):'Ejercicio '+p.dim+'D'],
 ['Dimensiones y malla',r.L.map(fmt).join(' × ')+' m · '+r.n.join(' × ')+' celdas'],
 ['Horizonte disponible',fmt(r.frameTimes[0]/3600)+' a '+fmt(r.frameTimes.at(-1)/3600)+' h · '+r.frameTimes.length+' campos guardados'],
 ['Colocación',c?c.pours.map(v=>'V'+v.id+': '+fmt(v.start_h)+' h / '+fmt(v.placement_C)+' °C').join(' · '):'Dominio presente desde el inicio · T inicial '+fmt(p.initial)+' °C'],
 ['Material','k='+fmt(p.k)+' W/(m·K) · ρ='+fmt(p.rho)+' kg/m³ · cp='+fmt(p.cp)+' J/(kg·K)'],
 ['Calor y ambiente',(c?.curve?.column||c?.model||p.source||'no declarado')+' · '+(p.weather?'clima horario cargado':'temperaturas de borde configuradas')],
 ['Inicio climático',p.weather?.start_utc||'Sin fecha climática declarada; tiempo relativo de simulación']
 ];}
function status(raw,hasResult,detail=""){if(raw.includes("RUNNING")&&detail.includes("Cargando plan"))return ["Cargando resultado","Se están leyendo campos guardados. No se está ejecutando de nuevo el solver."];if(raw.includes('RUNNING'))return ['Calculando en Python','Python está calculando una nueva corrida. La geometría y las temperaturas previas, si existen, todavía corresponden al cálculo anterior.'];if(raw.includes('STALE'))return ['Resultados anteriores','Cambiaste las entradas. Estos resultados conservan los datos originales que ves arriba. Pulsa Ejecutar Python para obtener temperaturas con tus cambios.'];if(raw.includes('FAILED'))return ['Cálculo fallido','Revisa el mensaje de error. Una ejecución fallida no genera un resultado válido nuevo.'];return hasResult?['Resultado calculado','Reproducir sólo recorre campos ya calculados. Cambiar datos y ejecutar Python crea otra corrida con su propio identificador.']:['Sin resultados','Empieza abriendo una simulación guardada. Ejecuta Python cuando quieras probar tus propios datos.'];}
function assessment(row){
 if(row.retired)return ['historical','Fuente retirada'];
 if(row.geometry==='block')return ['unknown','Ejercicio de verificación'];
 const t=row.Tmax_C, validated=row.s25_validated===true&&Number.isFinite(row.DeltaTmax_validated_C);
 const d=validated?row.DeltaTmax_validated_C:row.Delta_estimate_C;
 if(Number.isFinite(t)&&t>70)return ['over','Tmax supera 70 °C'];
 if(Number.isFinite(d)&&d>20)return ['over',validated?'ΔT supera 20 °C':'ΔT estimado supera 20 °C'];
 if(!Number.isFinite(t)||!Number.isFinite(d))return ['unknown','Evaluación incompleta'];
 if(row.complete_sampling!==true||row.openHorizon)return ['unknown','Bajo umbrales · evidencia parcial'];
 return ['under',validated?'Bajo ambos límites · S25 validado':'Bajo ambos límites · estimado'];
}
const referenceMesh='96x96x54';
function meshKey(shape){
 return Array.isArray(shape)&&shape.length&&shape.every(n=>Number.isInteger(n)&&n>0)?shape.join('x'):'unknown';
}
if(typeof module!=='undefined'&&module.exports)module.exports={facts,status,assessment,meshKey};
if(typeof document==='undefined')return;
const $=id=>document.getElementById(id);
const element=(tag,value,cls)=>{const node=document.createElement(tag);if(value!=null)node.textContent=value;if(cls)node.className=cls;return node;};
const format=value=>Number.isFinite(value)?value.toLocaleString('es-CL',{minimumFractionDigits:2,maximumFractionDigits:2}):'—';
const localDate=value=>value?value.slice(0,10).split('-').reverse().join('/'):'';
const normalize=value=>value.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'');
const identified=id=>/^[0-9a-f]{32}$/.test(id||'');
const pageSize=12;
let lastResult=null,loading=false,catalogReady=false,priorStatus='',catalogNames=new Map(),rows=[],catalogIssue='',listPage=0,passPage=0,studyStep='';
async function catalog(){
 if(loading)return;
 loading=true;
 $('simulationCatalogNote').textContent='Leyendo corridas guardadas…';
 try{
  const replies=await Promise.allSettled(['/api/simulation-catalog','/api/comparison-f02'].map(async url=>{
   const response=await fetch(url,{cache:'no-store'});
   if(!response.ok)throw Error('Catálogo no disponible.');
   return response.json();
  }));
  const local=replies[0].value?.simulations||[];
  const cohorts=replies[1].value?.cohorts||[];
  const runs=new Map();
  for(const item of local){
   let title=item.title||((item.geometry==='foundation'?'Fundación IFC':'Ejercicio '+item.dim+'D')+' · '+item.simulation_id.slice(0,8));
   if(Number.isFinite(item.basal_contact_R)&&title.includes('nitrógeno'))title+=' · R de contacto basal '+format(item.basal_contact_R);
   const followup=meshKey(item.shape)===referenceMesh&&item.eps_mm===100&&(item.ice_t>0||item.ice_t===0&&item.pours>1);
   runs.set(item.simulation_id,{...item,title,collection:'local',can_open:true,studyStep:followup?'followup':''});
  }
  for(const cohort of cohorts)for(const plan of cohort.plans)for(const run of plan.runs){
   if(!['COMPLETED','RETIRED'].includes(run.status))continue;
   const key=run.simulation_id||run.uid;
   const previous=runs.get(key);
   const parameters=plan.parameters||{};
   const common=cohort.id.startsWith('malla-comun-');
   const step=common&&meshKey(run.shape)===referenceMesh
    ? (plan.id.startsWith('t8_eps100_base')||plan.id.startsWith('t12_eps100_base')?'ice':'reference'):'';
   if(previous&&(!run.can_open||previous.can_open)){
    if(step){previous.studyStep=step;previous.routePlan=plan.name;}
    continue;
   }
   runs.set(key,{...run,title:plan.name,collection:common?'common':'published',studyStep:step||previous?.studyStep,routePlan:step?plan.name:previous?.routePlan,
    study:cohort.title,weather_start:parameters.start_utc,placement_C:parameters.placement,
    ice_t:parameters.preenfriamiento?.balance?.total_t,
    complete_sampling:run.coverage===1,openHorizon:run.horizon_captured===false,
    retired:run.retired===true||run.status==='RETIRED'});
  }
  rows=[...runs.values()].map(row=>({...row,result:assessment(row)}))
   .sort((a,b)=>Number(Boolean(b.can_open))-Number(Boolean(a.can_open)));
  updateMeshes();
  catalogNames=new Map(rows.filter(row=>row.simulation_id).map(row=>[row.simulation_id,row.title]));
  catalogIssue=replies.some(r=>r.status==='rejected')?'Parte del catálogo no está disponible.':'';
  catalogReady=true;
  renderLibraries();
 }catch(error){
  $('simulationCatalogNote').textContent='No se pudo cargar el catálogo. '+error.message;
  $('simulationPassNote').textContent=$('simulationCatalogNote').textContent;
 }finally{loading=false;update();}
}
function updateMeshes(){
 const sizes=[...new Set(rows.map(row=>meshKey(row.shape)))].filter(size=>size!==referenceMesh);
 sizes.sort((a,b)=>a.localeCompare(b,'es',{numeric:true}));
 for(const id of ['simulationMesh','simulationPassMesh']){
  const select=$(id),chosen=select.value;
  const options=[['all','Todas las mallas'],[referenceMesh,'96 × 96 × 54 · referencia'],
   ...sizes.map(size=>[size,size==='unknown'?'Malla sin informar':size.split('x').join(' × ')])];
  select.replaceChildren(...options.map(([size,label])=>new Option(label,size)));
  select.value=options.some(([size])=>size===chosen)?chosen:referenceMesh;
 }
}
function pagedTable(filtered,page,tableId,pagesId,changePage){
 const tableSlot=$(tableId),pages=$(pagesId);
 pages.replaceChildren();
 if(!filtered.length){tableSlot.replaceChildren(element('p','No hay corridas para mostrar.','hint'));return;}
 page=Math.min(page,Math.ceil(filtered.length/pageSize)-1);
 const start=page*pageSize, end=Math.min(start+pageSize,filtered.length);
 const table=element('table',null,'plan-table run-library-table');
 const head=table.createTHead().insertRow();
 for(const label of ['Simulación','Colocación [°C]','Tmax [°C]','ΔT S25 [°C]','Evaluación','Resultado']){
  const th=element('th',label);th.scope='col';head.append(th);
 }
 const body=table.createTBody();
 for(const row of filtered.slice(start,end)){
  const tr=body.insertRow();
  const climate=localDate(row.weather_start), retrieved=localDate(row.weather_retrieved);
  const study=row.collection==='local'?'Local':row.collection==='common'?'F02 · malla común':'Estudio publicado';
  const facts=[study,row.source_id?.replace(/^fv_/,''),row.shape?.join(' × '),row.days!=null&&row.days+' días',
   climate&&'inicio '+climate,retrieved&&'clima '+retrieved,Number.isFinite(row.ice_t)&&format(row.ice_t)+' t de hielo',
   identified(row.simulation_id)&&row.simulation_id.slice(0,8)].filter(Boolean);
  const title=(tableId==='simulationLibraryTable'&&studyStep&&row.routePlan)||row.title;
  tr.insertCell().append(element('strong',title),element('small',facts.join(' · ')));
  const placement=Array.isArray(row.placement_C)?[...new Set(row.placement_C)].map(format).join(' / '):'';
  tr.insertCell().textContent=placement||'—';
  tr.insertCell().textContent=format(row.Tmax_C);
  tr.insertCell().textContent=format(row.s25_validated&&Number.isFinite(row.DeltaTmax_validated_C)?row.DeltaTmax_validated_C:row.Delta_estimate_C);
  const badge=element('span',row.result[1],'run-assessment');badge.dataset.result=row.result[0];
  tr.insertCell().append(badge);
  const destination=tr.insertCell();
  if(row.can_open&&identified(row.simulation_id)){
   const link=element('a','Abrir corrida','run-open');
   link.href='?result='+row.simulation_id+'#simulationDesk';
   link.setAttribute('aria-label','Abrir corrida · '+title);
   destination.append(link);
  }else{
   const details=element('button','Ver resultados','quiet');
   details.type='button';
   details.onclick=()=>root.ThermaF02.openRun(row.cohort_id,row.plan_id,row.uid);
   destination.append(details,element('small','Resumen archivado'));
  }
 }
 tableSlot.replaceChildren(table);
 const back=element('button','Anterior','quiet'),next=element('button','Siguiente','quiet');
 back.type=next.type='button';back.disabled=page===0;next.disabled=end===filtered.length;
 back.onclick=()=>changePage(page-1);next.onclick=()=>changePage(page+1);
 pages.append(back,element('span',`${start+1}–${end} de ${filtered.length}`),next);
}
function renderLibraries(){
 if(!catalogReady)return;
 const category=$('simulationCollection').value,search=normalize($('simulationSearch').value.trim());
 const selectedMesh=$('simulationMesh').value,passMesh=$('simulationPassMesh').value;
 const counts={1:'una un',2:'dos',3:'tres',4:'cuatro',5:'cinco',6:'seis',10:'diez',12:'doce'};
 const filtered=rows.filter(r=>(category==='all'||r.collection===category)&&
  (selectedMesh==='all'||meshKey(r.shape)===selectedMesh)&&(!studyStep||r.studyStep===studyStep)&&
  search.split(/\s+/).every(term=>normalize([r.title,r.routePlan,r.studyStep==='ice'?'hielo moldaje eps protección basal':'',counts[r.pours],r.study,r.source_id,r.simulation_id,r.shape?.join(' '),r.result[1]].filter(Boolean).join(' ')).includes(term)));
 const passing=rows.filter(r=>r.result[0]==='under'&&(passMesh==='all'||meshKey(r.shape)===passMesh));
 const pathLabels={reference:'Ruta · referencias de construcción',ice:'Ruta · candidatos con hielo',followup:'Ruta · pruebas posteriores'};
 const evidence={
  reference:'Compara el efecto de los cronogramas de referencia. El diferencial estimado guía la búsqueda de medidas térmicas.',
  ice:'Compara los dos objetivos de colocación con el mismo moldaje, EPS y protección basal. Revisa las cuatro fuentes de cada candidato para ver su margen frente a 20 °C.',
  followup:'Estas pruebas locales permiten explorar otras secuencias y protecciones. Revisa el clima de cada fila antes de compararlas con el lote F02.'
 };
 $('studyEvidence').textContent=evidence[studyStep]||'Selecciona un paso para ver sus corridas en la tabla.';
 const pathMissing=(studyStep==='reference'||studyStep==='ice')&&!rows.some(r=>r.studyStep===studyStep);
 $('simulationCatalogNote').textContent=pathMissing
  ? 'El servidor todavía no publica este lote F02 de 96 × 96 × 54. Abre la versión actualizada de THERMA y vuelve a consultar la ruta.'
  : (studyStep?pathLabels[studyStep]+' · ':'')+filtered.length+(filtered.length===1?' corrida encontrada. ':' corridas encontradas. ')+catalogIssue;
 $('simulationPassNote').textContent=passing.length+(passing.length===1?' corrida bajo ambos umbrales. ':' corridas bajo ambos umbrales. ')+'«Estimado» indica S25 pendiente de validación física. Cada fila corresponde a un escenario, con su propia malla y clima. '+catalogIssue;
 pagedTable(filtered,listPage,'simulationLibraryTable','simulationLibraryPages',page=>{listPage=page;renderLibraries();});
 pagedTable(passing,passPage,'simulationPassTable','simulationPassPages',page=>{passPage=page;renderLibraries();});
}
for(const [id,event] of [['simulationCollection','change'],['simulationSearch','input'],['simulationMesh','change']]){
 $(id).addEventListener(event,()=>{if(id!=='simulationSearch')setStudyStep('');listPage=0;renderLibraries();});
}
$('simulationPassMesh').addEventListener('change',()=>{passPage=0;renderLibraries();});
function setStudyStep(step){
 studyStep=step;
 $('resetStudyPath').hidden=!step;
 for(const button of document.querySelectorAll('[data-study-step]')){
  button.setAttribute('aria-pressed',String(button.dataset.studyStep===step));
 }
}
for(const button of document.querySelectorAll('[data-study-step]')){
 button.addEventListener('click',()=>{
  setStudyStep(button.dataset.studyStep);
  $('simulationMesh').value=referenceMesh;
  $('simulationCollection').value='all';
  $('simulationSearch').value='';
  listPage=0;
  renderLibraries();
 });
}
$('resetStudyPath').onclick=()=>{setStudyStep('');listPage=0;renderLibraries();};
$('findNitrogenRuns').onclick=()=>{
 setStudyStep('');
 $('simulationSearch').value='nitrógeno';
 $('simulationCollection').value='local';
 $('simulationMesh').value=referenceMesh;
 listPage=0;
 renderLibraries();
};
function update(){const r=window.therma?.getResult(),raw=$('executionState').textContent,[label,explanation]=status(raw,!!r,$('executionOrigin').textContent),running=raw.includes('RUNNING');$('resultsPage').classList.toggle('has-loaded-run',!!r);$('resultsPage').classList.toggle('working-on-run',running||raw.includes('FAILED'));$('simulationStatus').textContent=label;$('simulationExplain').textContent=explanation;$('simulationPlay').disabled=!r;$('simulationPeak').disabled=!r;$('simulationRun').disabled=running;$('simulationCancel').hidden=!running;
 $('simulationPlay').textContent=window.therma?.state.playing?'Pausar reproducción':'Reproducir resultados';
 if(r){$('simulationTitle').textContent=(catalogNames.get(r.simulationId)||'Corrida '+(r.simulationId||'de verificación'));
 $('simulationDescription').textContent='Datos del resultado guardado · '+(r.engine||'motor no declarado')+' · instante mostrado: '+(r.frameTimes[window.therma.state.frame]/3600).toLocaleString('es-CL',{maximumFractionDigits:2})+' h. '+(r.config.geometry==='foundation'?'Geometría provisional; S25 estimado, sin cumplimiento validado.':'Ejercicio de verificación: no representa la fundación.');
 if(lastResult!==r){lastResult=r;$('simulationGuide').open=false;$('simulationInputs').replaceChildren();for(const [name,value] of facts(r)){const dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=name;dd.textContent=value;$('simulationInputs').append(dt,dd);}
  if(location.hash==='#simulationDesk'&&new URLSearchParams(location.search).get('result')===r.simulationId)requestAnimationFrame(()=>$('simulationDesk').scrollIntoView());
 }}
 if(raw!==priorStatus){if(raw.includes('COMPLETED'))catalog();priorStatus=raw;}}
$('refreshSimulations').onclick=catalog;
$('simulationPlay').onclick=()=>{$('play').click();update();document.querySelector('.timeline-shell').scrollIntoView({block:'center',behavior:'smooth'});};
$('simulationPeak').onclick=()=>{const r=window.therma.getResult();if(!r)return;const peak=window.ThermaIntelligence.globalMaximum(r);if(peak.frame<0)return;window.therma.setFrame(peak.frame);if(r.n.length===3){$('locateHot').click();$('viewerSection').scrollIntoView({block:'start',behavior:'smooth'});}else document.querySelector('.timeline-shell').scrollIntoView({block:'center',behavior:'smooth'});update();};
$('simulationRun').onclick=()=>{$('engineMode').value='python';$('engineMode').dispatchEvent(new Event('change'));$('run').click();};$('simulationCancel').onclick=()=>$('cancel').click();
window.addEventListener('therma:frame',update);window.addEventListener('therma:inputs',update);new MutationObserver(update).observe($('executionState'),{childList:true,subtree:true,characterData:true});
update();catalog();
})(typeof window==='undefined'?globalThis:window);
