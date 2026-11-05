(function(){'use strict';
const $=id=>document.getElementById(id),data=JSON.parse($('foundation-data').textContent),palette=['#6a9eaa','#d1ad71','#b47470'];
const state={visible:data.capas.map(()=>true),view:'orbit',zoom:1},fmt=(v,d=2)=>v.toLocaleString('es-CL',{maximumFractionDigits:d,minimumFractionDigits:d});
const dims=data.max.map((v,i)=>v-data.min[i]);
$('foundationDimensions').textContent=`Base ${fmt(dims[0])} × ${fmt(dims[1])} m · altura total ${fmt(dims[2])} m · diámetro superior ${fmt(data.capas.at(-1).max[0]-data.capas.at(-1).min[0])} m`;
const layers=$('foundationLayers');
data.capas.forEach((c,i)=>{const row=document.createElement('div');row.className='foundation-layer';const label=document.createElement('label');label.className='check';const input=document.createElement('input');input.type='checkbox';input.checked=true;input.setAttribute('aria-label','Mostrar '+c.nombre);input.onchange=()=>{state.visible[i]=input.checked;draw();};const swatch=document.createElement('i');swatch.style.background=palette[i%3];const title=document.createElement('b');title.textContent=c.nombre;label.append(input,swatch,title);const note=document.createElement('p');note.textContent=`z: ${fmt(c.min[2])} → ${fmt(c.max[2])} m · espesor ${fmt(c.max[2]-c.min[2])} m\nVolumen IFC: ${fmt(c.volumen_m3)} m³`;const solo=document.createElement('button');solo.className='quiet';solo.textContent='Ver sólo esta capa';solo.onclick=()=>{state.visible=state.visible.map((_,j)=>j===i);sync();draw();};row.append(label,note,solo);layers.append(row);});
$('foundationSource').textContent=`Fuente: ${data.archivo} · huella ${data.sha256.slice(0,12)}… · volumen total ${fmt(data.capas.reduce((s,c)=>s+c.volumen_m3,0))} m³.`;
$('foundationVolumeAudit').textContent='Volumen objetivo comunicado: 636,775 m³ (pendiente de confirmar su despiece). El IFC actual, con tres alturas de 1,10 m, suma '+fmt(data.capas.reduce((v,c)=>v+c.volumen_m3,0),3)+' m³. La resolución de voxel no cambia ese volumen geométrico. Revisar cotas antes de modificar la forma.';
function sync(){layers.querySelectorAll('input').forEach((e,i)=>e.checked=state.visible[i]);}
function draw(){
 if($('foundationPage').hidden)return;const canvas=$('foundationCanvas'),rect=canvas.getBoundingClientRect(),w=Math.max(280,rect.width),h=Math.max(300,rect.height),dpr=devicePixelRatio||1;canvas.width=w*dpr;canvas.height=h*dpr;const g=canvas.getContext('2d');g.scale(dpr,dpr);g.fillStyle='#fafbf7';g.fillRect(0,0,w,h);
 const explosion=Number($('explodeFoundation').value),yaw=Number($('foundationYaw').value)*Math.PI/180,pitch=Number($('foundationPitch').value)*Math.PI/180;
 $('explodeValue').textContent=fmt(explosion)+' m entre capas';$('foundationVisible').textContent=`${state.visible.filter(Boolean).length} / ${data.capas.length} capas visibles`;
 $('foundationViewTitle').textContent=explosion?'Capas separadas para inspección':'Fundación ensamblada';
 const zcenter=(dims[2]+explosion*(data.capas.length-1))/2,angle=state.view==='plan'?0:yaw,tilt=state.view==='plan'?Math.PI/2:state.view==='profile'?0:pitch;
 function transform(p,off=0){const x=p[0]-(data.min[0]+data.max[0])/2,y=p[1]-(data.min[1]+data.max[1])/2,z=p[2]-data.min[2]+off-zcenter,a=Math.cos(angle)*x-Math.sin(angle)*y,b=Math.sin(angle)*x+Math.cos(angle)*y;return [a,b*Math.sin(tilt)-z*Math.cos(tilt),b*Math.cos(tilt)+z*Math.sin(tilt)];}
 const corners=[];for(const x of [data.min[0],data.max[0]])for(const y of [data.min[1],data.max[1]])for(const z of [data.min[2],data.max[2]+explosion*(data.capas.length-1)])corners.push(transform([x,y,z]));
 const rx=Math.max(...corners.map(p=>p[0]))-Math.min(...corners.map(p=>p[0])),ry=Math.max(...corners.map(p=>p[1]))-Math.min(...corners.map(p=>p[1]));
 const scale=Math.min((w-130)/Math.max(rx,1),(h-110)/Math.max(ry,1))*state.zoom;
 function project(p,off=0){const t=transform(p,off);return [w/2+t[0]*scale,h/2+t[1]*scale,t[2]];}
 const line=(p,q,color='#b6c8b8')=>{g.strokeStyle=color;g.lineWidth=1;g.beginPath();g.moveTo(...project(p));g.lineTo(...project(q));g.stroke();};
 if(state.view!=='profile'){for(let a=-10;a<=10;a+=2){line([a,-10,0],[a,10,0],'#e3e9df');line([-10,a,0],[10,a,0],'#e3e9df');}}
 const triangles=[];
 data.capas.forEach((c,i)=>{if(!state.visible[i])return;for(const t of c.triangulos){
  // No dibujar tapas interiores coincidentes de dos vertidas ensambladas.
  if(explosion===0&&((i>0&&state.visible[i-1]&&t.every(p=>Math.abs(p[2]-c.min[2])<1e-6))||(i<data.capas.length-1&&state.visible[i+1]&&t.every(p=>Math.abs(p[2]-c.max[2])<1e-6))))continue;
  const p=t.map(v=>project(v,i*explosion)),u=t[1].map((v,a)=>v-t[0][a]),v=t[2].map((v,a)=>v-t[0][a]),n=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]],norm=Math.hypot(...n)||1,light=.67+.3*Math.abs((n[0]*.25+n[1]*-.4+n[2]*.88)/norm);triangles.push({p,depth:p.reduce((s,p)=>s+p[2],0)/3,color:palette[i%3],light});}});
 triangles.sort((a,b)=>a.depth-b.depth);
 for(const t of triangles){const rgb=t.color.match(/\w\w/g).map(v=>parseInt(v,16));g.fillStyle=`rgb(${rgb.map(v=>Math.round(v*t.light)).join(',')})`;g.strokeStyle=g.fillStyle;g.lineWidth=.45;g.beginPath();t.p.forEach((p,i)=>i?g.lineTo(p[0],p[1]):g.moveTo(p[0],p[1]));g.closePath();g.fill();g.stroke();}
 g.font='12px Segoe UI';g.fillStyle='#53665b';g.textAlign='center';g.fillText(`${fmt(dims[0])} × ${fmt(dims[1])} m · H ${fmt(dims[2])} m`,w/2,h-20);
 const label=(p,text,color)=>{const xy=project(p);g.fillStyle=color;g.textAlign='left';g.fillText(text,xy[0]+6,xy[1]-4);};
 const origin=[-10,-10,0];line(origin,[-6,-10,0],'#a27660');line(origin,[-10,-6,0],'#6a9581');line(origin,[-10,-10,3],'#758bad');label([-6,-10,0],'x','#a27660');label([-10,-6,0],'y','#6a9581');label([-10,-10,3],'z','#758bad');
 $('foundationViewNote').textContent=state.view==='plan'?'Planta del IFC: contorno octogonal y parte superior circular. Las capas superiores pueden ocultar las inferiores.':state.view==='profile'?'Perfil del IFC: tres niveles de 1,10 m; la segunda capa transiciona hacia el cilindro superior.':'Mallas trianguladas tomadas directamente del IFC, a escala física. Separar capas es sólo una ayuda visual.';
}
function mode(foundation){$('foundationPage').hidden=!foundation;$('labPage').hidden=foundation;$('modeFoundation').classList.toggle('active',foundation);$('modeLab').classList.toggle('active',!foundation);$('modeFoundation').setAttribute('aria-pressed',String(foundation));$('modeLab').setAttribute('aria-pressed',String(!foundation));if(foundation){if(window.therma?.state.playing)$('play').click();draw();}else window.therma?.render();}
$('modeFoundation').onclick=()=>mode(true);$('modeLab').onclick=()=>mode(false);
$('helpBtn').onclick=()=>{const area=$('foundationPage').hidden?$('physics'):document.querySelector('.foundation-scope');area.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});};
document.querySelectorAll('[data-fview]').forEach(b=>b.onclick=()=>{state.view=b.dataset.fview;document.querySelectorAll('[data-fview]').forEach(e=>e.classList.toggle('active',e===b));draw();});
['explodeFoundation','foundationYaw','foundationPitch'].forEach(id=>$(id).oninput=draw);
$('resetFoundation').onclick=()=>{state.visible=state.visible.map(()=>true);state.zoom=1;state.view='orbit';$('explodeFoundation').value=0;$('foundationYaw').value=-40;$('foundationPitch').value=28;document.querySelectorAll('[data-fview]').forEach(b=>b.classList.toggle('active',b.dataset.fview==='orbit'));sync();draw();};
let drag=null;const canvas=$('foundationCanvas');canvas.onpointerdown=e=>{if(state.view!=='orbit')return;drag={x:e.clientX,y:e.clientY,yaw:Number($('foundationYaw').value),pitch:Number($('foundationPitch').value)};canvas.setPointerCapture(e.pointerId);};canvas.onpointermove=e=>{if(!drag)return;$('foundationYaw').value=Math.max(-180,Math.min(180,drag.yaw+(e.clientX-drag.x)*.5));$('foundationPitch').value=Math.max(10,Math.min(80,drag.pitch+(e.clientY-drag.y)*.35));draw();};canvas.onpointerup=()=>drag=null;canvas.onpointercancel=()=>drag=null;canvas.addEventListener('wheel',e=>{e.preventDefault();state.zoom=Math.max(.5,Math.min(2,state.zoom*(e.deltaY>0?.9:1.1)));draw();},{passive:false});
$('foundationPNG').onclick=()=>{const a=document.createElement('a');a.download='fundacion-ifc-tres-capas.png';a.href=canvas.toDataURL('image/png');a.click();};
window.addEventListener('resize',draw);window.foundationViewer={data,draw,state};mode(false);
})();
