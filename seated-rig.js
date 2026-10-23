(function(root){'use strict';const lerp=(a,b,t)=>a+(b-a)*t,clamp=x=>Math.max(0,Math.min(1,x));
function create(images,make){const head=make(850,825),happy=make(850,825),face=make(850,825),mask=make(850,825);head.getContext('2d').drawImage(images.head,35,30,850,825,0,0,850,825);happy.getContext('2d').drawImage(images.head,885,30,850,825,0,0,850,825);const mc=mask.getContext('2d');for(const [x,y,rx,ry] of [[313,518,103,99],[575,512,101,96],[438,644,95,47]]){mc.save();mc.translate(x,y);mc.scale(rx,ry);const g=mc.createRadialGradient(0,0,.9,0,0,1);g.addColorStop(0,'#000');g.addColorStop(1,'#0000');mc.fillStyle=g;mc.fillRect(-1,-1,2,2);mc.restore()}const fc=face.getContext('2d');fc.drawImage(happy,0,0);fc.globalCompositeOperation='destination-in';fc.drawImage(mask,0,0);fc.globalCompositeOperation='source-over';
const parts={upper:{box:[270,170,330,498],a:[439,220],b:[400,566]},fore:{box:[720,250,455,407],a:[870,280],b:[1024,567]}};
function bone(c,part,A,B){const p=parts[part],sx=p.b[0]-p.a[0],sy=p.b[1]-p.a[1],dx=B.x-A.x,dy=B.y-A.y,s=Math.hypot(dx,dy)/Math.hypot(sx,sy);c.save();c.translate(A.x,A.y);c.rotate(Math.atan2(dy,dx)-Math.atan2(sy,sx));c.scale(s,s);c.drawImage(images.arm,...p.box,p.box[0]-p.a[0],p.box[1]-p.a[1],p.box[2],p.box[3]);c.restore()}
function draw(c,p={},checker=false){const tilt=clamp(p.tilt||0),smile=clamp(p.smile||0),wave=clamp(p.wave||0);c.clearRect(0,0,1672,941);if(checker){for(let y=0;y<941;y+=28)for(let x=0;x<1672;x+=28){c.fillStyle=((x/28+y/28)%2)?'#b8c0bb':'#e2e5e1';c.fillRect(x,y,28,28)}}else c.drawImage(images.bg,0,0,1672,941);
c.save();c.translate(1070,804);c.scale(1,.16);const shadow=c.createRadialGradient(0,0,30,0,0,235);shadow.addColorStop(0,'#163d3570');shadow.addColorStop(1,'#163d3500');c.fillStyle=shadow;c.fillRect(-235,-235,470,470);c.restore();
const shoulder={x:1020,y:550},upperAngle=lerp(2.18,2.82,wave),foreAngle=lerp(2.23,4.5,wave),elbow={x:shoulder.x+Math.cos(upperAngle)*95,y:shoulder.y+Math.sin(upperAngle)*95},wrist={x:elbow.x+Math.cos(foreAngle)*76,y:elbow.y+Math.sin(foreAngle)*76};
// Head and face are one transparent hierarchy, rotating about the neck.
c.save();c.translate(1075,511);c.rotate(-tilt*.13);c.scale(.43,.43);c.drawImage(head,-440,-760);if(smile>0){c.globalAlpha=clamp((smile-.08)/.22);c.drawImage(face,-440,-760)}c.restore();
bone(c,'upper',shoulder,elbow);
// Exclude the old hanging sleeve; keep torso and reconstructed knee intact.
c.save();c.translate(822,384);c.scale(.39,.39);c.beginPath();[[430,350],[550,250],[1254,250],[1254,1254],[0,1254],[0,800],[418,774],[470,650],[455,470],[430,400]].forEach(([x,y],i)=>i?c.lineTo(x,y):c.moveTo(x,y));c.closePath();c.clip();c.drawImage(images.body,0,0);c.restore();
bone(c,'fore',elbow,wrist);
// Palm turns edge-on while changing from a resting hand to the open palm.
const e=wave*wave*(3-2*wave),edge=.35+.65*Math.cos(wave*Math.PI)**2,blend=clamp((wave-.40)/.20),mix=blend*blend*(3-2*blend),flutterGate=clamp((wave-.75)/.25),flutter=Math.sin((p.clock||0)*5)*.055*flutterGate*flutterGate*(3-2*flutterGate),angle=Math.PI*e+lerp(.2,-.12,e)+flutter;
for(const [open,alpha] of [[false,1-mix],[true,mix]]){if(alpha<=0)continue;const box=open?[721,682,459,531]:[200,718,351,465],pivot=open?[941,1115]:[386,811];c.save();c.translate(wrist.x,wrist.y);c.rotate(angle-(open?Math.PI:0));c.scale(.19*edge,.19);c.globalAlpha=alpha;c.drawImage(images.arm,...box,box[0]-pivot[0],box[1]-pivot[1],box[2],box[3]);c.restore();}

return{shoulder,elbow,wrist};}
return{draw};}
async function load(){const entries={body:'body.png',head:'head-atlas.png',arm:'arm-atlas.png',bg:'seat-background.png'},images={};await Promise.all(Object.entries(entries).map(([k,n])=>new Promise((resolve,reject)=>{const i=new Image();i.onload=()=>{images[k]=i;resolve()};i.onerror=reject;i.src='assets/motion-lab/'+n})));return create(images,(w,h)=>{const c=document.createElement('canvas');c.width=w;c.height=h;return c})}
root.SeatedRig={create,load};})(typeof window!=='undefined'?window:globalThis);
