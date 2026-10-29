/* Solver cartesiano explícito, propiedades escalares constantes, unidades SI.
   Motor independiente del DOM: se ejecuta en Worker y se verifica contra Python. */
(function(root){
'use strict';
const DAY=86400;
function pulseIntegral(t,P){const u=Math.max(0,Math.min(t,P));return u/2-P*Math.sin(2*Math.PI*u/P)/(4*Math.PI);}
function shape(t,p){return p.source==='none'?0:p.source==='constant'?1:(t>=0&&t<=p.period?0.5*(1-Math.cos(2*Math.PI*t/p.period)):0);}
function meanSource(a,b,p){return p.source==='none'?0:p.source==='constant'?1:(pulseIntegral(b,p.period)-pulseIntegral(a,p.period))/(b-a);}
function make(p){
 const dim=p.dim, n=p.n.slice(0,dim), L=p.L.slice(0,dim);
 if(![1,2,3].includes(dim)||n.some(v=>!Number.isInteger(v)||v<2||v>160)||L.some(v=>!Number.isFinite(v)||v<=0))throw Error('Revisa las dimensiones y el número de celdas (2–160 por eje).');
 if(![p.k,p.rho,p.cp,p.days].every(v=>Number.isFinite(v)&&v>0))throw Error('Material y duración deben ser positivos.');
 if(p.source==='pulse'&&(!Number.isFinite(p.period)||p.period<=0))throw Error('La duración del pulso debe ser positiva.');
 if(![p.initial,p.amplitude,p.target,p.qmax].every(Number.isFinite))throw Error('Temperaturas y fuente deben ser números finitos.');
 const nx=n[0],ny=n[1]||1,nz=n[2]||1,N=nx*ny*nz, dx=L.map((v,a)=>v/n[a]),alpha=p.k/(p.rho*p.cp), vol=dx.reduce((a,b)=>a*b,1), C=p.rho*p.cp*vol;
 if(N>50000)throw Error('La malla supera 50.000 celdas. Reduce las celdas por eje.');
 const strides=[1,nx,nx*ny],rates=dx.map(d=>alpha/(d*d)), sum=new Float64Array(N),gB=new Float64Array(N),bB=new Float64Array(N),init=new Float64Array(N);
 for(let a=0;a<dim;a++)for(let s=0;s<2;s++){
  const b=p.faces[2*a+s];if(!b||!['D','N','R'].includes(b.type)||![b.temp,b.flux,b.h,b.R].every(Number.isFinite)||b.h<0||b.R<0)throw Error('Revisa las condiciones de borde: h y R deben ser ≥0.');
 }
 for(let z=0;z<nz;z++)for(let y=0;y<ny;y++)for(let x=0;x<nx;x++){
  const i=x+nx*(y+ny*z),coords=[x,y,z];let phi=1;
  for(let a=0;a<dim;a++){
   phi*=Math.sin(Math.PI*(coords[a]+.5)/n[a]);
   sum[i]+=rates[a]*((coords[a]>0?1:0)+(coords[a]<n[a]-1?1:0));
   for(let s=0;s<2;s++)if(coords[a]===(s?n[a]-1:0)){
    const b=p.faces[2*a+s];let rate=0;
    if(b.type==='N')bB[i]-=b.flux/(p.rho*p.cp*dx[a]);
    else {
     rate=b.type==='D'?2*rates[a]:(b.h===0?0:1/(dx[a]/(2*p.k)+b.R+1/b.h)/(p.rho*p.cp*dx[a]));
     gB[i]+=rate;bB[i]+=rate*b.temp;sum[i]+=rate;
    }
   }
  }
  init[i]=p.initial+(p.initialType==='sine'?p.amplitude*phi:0);
 }
 let dtMax=Infinity;for(const s of sum)if(s>0)dtMax=Math.min(dtMax,1/s);
 if(!Number.isFinite(p.factor)||p.factor<=0||p.factor>1)throw Error('El factor de estabilidad debe estar entre 0 y 1.');
 let dt=p.dtMode==='manual'?p.dt:p.factor*dtMax;
 if(!Number.isFinite(dt)||dt<=0||dt>dtMax*(1+1e-12))throw Error(`Δt inestable. Para esta malla debe ser ≤ ${dtMax.toFixed(4)} s.`);
 if(p.dtMode!=='manual'&&p.source==='pulse')dt=Math.min(dt,p.period/200);
 const duration=p.days*DAY, frames=Math.min(100,Math.max(20,p.frames||65));
 if(p.source==='pulse'&&duration<p.period)throw Error('La simulación debe cubrir el pulso completo.');
 const steps=Math.ceil(duration/dt)+2;
 if(steps*N*(p.calibrate?3:1)>3e8)throw Error('Este cálculo es demasiado grande para el navegador. Reduce la malla o la duración; usa Python para mallas grandes.');
 if(steps>200000)throw Error('Demasiados pasos. Aumenta Δt o reduce la duración.');
 const mids=n.map(v=>v%2?[Math.floor(v/2)]:[v/2-1,v/2]);const mid=[];
 for(const z of mids[2]||[0])for(const y of mids[1]||[0])for(const x of mids[0])mid.push(x+nx*(y+ny*z));
 const center=T=>mid.reduce((s,i)=>s+T[i],0)/mid.length;
 function step(T,out,dt,unit,q){
  for(let i=0;i<N;i++)out[i]=T[i]+dt*(-gB[i]*T[i]+(unit?0:bB[i])+q/(p.rho*p.cp));
  for(let z=0;z<nz;z++)for(let y=0;y<ny;y++)for(let x=0;x<nx;x++){
   const i=x+nx*(y+ny*z),coords=[x,y,z];
   for(let a=0;a<dim;a++)if(coords[a]<n[a]-1){const j=i+strides[a],f=dt*rates[a]*(T[j]-T[i]);out[i]+=f;out[j]-=f;}
  }
 }
 return {p,n,L,nx,ny,nz,N,dx,alpha,vol,C,dt,dtMax,duration,frames,steps,init,gB,bB,center,step};
}
function solve(p,progress=()=>{}){
 const m=make(p), {N,dt,duration}=m;let qmax=p.source==='none'?0:p.qmax;
 const nextTime=t=>{let end=Math.min(t+dt,duration);if(p.source==='pulse'&&t<p.period&&end>p.period)end=p.period;return end;};
 if(p.calibrate){
  if(p.source==='none')throw Error('Para calibrar Qmax selecciona una fuente constante o un pulso.');
  let B=m.init.slice(),U=new Float64Array(N),b=new Float64Array(N),u=new Float64Array(N),t=0,step=0,limit=Infinity;
  if(m.center(B)>=p.target)throw Error('El centro ya alcanza el objetivo en la condición inicial.');
  while(t<duration){let end=nextTime(t),h=end-t,q=meanSource(t,end,p);m.step(B,b,h,false,0);m.step(U,u,h,true,q);[B,b]=[b,B];[U,u]=[u,U];t=end;step++;
   const base=m.center(B),gain=m.center(U);
   if(base>=p.target)throw Error('Los bordes o el estado inicial ya alcanzan el objetivo sin fuente positiva.');
   if(gain>1e-15)limit=Math.min(limit,(p.target-base)/gain);
   if(step%250===0)progress(.45*t/duration);
  }
  if(!Number.isFinite(limit)||limit<=0)throw Error('No hay una calibración positiva para estos datos.');qmax=limit;
 }
 let T=m.init.slice(),out=new Float64Array(N),t=0,step=0,initialEnergy=0,net=0,residual=0,maxCenter=-Infinity,peakTime=0,maxField=-Infinity;
 const history=[],fields=[],frameTimes=[],targets=Array.from({length:m.frames},(_,i)=>duration*i/(m.frames-1));let frame=0;
 for(const v of T)initialEnergy+=v*m.C;
 function stats(time){let min=Infinity,max=-Infinity,E=0;for(const v of T){min=Math.min(min,v);max=Math.max(max,v);E+=v*m.C;}const center=m.center(T);
  if(center>maxCenter+1e-8){maxCenter=center;peakTime=time;}maxField=Math.max(maxField,max);
  const err=E-initialEnergy-net;residual=Math.max(residual,Math.abs(err));
  history.push({t:time,center,min,max,energy:E-initialEnergy,net,residual:err,q:qmax*shape(time,p)});
 }
 stats(0);fields.push(new Float32Array(T));frameTimes.push(0);frame=1;
 while(t<duration){const end=nextTime(t),h=end-t,q=qmax*meanSource(t,end,p);let P=q*m.vol*N;
  for(let i=0;i<N;i++)P+=m.C*(m.bB[i]-m.gB[i]*T[i]);net+=h*P;
  m.step(T,out,h,false,q);
  while(frame<targets.length&&targets[frame]<=end+1e-8){const w=Math.min(1,(targets[frame]-t)/h),A=new Float32Array(N);for(let i=0;i<N;i++)A[i]=T[i]*(1-w)+out[i]*w;fields.push(A);frameTimes.push(targets[frame]);frame++;}
  [T,out]=[out,T];t=end;step++;stats(t);if(step%250===0)progress((p.calibrate?.45:0)+(p.calibrate?.55:1)*t/duration);
 }
 let exactError=null;
 const exactOK=p.initialType==='sine'&&p.source==='none'&&p.faces.slice(0,2*p.dim).every(b=>b.type==='D'&&Math.abs(b.temp-p.initial)<1e-12);
 if(exactOK){exactError=0;let lambda=m.L.reduce((s,L)=>s+(Math.PI/L)**2,0);for(let z=0;z<m.nz;z++)for(let y=0;y<m.ny;y++)for(let x=0;x<m.nx;x++){
  let phi=1;const co=[x,y,z];for(let a=0;a<p.dim;a++)phi*=Math.sin(Math.PI*(co[a]+.5)/m.n[a]);
  exactError=Math.max(exactError,Math.abs(T[x+m.nx*(y+m.ny*z)]-(p.initial+p.amplitude*phi*Math.exp(-m.alpha*lambda*duration))));
 }}
 for(const v of T)if(!Number.isFinite(v))throw Error('El cálculo dejó de ser finito. Revisa los parámetros.');
 return {config:p,n:m.n,L:m.L,dx:m.dx,alpha:m.alpha,dt,dtMax:m.dtMax,qmax,history,fields,frameTimes,maxCenter,peakTime,maxField,residual,exactError,steps:step,N,calibrationHorizon:duration};
}
const api={make,solve,pulseIntegral,shape};
if(typeof module!=='undefined'&&module.exports)module.exports=api;
if(typeof WorkerGlobalScope!=='undefined'&&root instanceof WorkerGlobalScope)root.onmessage=e=>{try{const result=solve(e.data,p=>root.postMessage({type:'progress',value:p}));root.postMessage({type:'result',result},result.fields.map(v=>v.buffer));}catch(err){root.postMessage({type:'error',message:err.message});}};
root.ThermalSolver=api;
})(typeof self!=='undefined'?self:globalThis);
