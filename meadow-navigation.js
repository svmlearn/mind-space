(()=>{'use strict';
const obstacle=[[0,0],[39,0],[39,30],[34,41],[17,45],[0,49]];
function inside(p,poly){let yes=false;for(let i=0,j=poly.length-1;i<poly.length;j=i++){const a=poly[i],b=poly[j];if((a[1]>p.y)!==(b[1]>p.y)&&p.x<(b[0]-a[0])*(p.y-a[1])/(b[1]-a[1])+a[0])yes=!yes}return yes}
function free(p){return p.x>=4&&p.x<=96&&p.y>=12&&p.y<=95&&!inside(p,obstacle)}
function segment(a,b){const n=Math.ceil(Math.hypot(b.x-a.x,b.y-a.y)*2);for(let i=0;i<=n;i++){const t=n?i/n:0;if(!free({x:a.x+(b.x-a.x)*t,y:a.y+(b.y-a.y)*t}))return false}return true}
const nodes=[];for(let y=12;y<=94;y+=2)for(let x=4;x<=96;x+=2){const p={x,y};if(free(p))nodes.push(p)}
function nearest(p){if(free(p))return p;return nodes.reduce((a,b)=>Math.hypot(b.x-p.x,b.y-p.y)<Math.hypot(a.x-p.x,a.y-p.y)?b:a)}
function route(start,end){start=nearest(start);end=nearest(end);if(segment(start,end))return[end];const corners=[{x:41,y:12},{x:41,y:32},{x:36,y:43},{x:17,y:47},{x:4,y:51}],vertices=[start,...corners.filter(free),end],cost=vertices.map(()=>Infinity),prev=vertices.map(()=>-1),visited=new Set();cost[0]=0;for(let k=0;k<vertices.length;k++){let u=-1;for(let i=0;i<vertices.length;i++)if(!visited.has(i)&&(u<0||cost[i]<cost[u]))u=i;if(u<0||!Number.isFinite(cost[u]))break;visited.add(u);for(let v=0;v<vertices.length;v++){if(v===u||visited.has(v)||!segment(vertices[u],vertices[v]))continue;const d=cost[u]+Math.hypot(vertices[v].x-vertices[u].x,vertices[v].y-vertices[u].y);if(d<cost[v]){cost[v]=d;prev[v]=u}}}let i=vertices.length-1;if(!Number.isFinite(cost[i]))return[];const path=[];while(i>0){path.unshift(vertices[i]);i=prev[i]}return path}
window.MeadowNavigation={free,segment,nearest,route};
})();
