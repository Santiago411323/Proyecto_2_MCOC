(function(root){'use strict';
function extra(p,face){const m=p.formwork;return m&&m.faces[face]?m.thickness_m/m.conductivity_W_mK:0;}
const api={extra};if(typeof module!=='undefined')module.exports=api;else root.ThermaFormworkMath=api;
})(typeof window==='undefined'?globalThis:window);
