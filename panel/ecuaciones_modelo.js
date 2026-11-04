/* Álgebra de fronteras del motor oficial. No integra la ecuación del calor. */
(function(root){'use strict';
const names=['x−','x+','y−','y+','z−','z+'];
const finite=(v)=>typeof v==='number'&&Number.isFinite(v);
const f=v=>finite(v)?Number(v.toPrecision(7)).toString():'incógnita';
function layers(parts){return parts.reduce((sum,p)=>{if(!p.enabled)return sum;if(!finite(p.e)||p.e<0||!finite(p.k)||p.k<=0)throw Error('Espesor no negativo y conductividad positiva requeridos.');return sum+p.e/p.k;},0);}
function faceClass(r,index,face,frame){
 if(!r||!Number.isInteger(index)||index<0||index>=r.fields[frame].length||face>=2*r.n.length)return 'unselected';
 const active=i=>(!r.config.mask||r.config.mask[i]>0)&&(!r.activeFrames||r.activeFrames[frame][i]===1);
 if(!active(index))return 'inactive';
 const n=r.n,ijk=[index%n[0],Math.floor(index/n[0])%(n[1]||1),Math.floor(index/(n[0]*(n[1]||1)))],a=Math.floor(face/2),next=ijk[a]+(face%2?1:-1);
 if(next>=0&&next<n[a]){const j=index+(face%2?1:-1)*(a===0?1:a===1?n[0]:n[0]*n[1]);if(active(j))return 'internal';}
 if(r.config.environment?.soil&&face===4&&ijk[2]===0)return 'soil';
 return 'air';
}
function compatible(config,r){return !!r&&config.geometry===r.config.geometry&&config.dim===r.config.dim&&config.n.slice(0,config.dim).every((x,i)=>x===r.n[i])&&config.L.slice(0,config.dim).every((x,i)=>Math.abs(x-r.L[i])<1e-9)&&JSON.stringify(config.origin)===JSON.stringify(r.config.origin)&&JSON.stringify(config.mask)===JSON.stringify(r.config.mask);}
function describe(config,face,{cellTemperature=null,classification=null}={}){
 const a=Math.floor(face/2),b=config.faces[face],d=config.L[a]/config.n[a],k=config.k,rows=[],add=(s,meaning,value,unit)=>rows.push([s,meaning,value,unit]);
 if(classification==='inactive')return {type:'inactive',rows,formula:'Hormigón todavía no colocado',substitution:'Sin temperatura ni intercambio térmico de hormigón activo.',explanation:'NOT YET POURED',flux:null};
 if(classification==='internal')return {type:'internal',rows,formula:'Pⱼ→ᵢ = Gᵢⱼ (Tⱼ − Tᵢ)',substitution:'Gᵢⱼ = A / (Δnᵢ/(2kᵢ) + Δnⱼ/(2kⱼ))',explanation:'Interfaz interna entre celdas activas: conducción conservativa y contacto perfecto, sin borde de aire. Un corte visual no crea una superficie física.',flux:null};
 const soil=config.environment?.soil&&face===4,tc=finite(cellTemperature)?cellTemperature:null;
 if(!finite(k)||k<=0||!finite(d)||d<=0)throw Error('k, longitud y número de celdas deben ser positivos y finitos.');
 if(soil){const s=config.environment.soil;if(!finite(s.temperature_C)||!finite(s.depth_m)||s.depth_m<=0||!finite(s.conductivity_W_mK)||s.conductivity_W_mK<=0||!finite(s.contact_R_m2K_W)||s.contact_R_m2K_W<0)throw Error('Revisa los parámetros de suelo.');
 const rc=d/(2*k),rs=s.depth_m/s.conductivity_W_mK,R=rc+rs+s.contact_R_m2K_W,q=tc===null?null:(tc-s.temperature_C)/R;
 add('T_celda','Centro de celda de hormigón',tc,'°C');add('Ts','Reservorio de suelo',s.temperature_C,'°C');add('Δn','Tamaño normal',d,'m');add('kc','Conductividad del hormigón',k,'W/(m·K)');add('Ls','Distancia efectiva de suelo',s.depth_m,'m');add('ks','Conductividad efectiva del suelo',s.conductivity_W_mK,'W/(m·K)');add('Rc','Contacto',s.contact_R_m2K_W,'m²·K/W');add('Rtotal','Media celda + contacto + suelo',R,'m²·K/W');
 return {type:'soil',rows,flux:q,resistance:R,formula:'q″salida = (T_celda − Ts) / [Δn/(2kc) + Rc + Ls/ks]',substitution:`R″total = ${f(rc)} + ${f(s.contact_R_m2K_W)} + ${f(rs)} = ${f(R)} m²·K/W\nq″salida = (${f(tc)} − ${f(s.temperature_C)}) / ${f(R)} W/m²`,explanation:'Contacto basal exclusivo con reservorio de suelo efectivo. No es convección de aire. La energía positiva hacia el suelo sale del hormigón; el ledger Python de energía entrante usa el signo opuesto.'};}
 if(b.type==='D'){if(!finite(b.temp))throw Error('Temperatura impuesta finita requerida.');add('T_superficie','Temperatura en la frontera',b.temp,'°C');add('Tb','Temperatura impuesta',b.temp,'°C');return {type:'D',rows,flux:null,formula:'T_superficie = Tb',substitution:`T_superficie = ${f(b.temp)} °C`,explanation:'Esta condición fija la temperatura de la frontera. El solver calcula el intercambio necesario. El flujo depende de la solución y no se obtiene sólo de Tb.'};}
 if(b.type==='N'){if(!finite(b.flux))throw Error('Flujo finito requerido.');add('q″impuesto','Flujo normal exterior',b.flux,'W/m²');add('k','Conductividad',k,'W/(m·K)');add('∇T','Gradiente de temperatura',null,'K/m');add('n','Normal unitaria exterior','unitaria','—');return {type:'N',rows,flux:b.flux,formula:'q″salida = −k ∇T · n = q″impuesto',substitution:`q″salida = ${f(b.flux)} W/m²\n∂T/∂n = −${f(b.flux)} / ${f(k)} = ${f(-b.flux/k)} K/m`,explanation:b.flux>0?'El hormigón pierde calor por esta superficie.':b.flux<0?'El calor entra al hormigón por esta superficie.':'Condición adiabática: no existe transferencia de calor a través de esta frontera.'};}
 if(b.type!=='R'||!finite(b.temp)||!finite(b.h)||b.h<0||!finite(b.R)||b.R<0)throw Error('Robin requiere temperatura finita, h ≥ 0 y R ≥ 0.');
 const rc=d/(2*k),film=b.h===0?Infinity:1/b.h,R=rc+b.R+film,q=b.h===0?0:tc===null?null:(tc-b.temp)/R;
 add('h','Coeficiente de convección',b.h,'W/(m²·K)');add('T_ambiente','Aire',b.temp,'°C');add('T_s','Superficie del hormigón (no centro de celda)',null,'°C');add('T_celda','Centro del voxel; sólo si se habilita snapshot',tc,'°C');add('Δn','Tamaño normal del voxel',d,'m');add('k','Conductividad del hormigón',k,'W/(m·K)');add('Rprotección','Resistencia agregada aplicada por Python',b.R,'m²·K/W');add('Δn/(2k)','Resistencia de media celda',rc,'m²·K/W');add('1/h','Película convectiva',b.h===0?'∞':film,'m²·K/W');add('Rtotal','Suma de resistencias',b.h===0?'∞':R,'m²·K/W');
 return {type:'R',rows,flux:q,resistance:R,formula:(b.R>0?'q″salida = (T_celda − T_ambiente) / R″total\nR″total = Δn/(2k) + Rprotección + 1/h\nRprotección = e_moldaje/k_moldaje + e_aislación/k_aislación':'q″salida = h (T_s − T_ambiente)\nDiscretización Python: q″salida = (T_celda − T_ambiente) / [Δn/(2k) + 1/h]'),substitution:b.h===0?'h = 0 → R″película → ∞ → q″salida = 0 W/m²':`R″total = ${f(rc)} + ${f(b.R)} + ${f(film)} = ${f(R)} m²·K/W\n${b.R===0?`q″salida = ${f(b.h)} × (T_s − ${f(b.temp)})\n`:''}q″salida = (${f(tc)} − ${f(b.temp)}) / ${f(R)} W/m²`,explanation:b.h===0?'Sin intercambio convectivo: h = 0.':tc===null?'T_s es una incógnita del problema. No se sustituye por T_celda. Selecciona una celda y habilita su snapshot para evaluar la formulación discreta.':q>0?'La celda entrega calor al ambiente a través de las resistencias.':q<0?'El ambiente entrega calor a la celda a través de las resistencias.':'No hay flujo instantáneo: las temperaturas son iguales.'};
}
const api={describe,faceClass,compatible,layers,names};if(typeof module!=='undefined')module.exports=api;else root.ThermaBoundaryMath=api;
})(typeof window==='undefined'?globalThis:window);
