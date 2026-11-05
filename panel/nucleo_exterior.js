/* Dos centros de voxel fijos, seleccionados por geometría, no por temperatura. */
(function(root){'use strict';const D=typeof module!=='undefined'?require('./visordatos.js'):root.ThermaViewData,I=typeof module!=='undefined'?require('./inteligencia.js'):root.ThermaIntelligence;
function exteriorFaces(r,i){const p=D.ijk(i,r.n),faces=[];for(let a=0;a<3;a++)for(let s=0;s<2;s++){const q=p.slice();q[a]+=s?1:-1;const boundary=q[a]<0||q[a]>=r.n[a]||!D.active(r,D.index(...q,r.n));if(boundary&&!(a===2&&s===0&&p[2]===0))faces.push(2*a+s);}return faces;}
function validatePair(r,pair){if(!pair||![pair.core,pair.exterior].every(i=>Number.isInteger(i)&&i>=0&&i<r.fields[0].length)||!D.active(r,pair.core)||!D.active(r,pair.exterior)||pair.core===pair.exterior||!exteriorFaces(r,pair.exterior).includes(pair.face))throw Error('Se requieren dos voxeles distintos; el exterior debe tener una cara geométrica expuesta al aire.');return pair;}
function defaults(r){const core=I.suggestions(r)[0].index,cp=D.xyz(r,core),id=r.config.mask?.[core];let best=null,score=Infinity;
 for(const i of D.instanceIndices(r)){if(i===core)continue;const faces=exteriorFaces(r,i);if(!faces.length)continue;const face=faces.includes(1)?1:faces[0],p=D.xyz(r,i),same=!r.config.mask||r.config.mask[i]===id;
 const value=(same?0:1e9)+(face===1?0:1e7)+1e6*(p[2]-cp[2])**2+1e3*(p[1]-cp[1])**2+(p[0]-cp[0])**2;
 if(value<score){score=value;best={core,exterior:i,face};}}
 if(!best)throw Error('No se encontró un voxel exterior distinto del núcleo.');return validatePair(r,best);}
function history(r,pair){validatePair(r,pair);const core=[],exterior=[],delta=[];let peakIndex=-1;for(let j=0;j<r.fields.length;j++){const a=D.active(r,pair.core,j)?r.fields[j][pair.core]:null,b=D.active(r,pair.exterior,j)?r.fields[j][pair.exterior]:null,d=a===null||b===null?null:a-b;core.push(a);exterior.push(b);delta.push(d);if(d!==null&&(peakIndex<0||Math.abs(d)>Math.abs(delta[peakIndex])))peakIndex=j;}return {core,exterior,delta,peakIndex,peak:peakIndex<0?null:Math.abs(delta[peakIndex]),peakTime:peakIndex<0?null:r.frameTimes[peakIndex]};}
const api={exteriorFaces,validatePair,defaults,history};if(typeof module!=='undefined')module.exports=api;else root.ThermaCoreExterior=api;
})(typeof window==='undefined'?globalThis:window);
