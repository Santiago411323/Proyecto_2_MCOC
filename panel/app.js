(function(){'use strict';
const $=id=>document.getElementById(id),num=id=>Number($(id).value),DAY=86400;
const colors=['#317f75','#c88d4e','#8370a5','#bd6370','#6c88a8'];
const S={dim:3,result:null,pins:[],frame:0,worker:null,playing:false,playTime:0,view:'flat',lastConfig:null,runId:0};
const fmt=(n,d=2)=>Number.isFinite(n)?n.toLocaleString('es-CL',{maximumFractionDigits:d,minimumFractionDigits:d}):'—';
const sci=n=>Math.abs(n)<.001&&n!==0?n.toExponential(2):fmt(n,3);
const faceNames=['x−','x+','y−','y+','z−','z+'];
function buildFaces(){
 $('faces').innerHTML=faceNames.map((name,i)=>`<div class="face" data-face="${i}"><div class="face-head"><b>${name}</b><select id="ft${i}" aria-label="Tipo de borde ${name}"><option value="D">Dirichlet</option><option value="N">Neumann</option><option value="R" selected>Robin</option></select></div><div class="field-grid"><label data-kind="temp">T borde / aire [°C]<input id="fb${i}" type="number" step="any" value="20"></label><label data-kind="flux">Flujo saliente [W/m²]<input id="fq${i}" type="number" step="any" value="0"></label><label data-kind="h">h [W/(m²·K)]<input id="fh${i}" type="number" step="any" value="10" min="0"></label><label data-kind="R">R [m²·K/W]<input id="fr${i}" type="number" step="any" value="0" min="0"></label></div></div>`).join('');
 for(let i=0;i<6;i++)$('ft'+i).onchange=()=>{visibility();dirty();};
}
function visibility(){
 document.querySelectorAll('[data-axis]').forEach(e=>e.hidden=Number(e.dataset.axis)>S.dim);
 document.querySelectorAll('[data-dim]').forEach(e=>{e.classList.toggle('active',Number(e.dataset.dim)===S.dim);e.setAttribute('aria-pressed',String(Number(e.dataset.dim)===S.dim));});
 document.querySelectorAll('[data-face]').forEach(e=>{const i=Number(e.dataset.face),type=$('ft'+i).value;e.hidden=i>=2*S.dim;e.querySelectorAll('[data-kind]').forEach(f=>{f.hidden=type==='D'?f.dataset.kind!=='temp':type==='N'?f.dataset.kind!=='flux':f.dataset.kind==='flux';});});
 $('amplitudeLabel').hidden=$('initialType').value!=='sine';
 $('sourceFields').hidden=$('source').value==='none';$('periodLabel').hidden=$('source').value!=='pulse';document.querySelector('.formula').hidden=$('source').value!=='pulse';
 $('targetLabel').hidden=!$('calibrate').checked;$('qmaxLabel').hidden=$('calibrate').checked;
 $('factorLabel').hidden=$('dtMode').value==='manual';$('dtLabel').hidden=$('dtMode').value!=='manual';
 $('alphaRead').textContent=`α = ${sci(num('k')/(num('rho')*num('cp')))} m²/s · β = h/k por cara`;
 $('dimensionHint').textContent=S.dim===1?'1D: temperatura uniforme en la sección transversal; área de referencia 1 m².':S.dim===2?'2D: uniforme en la dirección no resuelta; espesor de referencia 1 m.':'3D: se resuelven largo, ancho y altura; todas las caras son editables.';
}
function gather(){return {dim:S.dim,L:['lx','ly','lz'].map(num),n:['nx','ny','nz'].map(num),k:num('k'),rho:num('rho'),cp:num('cp'),initial:num('initial'),initialType:$('initialType').value,amplitude:num('amplitude'),source:$('source').value,period:num('period')*DAY,qmax:num('qmax'),calibrate:$('calibrate').checked&&$('source').value!=='none',target:num('target'),days:num('days'),dtMode:$('dtMode').value,dt:num('dt'),factor:num('factor'),frames:65,faces:faceNames.map((_,i)=>({type:$('ft'+i).value,temp:num('fb'+i),flux:num('fq'+i),h:num('fh'+i),R:num('fr'+i)}))};}
function setConfig(p){
 if(!p||![1,2,3].includes(p.dim)||!Array.isArray(p.L)||p.L.length!==3||!Array.isArray(p.n)||p.n.length!==3||!Array.isArray(p.faces)||p.faces.length!==6)throw Error('El archivo no contiene ajustes válidos de THERMA.');
 S.dim=p.dim;['lx','ly','lz'].forEach((id,i)=>$(id).value=p.L[i]);['nx','ny','nz'].forEach((id,i)=>$(id).value=p.n[i]);
 ['k','rho','cp','initial','initialType','amplitude','source','qmax','target','days','dtMode','dt','factor'].forEach(id=>{if(p[id]!==undefined)$(id).value=p[id];});$('period').value=p.period/DAY;$('calibrate').checked=!!p.calibrate;
 p.faces.forEach((b,i)=>{if(!['D','N','R'].includes(b.type))throw Error('Tipo de borde desconocido.');$('ft'+i).value=b.type;[['fb','temp'],['fq','flux'],['fh','h'],['fr','R']].forEach(([prefix,key])=>$(prefix+i).value=b[key]);});
 visibility();dirty();
}
function applyFaces(){for(let i=0;i<2*S.dim;i++){$('ft'+i).value=$('globalType').value;$('fb'+i).value=$('globalTemp').value;$('fq'+i).value=$('globalFlux').value;$('fh'+i).value=$('globalH').value;$('fr'+i).value=$('globalR').value;}visibility();dirty();}
function dirty(){if(S.result)$('stale').hidden=false;visibility();}
function preset(name){
 const p={dim:3,L:[3,3,.6],n:[30,30,6],k:2,rho:2400,cp:900,initial:20,initialType:'uniform',amplitude:30,source:'pulse',period:2*DAY,qmax:1905.58,calibrate:true,target:70,days:14,dtMode:'auto',dt:300,factor:.7,faces:Array.from({length:6},()=>({type:'R',temp:20,flux:0,h:10,R:0}))};
 if(name==='d20'||name==='d30')p.faces.forEach(b=>{b.type='D';b.temp=name==='d30'?30:20;});
 if(name==='adiabatic')p.faces.forEach(b=>b.type='N');
 if(name==='bar3'){p.L=[4,2,1];p.n=[32,16,8];p.faces.forEach(b=>b.type='D');}
 if(name==='sine'){p.dim=1;p.L=[1,1,1];p.n=[40,16,8];p.initialType='sine';p.amplitude=40;p.source='none';p.calibrate=false;p.days=1;p.faces.forEach(b=>b.type='D');}
 setConfig(p);$('globalType').value=p.faces[0].type;$('globalTemp').value=p.faces[0].temp;
}
function error(message){$('error').textContent=message;$('error').hidden=false;$('status').textContent='Revisa los datos y vuelve a ejecutar.';}
function run(){
 if(S.worker)S.worker.terminate();stop();$('error').hidden=true;const p=gather();
 if(!['uniform','sine'].includes(p.initialType)||!['none','constant','pulse'].includes(p.source)||!['auto','manual'].includes(p.dtMode))return error('Selecciona opciones válidas.');
 const blob=new Blob([$('solver-source').textContent],{type:'text/javascript'}),url=URL.createObjectURL(blob);
 const worker=new Worker(url);URL.revokeObjectURL(url);S.worker=worker;S.runId++;const id=S.runId;
 $('run').disabled=true;$('cancel').hidden=false;$('progress').style.width='3%';$('status').textContent=p.calibrate?'Calculando la respuesta y calibrando Qmax…':'Integrando el balance de energía…';
 worker.onmessage=e=>{if(id!==S.runId)return;const msg=e.data;if(msg.type==='progress'){$('progress').style.width=Math.max(3,msg.value*100)+'%';return;}
  finish();if(msg.type==='error'){error(msg.message);return;}
  S.result=msg.result;S.lastConfig=JSON.parse(JSON.stringify(p));S.frame=0;S.hasPlayed=false;$('timeline').max=S.result.fields.length-1;
  $('stale').hidden=true;const labels={D:'Dirichlet',N:'Neumann',R:'Robin'},types=[...new Set(p.faces.slice(0,2*p.dim).map(b=>labels[b.type]))];
  S.result.label=`${p.dim}D · ${types.join(' + ')}`;$('resultState').textContent=`${S.result.label} · ${S.result.N.toLocaleString('es-CL')} celdas`;
  $('metricPeak').innerHTML=`${fmt(S.result.maxCenter)}<small> °C</small>`;
  $('metricTime').textContent=`Día ${fmt(S.result.peakTime/DAY,3)} · primer máximo / inicio de meseta`;
  $('metricQ').innerHTML=`${fmt(S.result.qmax,1)}<small> W/m³</small>`;
  $('metricQNote').textContent=p.source==='none'?'Fuente desactivada':p.calibrate?`Calibrado para ${fmt(p.target,1)} °C en el centro`:'Intensidad definida manualmente';
  $('metricDt').innerHTML=`${fmt(S.result.dt,1)} <small>/ ${fmt(S.result.dtMax,1)} s</small>`;
  $('metricMesh').textContent=`Δ = ${S.result.dx.map(v=>fmt(v,4)).join(' × ')} m`;
  $('metricEnergy').innerHTML=`${S.result.residual.toExponential(1)}<small> J</small>`;
  $('numericalDetail').textContent=`α = ${S.result.alpha.toExponential(4)} m²/s · ${S.result.steps.toLocaleString('es-CL')} pasos · malla ${S.result.n.join(' × ')} · máximo en todo el campo: ${fmt(S.result.maxField)} °C`;
  $('exactNote').textContent=S.result.exactError!==null?`Verificación sinusoidal: error máximo final vs. solución exacta = ${S.result.exactError.toExponential(3)} °C.`:p.calibrate?'Qmax se calibra al máximo central dentro de la duración seleccionada. Cada simulación puede tener un Qmax diferente.':'Una fuente positiva añade energía; los bordes determinan cuánto calor entra o sale.';
  $('status').textContent='Simulación terminada. Puedes reproducir y exportar los resultados.';$('progress').style.width='100%';
  try{localStorage.setItem('therma-config-v1',JSON.stringify(p));}catch(_){}
  const peak=S.result.peakTime;S.frame=S.result.frameTimes.reduce((best,t,i)=>Math.abs(t-peak)<Math.abs(S.result.frameTimes[best]-peak)?i:best,0);
  updateViewControls();renderLegend();render();
 };
 worker.onerror=e=>{finish();error('No se pudo ejecutar el motor: '+e.message);};worker.postMessage(p);
}
function finish(){if(S.worker)S.worker.terminate();S.worker=null;$('run').disabled=false;$('cancel').hidden=true;}
function stop(){S.playing=false;$('play').textContent='▶';$('play').setAttribute('aria-label','Reproducir animación');}
function togglePlay(){if(!S.result)return;if(S.playing){stop();return;}if(!S.hasPlayed||S.frame>=S.result.fields.length-1)S.frame=0;S.hasPlayed=true;S.playing=true;S.playTime=0;$('play').textContent='Ⅱ';$('play').setAttribute('aria-label','Pausar animación');requestAnimationFrame(tick);}
function tick(t){if(!S.playing)return;const interval=140/Number($('speed').value);if(!S.playTime||t-S.playTime>interval){S.playTime=t;render();if(S.frame>=S.result.fields.length-1){stop();return;}S.frame++;}requestAnimationFrame(tick);}
function ctx(id){const c=$(id),r=c.getBoundingClientRect(),dpr=window.devicePixelRatio||1,w=Math.max(100,r.width),h=Math.max(100,r.height);c.width=Math.round(w*dpr);c.height=Math.round(h*dpr);const g=c.getContext('2d');g.scale(dpr,dpr);g.clearRect(0,0,w,h);return {g,w,h,c};}
const stops=[[21,19,43],[85,60,118],[172,83,105],[237,144,83],[242,223,136]];
function heat(v,lo,hi){let f=Math.max(0,Math.min(.999999,(v-lo)/(hi-lo||1)))*4,i=Math.floor(f),a=stops[i],b=stops[i+1],t=f-i;return `rgb(${a.map((v,j)=>Math.round(v*(1-t)+b[j]*t)).join(',')})`;}
function range(){const r=S.result;let lo=r.config.initial,hi=r.maxField;for(const h of r.history){lo=Math.min(lo,h.min);hi=Math.max(hi,h.max);}if(hi-lo<1e-4)hi=lo+1;return [lo,hi];}
function updateViewControls(){const r=S.result;if(!r)return;const dim=r.config.dim;$('viewIso').hidden=dim!==3;$('plane').parentElement.hidden=dim!==3;$('slice').parentElement.hidden=dim!==3;if(dim!==3)S.view='flat';const axis={xy:2,xz:1,yz:0}[$('plane').value],n=r.n[axis]||1;$('slice').max=n-1;$('slice').value=Math.min(Number($('slice').value)||Math.floor(n/2),n-1);$('viewFlat').classList.toggle('active',S.view==='flat');$('viewIso').classList.toggle('active',S.view==='iso');}
function field(){const r=S.result;if(!r)return;const {g,w,h}=ctx('fieldCanvas'),F=r.fields[S.frame], [lo,hi]=range(),nx=r.n[0],ny=r.n[1]||1,nz=r.n[2]||1;
 const val=(x,y=0,z=0)=>F[x+nx*(y+ny*z)];g.font='11px Segoe UI';g.fillStyle='#65756e';
 $('colorMin').textContent=fmt(lo,1)+' °C';$('colorMax').textContent=fmt(hi,1)+' °C';$('frameLabel').textContent='Día '+fmt(r.frameTimes[S.frame]/DAY,3);$('timeline').value=S.frame;
 const plane=$('plane').value,axis=plane==='xy'?2:plane==='xz'?1:0,cut=Math.min(Number($('slice').value), (r.n[axis]||1)-1),pos=(cut+.5)*(r.dx[axis]||1);
 $('sliceLabel').textContent=`${'xyz'[axis]} = ${fmt(pos,3)} m`;
 $('fieldTitle').textContent=r.config.dim===1?'Perfil de temperatura':S.view==='iso'?'Bloque 3D y corte interior':'Campo de temperatura';
 $('fieldNote').textContent=r.config.dim===1?'Perfil 1D · bordes en las caras, valores en centros de celda':r.config.dim===2?'Campo 2D · espesor de referencia 1 m':`Corte interno ${plane.toUpperCase()} a ${'xyz'[axis]} = ${fmt(pos,3)} m · no es la cara exterior`;
 if(r.config.dim===1){
  $('fieldCanvas')._plot=null;
  const left=47,right=w-20,top=20,bottom=h-68;
  g.strokeStyle='#dce3d6';g.lineWidth=1;
  for(let j=0;j<=4;j++){const y=bottom-(bottom-top)*j/4;g.beginPath();g.moveTo(left,y);g.lineTo(right,y);g.stroke();g.fillStyle='#65756e';g.textAlign='right';g.fillText(fmt(lo+(hi-lo)*j/4,0),left-8,y+4);}
  g.fillStyle='#65756e';g.textAlign='left';g.fillText('T [°C]',7,12);g.textAlign='center';g.fillText('Posición x [m]',(left+right)/2,h-7);
  const px=x=>left+(right-left)*x/r.L[0],py=v=>bottom-(v-lo)/(hi-lo)*(bottom-top);
  g.strokeStyle='#317f75';g.lineWidth=2;g.beginPath();for(let i=0;i<nx;i++){const x=px((i+.5)*r.dx[0]),y=py(val(i));i?g.lineTo(x,y):g.moveTo(x,y);}g.stroke();
  if(r.config.initialType==='sine'){g.strokeStyle='#a1b096';g.setLineDash([4,4]);g.beginPath();for(let i=0;i<nx;i++){const x=px((i+.5)*r.dx[0]),y=py(r.config.initial+r.config.amplitude*Math.sin(Math.PI*(i+.5)/nx));i?g.lineTo(x,y):g.moveTo(x,y);}g.stroke();g.setLineDash([]);g.fillStyle='#65756e';g.textAlign='right';g.fillText('Trazo discontinuo: perfil inicial',right,15);}
  for(let i=0;i<nx;i++){g.fillStyle=heat(val(i),lo,hi);g.fillRect(left+i*(right-left)/nx,bottom+14,(right-left)/nx+1,10);}for(let j=0;j<=4;j++){g.fillStyle='#65756e';g.textAlign='center';g.fillText(fmt(j*r.L[0]/4,2),px(j*r.L[0]/4),h-28);}return;
 }
 let ax=0,ay=1;if(r.config.dim===3){if(plane==='xz'){ax=0;ay=2;}if(plane==='yz'){ax=1;ay=2;}}
 const na=r.n[ax],nb=r.n[ay],La=r.L[ax],Lb=r.L[ay];
 const fetchValue=(a,b)=>{const co=[0,0,0];co[ax]=a;co[ay]=b;if(r.config.dim===3)co[axis]=cut;return val(...co);};
 if(S.view==='iso'&&r.config.dim===3){
  const L=r.L,yaw=-.65,scale=Math.min((w-75)/(L[0]+L[1]),(h-65)/(L[2]+.43*(L[0]+L[1]))),ox=w/2,oy=h/2+20;
  const project=(x,y,z)=>[ox+(x-L[0]/2-(y-L[1]/2))*Math.cos(yaw)*scale,oy+((x-L[0]/2)+(y-L[1]/2))*.32*scale-(z-L[2]/2)*scale];
  const poly=points=>{g.beginPath();points.forEach((p,i)=>{const q=project(...p);i?g.lineTo(...q):g.moveTo(...q);});g.closePath();};
  // Back wireframe, then the physical interior slice.
  g.strokeStyle='#b3c1b3';g.lineWidth=1;
  for(let a=0;a<3;a++){const others=[0,1,2].filter(j=>j!==a);for(const b of [0,L[others[0]]])for(const c of [0,L[others[1]]]){const p=[0,0,0],q=[0,0,0];p[others[0]]=q[others[0]]=b;p[others[1]]=q[others[1]]=c;q[a]=L[a];g.beginPath();g.moveTo(...project(...p));g.lineTo(...project(...q));g.stroke();}}
  for(let b=nb-1;b>=0;b--)for(let a=0;a<na;a++){const points=[[a,b],[a+1,b],[a+1,b+1],[a,b+1]].map(([a,b])=>{const p=[0,0,0];p[ax]=a*r.dx[ax];p[ay]=b*r.dx[ay];p[axis]=pos;return p;});poly(points);g.fillStyle=heat(fetchValue(a,b),lo,hi);g.fill();}
  g.fillStyle='#53665b';g.textAlign='center';g.fillText(`x: ${r.L[0]} m · y: ${r.L[1]} m · z: ${r.L[2]} m`,w/2,h-15);$('fieldCanvas')._plot=null;
 }else{
  const scale=Math.min((w-80)/La,(h-55)/Lb),pw=La*scale,ph=Lb*scale,left=(w-pw)/2+12,top=(h-ph)/2-5;
  for(let b=0;b<nb;b++)for(let a=0;a<na;a++){g.fillStyle=heat(fetchValue(a,b),lo,hi);g.fillRect(left+a*pw/na,top+(nb-1-b)*ph/nb,pw/na+.5,ph/nb+.5);}
  g.strokeStyle='#cbd6c7';g.strokeRect(left,top,pw,ph);g.fillStyle='#65756e';g.textAlign='center';
  for(let j=0;j<=4;j++){g.fillText(fmt(La*j/4,2),left+pw*j/4,top+ph+17);g.textAlign='right';g.fillText(fmt(Lb*j/4,2),left-9,top+ph-ph*j/4+4);g.textAlign='center';}
  g.fillText(`${'xyz'[ax]} [m]`,left+pw/2,top+ph+33);g.save();g.translate(left-42,top+ph/2);g.rotate(-Math.PI/2);g.fillText(`${'xyz'[ay]} [m]`,0,0);g.restore();
  $('fieldCanvas')._plot={left,top,pw,ph,na,nb,ax,ay,axis,cut,fetchValue};
 }
}
function chart(id,series,ylabel,{target=null,cursor=null}={}){
 const {g,w,h,c}=ctx(id);if(!series.length)return;const left=54,right=w-15,top=20,bottom=h-38;let xmax=0,ymin=Infinity,ymax=-Infinity;
 series.forEach(s=>s.data.forEach(p=>{xmax=Math.max(xmax,p[0]);ymin=Math.min(ymin,p[1]);ymax=Math.max(ymax,p[1]);}));if(target!==null){ymin=Math.min(ymin,target);ymax=Math.max(ymax,target);}if(ymin===ymax){ymin-=1;ymax+=1;}const pad=(ymax-ymin)*.1;ymin-=pad;ymax+=pad;xmax=xmax||1;
 const X=t=>left+t/xmax*(right-left),Y=v=>bottom-(v-ymin)/(ymax-ymin)*(bottom-top);
 g.font='10px Segoe UI';g.lineWidth=1;g.strokeStyle='#e8ede3';g.fillStyle='#73816e';
 for(let j=0;j<=4;j++){const y=top+(bottom-top)*j/4;g.beginPath();g.moveTo(left,y);g.lineTo(right,y);g.stroke();g.textAlign='right';const v=ymax-(ymax-ymin)*j/4;g.fillText(Math.abs(v)>=10000?v.toExponential(1):fmt(v,Math.abs(ymax-ymin)>10?0:2),left-8,y+3);}
 const ticks=w<370?3:5;for(let j=0;j<=ticks;j++){const x=left+(right-left)*j/ticks;g.textAlign='center';g.fillText(fmt(xmax*j/ticks,1),x,bottom+16);}
 g.textAlign='left';g.fillText(ylabel,6,11);g.textAlign='center';g.fillText('Tiempo [días]',(left+right)/2,h-3);
 g.save();g.beginPath();g.rect(left,top,right-left,bottom-top);g.clip();
 if(target!==null){g.setLineDash([5,4]);g.strokeStyle='#a4afa0';g.beginPath();g.moveTo(left,Y(target));g.lineTo(right,Y(target));g.stroke();g.setLineDash([]);}
 series.forEach(s=>{g.strokeStyle=s.color;g.lineWidth=s.width||2;g.setLineDash(s.dash||[]);g.beginPath();const stride=Math.max(1,Math.ceil(s.data.length/1400));let started=false;for(let i=0;i<s.data.length;i+=stride){const p=s.data[i];started?g.lineTo(X(p[0]),Y(p[1])):g.moveTo(X(p[0]),Y(p[1]));started=true;}const last=s.data[s.data.length-1];g.lineTo(X(last[0]),Y(last[1]));g.stroke();g.setLineDash([]);});
 if(cursor!==null){g.strokeStyle='#8c9d8a';g.lineWidth=1;g.beginPath();g.moveTo(X(cursor),top);g.lineTo(X(cursor),bottom);g.stroke();}
 g.restore();c._chart={left,right,top,bottom,xmax,ymin,ymax};
}
function interpolate(hist,t,key='center'){let lo=0,hi=hist.length-1;if(t<=hist[0].t)return hist[0][key];if(t>=hist[hi].t)return hist[hi][key];while(hi-lo>1){const mid=(lo+hi)>>1;if(hist[mid].t<t)lo=mid;else hi=mid;}const f=(t-hist[lo].t)/(hist[hi].t-hist[lo].t);return hist[lo][key]*(1-f)+hist[hi][key]*f;}
function renderLegend(){const r=S.result;if(!r)return;const el=$('legend');el.replaceChildren();[r,...S.pins].forEach((v,i)=>{const span=document.createElement('span'),mark=document.createElement('i');mark.style.background=colors[i%colors.length];span.append(mark,document.createTextNode(i===0?'Actual · '+v.label:v.label));if(i>0){const b=document.createElement('button');b.textContent='×';b.setAttribute('aria-label','Quitar comparación');b.onclick=()=>{S.pins.splice(i-1,1);renderLegend();render();};span.append(b);}el.append(span);});}
function render(){if(!S.result)return;field();const r=S.result,t=r.frameTimes[S.frame]/DAY;
 chart('centerCanvas',[r,...S.pins].map((v,i)=>({color:colors[i%colors.length],data:v.history.map(p=>[p.t/DAY,p.center])})), 'T [°C]',{target:r.config.calibrate?r.config.target:null,cursor:t});
 chart('sourceCanvas',[{color:'#c88d4e',data:r.history.map(p=>[p.t/DAY,p.q])}],'q [W/m³]',{cursor:t});
 chart('energyCanvas',[{color:'#317f75',data:r.history.map(p=>[p.t/DAY,p.energy/1e6])},{color:'#c88d4e',dash:[5,4],data:r.history.map(p=>[p.t/DAY,p.net/1e6])}],'ΔE [MJ]',{cursor:t});
 $('hoverRead').textContent=`Día ${fmt(t,3)} · centro ${fmt(interpolate(r.history,t*DAY))} °C · q = ${fmt(interpolate(r.history,t*DAY,'q'),1)} W/m³`;
}
function download(name,text,type='application/json'){const url=URL.createObjectURL(new Blob([text],{type})),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),2000);}
function exportConfig(){download('therma-ajustes.json',JSON.stringify(gather(),null,2));}
function exportCSV(){if(!S.result)return;const r=S.result;const lines=['tiempo_s,tiempo_dias,T_centro_C,T_min_C,T_max_C,q_W_m3,delta_energia_J,aporte_neto_J,residual_J'];r.history.forEach(p=>lines.push([p.t,p.t/DAY,p.center,p.min,p.max,p.q,p.energy,p.net,p.residual].join(',')));download('therma-resultados.csv',lines.join('\n'),'text/csv;charset=utf-8');}
function exportField(){if(!S.result)return;const r=S.result,F=r.fields[S.frame],nx=r.n[0],ny=r.n[1]||1,nz=r.n[2]||1,lines=['tiempo_s,x_m,y_m,z_m,T_C'];for(let z=0;z<nz;z++)for(let y=0;y<ny;y++)for(let x=0;x<nx;x++)lines.push([r.frameTimes[S.frame],(x+.5)*r.dx[0],r.config.dim>=2?(y+.5)*r.dx[1]:'',r.config.dim===3?(z+.5)*r.dx[2]:'',F[x+nx*(y+ny*z)]].join(','));download('therma-campo.csv',lines.join('\n'),'text/csv;charset=utf-8');}
buildFaces();visibility();
document.querySelectorAll('[data-dim]').forEach(b=>b.onclick=()=>{S.dim=Number(b.dataset.dim);visibility();dirty();});
$('controls').addEventListener('input',dirty);$('controls').addEventListener('change',dirty);$('controls').onsubmit=e=>{e.preventDefault();run();};
$('applyFaces').onclick=applyFaces;$('run').onclick=run;$('cancel').onclick=()=>{S.runId++;finish();$('status').textContent='Cálculo detenido. Los resultados anteriores se conservan.';$('progress').style.width='0';};
$('preset').onchange=()=>{preset($('preset').value);run();};$('play').onclick=togglePlay;$('timeline').oninput=()=>{stop();S.hasPlayed=true;S.frame=Number($('timeline').value);render();};
$('viewFlat').onclick=()=>{S.view='flat';updateViewControls();render();};$('viewIso').onclick=()=>{S.view='iso';updateViewControls();render();};
$('plane').onchange=()=>{if(S.result){const a={xy:2,xz:1,yz:0}[$('plane').value];$('slice').value=Math.floor((S.result.n[a]||1)/2);}updateViewControls();render();};$('slice').oninput=render;
$('pin').onclick=()=>{if(!S.result)return;if(S.pins.length===3)S.pins.pop();S.pins.unshift({label:S.result.label+' · Q='+fmt(S.result.qmax,0),history:S.result.history});renderLegend();render();};
$('configExport').onclick=exportConfig;$('csvExport').onclick=exportCSV;$('fieldExport').onclick=exportField;$('pngExport').onclick=()=>{if(!S.result)return;const r=S.result,source=$('fieldCanvas'),c=document.createElement('canvas');c.width=source.width;c.height=source.height+140;const g=c.getContext('2d');g.fillStyle='#fafbf7';g.fillRect(0,0,c.width,c.height);g.fillStyle='#203b30';g.font='20px Segoe UI';g.fillText(`THERMA · ${r.label} · día ${fmt(r.frameTimes[S.frame]/DAY,3)}`,24,32);g.font='14px Segoe UI';g.fillText(`L = ${r.L.join(' × ')} m · ${$('fieldNote').textContent}`,24,58);g.drawImage(source,0,75);const [lo,hi]=range(),y=c.height-40;for(let i=0;i<200;i++){g.fillStyle=heat(lo+(hi-lo)*i/199,lo,hi);g.fillRect(90+i*(c.width-180)/200,y,(c.width-180)/200+1,9);}g.fillStyle='#53665b';g.font='13px Segoe UI';g.fillText(fmt(lo,1)+' °C',22,y+10);g.fillText(fmt(hi,1)+' °C',c.width-75,y+10);const a=document.createElement('a');a.href=c.toDataURL('image/png');a.download='therma-campo.png';a.click();};
$('configImport').onchange=async e=>{try{const file=e.target.files[0];if(!file)return;const p=JSON.parse(await file.text());setConfig(p);run();}catch(err){error(err.message);}e.target.value='';};
$('helpBtn').onclick=()=>$('physics').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});
$('fieldCanvas').onmousemove=e=>{const plot=$('fieldCanvas')._plot,r=S.result;if(!plot||!r){$('fieldTooltip').hidden=true;return;}const rect=e.target.getBoundingClientRect(),x=e.clientX-rect.left,y=e.clientY-rect.top;if(x<plot.left||x>plot.left+plot.pw||y<plot.top||y>plot.top+plot.ph){$('fieldTooltip').hidden=true;return;}const a=Math.min(plot.na-1,Math.floor((x-plot.left)/plot.pw*plot.na)),b=Math.min(plot.nb-1,Math.floor((1-(y-plot.top)/plot.ph)*plot.nb));$('fieldTooltip').textContent=`${'xyz'[plot.ax]}=${fmt((a+.5)*r.dx[plot.ax],3)} m · ${'xyz'[plot.ay]}=${fmt((b+.5)*r.dx[plot.ay],3)} m · ${fmt(plot.fetchValue(a,b))} °C`;$('fieldTooltip').hidden=false;};$('fieldCanvas').onmouseleave=()=>$('fieldTooltip').hidden=true;
function chartPointer(e){const r=S.result,plot=$('centerCanvas')._chart;if(!r||!plot)return;const box=e.target.getBoundingClientRect(),x=Math.max(plot.left,Math.min(plot.right,e.clientX-box.left)),day=(x-plot.left)/(plot.right-plot.left)*plot.xmax;const items=[r,...S.pins].map(v=>`${v===r?'Actual':v.label}: ${fmt(interpolate(v.history,day*DAY))} °C`);$('hoverRead').textContent=`Día ${fmt(day,3)} · ${items.join(' · ')}`;if(e.type==='click'){stop();S.frame=r.frameTimes.reduce((best,t,i)=>Math.abs(t-day*DAY)<Math.abs(r.frameTimes[best]-day*DAY)?i:best,0);render();}}
$('centerCanvas').onmousemove=chartPointer;$('centerCanvas').onclick=chartPointer;
let resizeTimer;window.addEventListener('resize',()=>{clearTimeout(resizeTimer);resizeTimer=setTimeout(render,100);});
try{const saved=localStorage.getItem('therma-config-v1');if(saved)setConfig(JSON.parse(saved));else preset('robin');}catch(_){preset('robin');}
window.therma={getResult:()=>S.result,getConfig:gather,setConfig,run,render,state:S};
run();
})();
