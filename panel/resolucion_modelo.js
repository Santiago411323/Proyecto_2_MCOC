/* Estimaciones de recursos; no resuelve calor ni predice tiempos de ejecución. */
(function(root){'use strict';
function estimate(L,steps,volume,p={}){
 const k=p.k??2,rho=p.rho??2400,cp=p.cp??900,frames=p.frames??65,days=p.days??14,dt=p.dt??900;
 if([...L,...steps,volume,k,rho,cp,frames,days,dt].some(v=>!Number.isFinite(v)||v<=0))throw Error('Dimensiones, pasos y propiedades positivas.');
 const shape=L.map((v,a)=>Math.max(2,Math.ceil(v/steps[a]-1e-10))),spacing=L.map((v,a)=>v/shape[a]),N=shape.reduce((a,b)=>a*b,1),safe=1/(4*k/(rho*cp)*spacing.reduce((s,d)=>s+1/d**2,0)),memory=N*(250+frames*13),cost=N*Math.ceil(days*86400/Math.min(dt,safe)),reasons=[];
 if(N>80000)reasons.push('Máximo 80.000 celdas.');if(Math.max(...shape)>160)reasons.push('Máximo 160 celdas por eje.');if(memory>512*1024**2)reasons.push('Memoria estimada >512 MiB.');if(cost>3e8)reasons.push('Costo conservador >300 millones de celda-pasos.');
 return {shape,spacing,total_cells:N,occupied_cells_estimate:Math.min(N,Math.round(volume/spacing.reduce((a,b)=>a*b,1))),memory_bytes_estimate:memory,dt_sufficient_s:safe,relative_cost:cost/(36*36*12*Math.ceil(days*86400/900)),allowed:!reasons.length,reasons,isotropic:Math.max(...spacing)-Math.min(...spacing)<1e-10};
}
if(typeof module!=='undefined')module.exports={estimate};else root.ThermaResolution={estimate};
})(typeof window==='undefined'?globalThis:window);
