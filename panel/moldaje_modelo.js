(function(root){'use strict';
function extra(p,face,time_s=0){const m=p.formwork;return m&&m.faces[face]&&time_s<(m.remove_at_h??Infinity)*3600?m.thickness_m/m.conductivity_W_mK:0;}
const api={extra};if(typeof module!=='undefined')module.exports=api;else root.ThermaFormworkMath=api;
})(typeof window==='undefined'?globalThis:window);
