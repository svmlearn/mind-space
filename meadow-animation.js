(()=>{'use strict';
const canvas=document.querySelector('#walker-canvas'),ctx=canvas.getContext('2d'),atlas=new Image();
let ready=false,last=[0,0,false],amount=0,stamp=0,settle=0;
function paint(){if(!ready)return;const [direction,phase]=last;ctx.clearRect(0,0,400,520);ctx.save();if(direction%2===1){ctx.translate(400,0);ctx.scale(-1,1)}window.GaitMesh.renderActor(ctx,atlas,phase/(Math.PI*2)*1.28,{back:direction>=2,amount});ctx.restore();
// Scene light remains on the sunset side even when the character turns.
ctx.save();ctx.globalCompositeOperation='source-atop';const light=ctx.createLinearGradient(50,420,340,80);light.addColorStop(0,'rgba(73,104,64,0.11)');light.addColorStop(.5,'rgba(232,192,116,0.04)');light.addColorStop(1,'rgba(255,207,128,0.20)');ctx.fillStyle=light;ctx.fillRect(0,0,400,520);
// Let the lowest sole pixels meet the lawn rather than form a hard cutout.
ctx.globalCompositeOperation='destination-out';const edge=ctx.createLinearGradient(0,506,0,520);edge.addColorStop(0,'rgba(0,0,0,0)');edge.addColorStop(1,'rgba(0,0,0,0.65)');ctx.fillStyle=edge;ctx.fillRect(0,506,400,14);
ctx.globalCompositeOperation='destination-over';ctx.translate(205,504);ctx.scale(1,.18);const shadow=ctx.createRadialGradient(0,0,12,0,0,93);shadow.addColorStop(0,'rgba(25,43,27,0.52)');shadow.addColorStop(.5,'rgba(25,43,27,0.25)');shadow.addColorStop(1,'rgba(25,43,27,0)');ctx.fillStyle=shadow;ctx.fillRect(-100,-100,200,200);ctx.restore()}
function finish(t){settle=0;if(last[2])return;if(document.hidden||document.querySelector('#walk-view').hidden||document.querySelector('#viewer').open||document.querySelector('#tree-dialog').open){amount=0;paint();return}const dt=Math.min((t-stamp)/1000,.05);stamp=t;amount=Math.max(0,amount-dt/0.24);paint();if(amount>0)settle=requestAnimationFrame(finish)}
function draw(direction,phase,moving){const now=performance.now();cancelAnimationFrame(settle);settle=0;last=[direction,phase,moving];if(moving){const dt=stamp?Math.min((now-stamp)/1000,.05):0;amount=Math.min(1,amount+dt/.16);stamp=now;paint()}else{if(document.hidden||document.querySelector('#walk-view').hidden||document.querySelector('#viewer').open||document.querySelector('#tree-dialog').open||matchMedia('(prefers-reduced-motion: reduce)').matches){amount=0;stamp=0;paint();return}stamp=now;paint();if(amount>0)settle=requestAnimationFrame(finish)}}
atlas.onload=()=>{ready=true;paint()};atlas.onerror=()=>{document.querySelector('#meadow-hint').textContent='人物素材未能加载，请刷新后再试'};atlas.src='assets/meadow/rig-parts.webp';window.MeadowActor={draw};
})();
