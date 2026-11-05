/* Correspondencia numérica del visor. Sin ecuaciones térmicas ni dependencias GPU. */
(function(root){'use strict';
 const index=(x,y,z,n)=>x+n[0]*(y+n[1]*z);
 const ijk=(i,n)=>[i%n[0],Math.floor(i/n[0])%n[1],Math.floor(i/(n[0]*n[1]))];
 const active=(r,i,frame)=>!!(!r.config.mask||r.config.mask[i]>0)&&(frame===undefined||!r.activeFrames||r.activeFrames[frame][i]===1);
 const xyz=(r,i)=>ijk(i,r.n).map((v,a)=>(r.metadata?.geometry.origin_m?.[a]??r.config.origin?.[a]??0)+(v+.5)*r.dx[a]);
 function extrema(r,frame){let min=Infinity,max=-Infinity,hot=-1,count=0;const f=r.fields[frame];for(let i=0;i<f.length;i++)if(active(r,i,frame)&&Number.isFinite(f[i])){if(f[i]>max){max=f[i];hot=i;}min=Math.min(min,f[i]);count++;}return {min:count?min:null,max:count?max:null,hot,count};}
 function limits(r,mode,lo,hi){if(mode==='auto'){let a=Infinity,b=-Infinity;for(let j=0;j<r.fields.length;j++){const e=extrema(r,j);if(e.count){a=Math.min(a,e.min);b=Math.max(b,e.max);}}if(!Number.isFinite(a))return [20,80];return [a,b>a?b:a+1];}lo=Number(lo);hi=Number(hi);if(!Number.isFinite(lo)||!Number.isFinite(hi)||hi<=lo)throw Error('La escala requiere mínimo < máximo.');return [lo,hi];}
 const stops=[[.06,.22,.65],[0,.77,.91],[.98,.89,.24],[1,.44,.08],[.83,.08,.14]];
 function color(t,lo,hi){const u=Math.max(0,Math.min(1,(t-lo)/(hi-lo)))*4,a=Math.min(3,Math.floor(u)),f=u-a;return stops[a].map((c,k)=>c+(stops[a+1][k]-c)*f);}
 function clipped(p,cuts){return cuts.some((c,a)=>c.enabled&&p[a]>c.position+1e-8);}
 function visible(r,i,cuts,frame){return active(r,i,frame)&&!clipped(xyz(r,i),cuts);}
 function nearest(times,t){return times.reduce((b,v,i)=>Math.abs(v-t)<Math.abs(times[b]-t)?i:b,0);}
 function instanceIndices(r){return Array.from({length:r.fields[0].length},(_,i)=>i).filter(i=>active(r,i));}
 function thermalSpread(stats,times,frame,reference=20){
  const series=stats.map(e=>e.count&&Number.isFinite(e.max)&&Number.isFinite(e.min)?e.max-e.min:null);
  let peakIndex=-1;series.forEach((v,i)=>{if(v!==null&&(peakIndex<0||v>series[peakIndex]))peakIndex=i;});
  return {series,current:series[frame]??null,peak:peakIndex<0?null:series[peakIndex],peakIndex,peakTime:peakIndex<0?null:times[peakIndex],reference,exceeds:series[frame]===null?null:series[frame]>reference,official:'NOT EVALUATED'};
 }
 const api={index,ijk,active,xyz,extrema,limits,color,clipped,visible,nearest,instanceIndices,thermalSpread};
 if(typeof module!=='undefined')module.exports=api;else root.ThermaViewData=api;
})(typeof window==='undefined'?globalThis:window);
