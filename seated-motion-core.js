(function(root){'use strict';
const W=1672,H=941;
function create(images,make){const rest=make(W,H),face=make(W,H),mask=make(W,H);rest.getContext('2d').drawImage(images.upright,0,0);const m=mask.getContext('2d');for(const [x,y,rx,ry] of [[1016,391,63,58],[1135,391,60,58],[1075,442,43,26]]){m.save();m.translate(x,y);m.scale(rx,ry);const g=m.createRadialGradient(0,0,.88,0,0,1);g.addColorStop(0,'#000');g.addColorStop(1,'#0000');m.fillStyle=g;m.fillRect(-1,-1,2,2);m.restore()}const f=face.getContext('2d');f.drawImage(images.smile,0,0);f.globalCompositeOperation='destination-in';f.drawImage(mask,0,0);f.globalCompositeOperation='source-over';
function render(c,h=0){c.clearRect(0,0,W,H);c.drawImage(rest,0,0);if(h>0){c.save();c.globalAlpha=Math.min(1,Math.max(0,h));c.drawImage(face,0,0);c.restore()}}
return{render,rest};}
root.SeatedMotion={create};})(typeof window!=='undefined'?window:globalThis);
