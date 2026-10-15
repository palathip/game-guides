/* game-guides runtime: walkthrough SVG layout, checklist+storage, counters, search, chapter picker */
(()=>{ // 1) Walkthrough: lay out boxes, wrap text by measuring real glyph widths -> never overflows
const NS='http://www.w3.org/2000/svg',C=5,W=170,GX=30,GY=34,LH=15,PAD=14,MAXW=W-2*PAD-6;
const seg=(()=>{try{const s=new Intl.Segmenter(GG.lang||'th',{granularity:'word'});return t=>[...s.segment(t)].map(x=>x.segment)}catch(e){return t=>t.split(/(\s+)/)}})();
const ms=document.createElementNS(NS,'svg');ms.setAttribute('class','fl');ms.setAttribute('aria-hidden','true');ms.style.cssText='position:absolute;left:-9999px;top:0;width:10px;height:10px;visibility:hidden';document.body.appendChild(ms);
const mt={};['nl','nd'].forEach(c=>{const t=document.createElementNS(NS,'text');t.setAttribute('class',c);ms.appendChild(t);mt[c]=t});
const wd=(c,s)=>{mt[c].textContent=s;return mt[c].getComputedTextLength()};
function wrap(text,c){if(!text)return[];const L=[];let cur='';
 for(const tk of seg(text)){const n=cur+tk;if(wd(c,n.trim())<=MAXW){cur=(cur||/\S/.test(tk))?n:'';continue}
  if(cur.trim())L.push(cur.trim());cur=/\S/.test(tk)?tk:'';
  while(cur&&wd(c,cur)>MAXW){let i=1;const a=[...cur];while(i<a.length&&wd(c,a.slice(0,i+1).join(''))<=MAXW)i++;while(i<a.length&&/[\u0E31\u0E34-\u0E3A\u0E47-\u0E4E\u0300-\u036f]/.test(a[i]))i++;L.push(a.slice(0,i).join(''));cur=a.slice(i).join('')}}
 if(cur.trim())L.push(cur.trim());return L}
const el=(n,a,p)=>{const e=document.createElementNS(NS,n);for(const k in a)e.setAttribute(k,a[k]);if(p)p.appendChild(e);return e};
function render(box){const F=JSON.parse(box.dataset.flow),N=F.nodes;
 const lab=N.map(n=>wrap(n.l,'nl')),sub=N.map(n=>wrap(n.s,'nd'));
 const hs=N.map((n,i)=>Math.max(54,21+(lab[i].length-1)*LH+(sub[i].length?19+(sub[i].length-1)*LH:0)+14));
 const rows=[];for(let r=0;r<N.length;r+=C)rows.push([...Array(Math.min(C,N.length-r)).keys()].map(j=>r+j));
 const pos=[],rowof=[];let y=14;rows.forEach((row,ri)=>{const rh=Math.max(...row.map(k=>hs[k]));row.forEach((k,j)=>{const c=ri%2?C-1-j:j;pos[k]=[14+c*(W+GX),y];rowof[k]=ri});y+=rh+GY});
 const TW=14+C*(W+GX),TH=y-GY+16;const sv=el('svg',{class:'fl',viewBox:`0 0 ${TW} ${TH}`,width:TW,role:'img','aria-label':F.label});
 for(let k=0;k<N.length-1;k++){const[x1,y1]=pos[k],[x2,y2]=pos[k+1];let d;if(rowof[k]===rowof[k+1]){const ym=y1+27;d=`M${x2>x1?x1+W:x1} ${ym}H${x2>x1?x2:x2+W}`}else d=`M${x1+W/2} ${y1+hs[k]}V${y2}`;el('path',{d,class:'ed'+(N[k+1].b?' bk':''),'marker-end':'url(#ah)'},sv)}
 N.forEach((n,i)=>{const[x,y]=pos[i],h=hs[i],g=el('g',{'data-n':1},sv);el('title',{},g).textContent=n.l+(n.s?' · '+n.s:'');
  const r={class:'nb',x,y,width:W,height:h,rx:8,stroke:n.c,'stroke-width':n.k==='boss'?2:1.3};if(n.b)r['stroke-dasharray']='4 3';el('rect',r,g);
  el('rect',{x,y,width:6,height:h,rx:3,fill:n.c},g);const cx=x+W/2+3;let ty=y+21;
  const put=(L,c)=>{if(!L.length)return;const t=el('text',{x:cx,y:ty,class:c},g);L.forEach((s,j)=>{const sp=el('tspan',{x:cx,dy:j?LH:0},t);sp.textContent=s});ty+=(L.length-1)*LH};
  put(lab[i],'nl');ty+=LH+4;put(sub[i],'nd')});
 box.replaceChildren(sv)}
const all=()=>{document.querySelectorAll('.flow[data-flow]').forEach(render);mt.nl.textContent=mt.nd.textContent=''};all();
if(document.fonts&&document.fonts.ready)document.fonts.ready.then(all);})();

const K=GG.key;const LS={g(k){try{return localStorage.getItem(k)}catch(e){return null}},s(k,v){try{localStorage.setItem(k,v)}catch(e){}}};document.querySelectorAll('input[data-k]').forEach(c=>{c.checked=LS.g(K+c.dataset.k)==='1';c.onchange=()=>{LS.s(K+c.dataset.k,c.checked?'1':'0');pg()}});
function pg(){const a=[...document.querySelectorAll('input[data-k]')];document.getElementById('prog').textContent=GG.ui.collected+' '+a.filter(x=>x.checked).length+'/'+a.length}pg();
document.getElementById('q').oninput=e=>{const v=e.target.value.toLowerCase().trim();document.querySelectorAll('main details').forEach(d=>{let any=false;d.querySelectorAll('.ck li,tr').forEach(li=>{const m=!v||li.textContent.toLowerCase().includes(v);li.classList.toggle('hide',!m&&li.tagName!=='TR'||(!m&&li.querySelector('td')));if(m)any=true});const show=!v||any||d.textContent.toLowerCase().includes(v);d.classList.toggle('hide',!show);if(v&&show)d.open=true})};
(()=>{const q=document.getElementById('q'),hdr=document.querySelector('header'),bar=document.querySelector('#pbar i'),em=document.getElementById('empty');
const setH=()=>document.documentElement.style.setProperty('--hh',hdr.offsetHeight+8+'px');setH();addEventListener('resize',setH);
const secs=[...document.querySelectorAll('main details')];const open0=new Map(secs.map(d=>[d,d.open]));
secs.forEach(d=>{const c=d.querySelector('.cnt');const b=[...d.querySelectorAll('input[data-k]')];if(!c||!b.length)return;const u=()=>{const n=b.filter(x=>x.checked).length;c.textContent=n+'/'+b.length+' '+GG.ui.unit;c.classList.toggle('done',n===b.length)};b.forEach(x=>x.addEventListener('change',u));u()});
const all=[...document.querySelectorAll('input[data-k]')];const up=()=>{bar.style.width=(all.filter(x=>x.checked).length/all.length*100)+'%'};all.forEach(x=>x.addEventListener('change',up));up();
const run=q.oninput;let t;q.oninput=e=>{clearTimeout(t);t=setTimeout(()=>{run(e);const v=q.value.trim();if(!v)secs.forEach(d=>{d.open=open0.get(d)});em.style.display=v&&secs.every(d=>d.classList.contains('hide'))?'block':'none'},120)};
q.addEventListener('keydown',e=>{if(e.key==='Escape'){q.value='';q.oninput({target:q})}});})();
(()=>{const b=document.getElementById('pkb'),p=document.getElementById('pk'),bg=document.getElementById('pkbg'),cur=document.getElementById('pkc'),x=p.querySelector('.pkx');
const links=[...p.querySelectorAll('a[data-s]')];
const open=()=>{p.hidden=false;bg.hidden=false;b.setAttribute('aria-expanded','true');(p.querySelector('a[aria-current=true]')||links[0]).focus({preventScroll:true})};
const close=(f)=>{p.hidden=true;bg.hidden=true;b.setAttribute('aria-expanded','false');if(f)b.focus({preventScroll:true})};
b.onclick=()=>p.hidden?open():close(true);x.onclick=()=>close(true);bg.onclick=()=>close(true);
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!p.hidden){close(true)}});
document.addEventListener('pointerdown',e=>{if(!p.hidden&&!p.contains(e.target)&&!b.contains(e.target))close(false)});
links.forEach(a=>a.addEventListener('click',e=>{const t=document.getElementById(a.dataset.s);if(t&&t.tagName==='DETAILS')t.open=true;close(false)}));
p.addEventListener('keydown',e=>{if(!/^Arrow/.test(e.key))return;const i=links.indexOf(document.activeElement);if(i<0)return;e.preventDefault();const d={ArrowRight:1,ArrowDown:1,ArrowLeft:-1,ArrowUp:-1}[e.key];links[(i+d+links.length)%links.length].focus()});
const short={};links.forEach(a=>short[a.dataset.s]=a.querySelector('b')?a.querySelector('b').textContent:'');
const targets=links.map(a=>document.getElementById(a.dataset.s)).filter(Boolean);
const mark=id=>{links.forEach(a=>a.setAttribute('aria-current',a.dataset.s===id?'true':'false'));cur.textContent=id&&id!=='intro'?'· '+short[id]:''};
let tk=0;const upd=()=>{tk=0;const y=document.querySelector('header').getBoundingClientRect().bottom+12;let id='intro',best=-1e9;for(const t of targets){const tp=t.getBoundingClientRect().top;if(tp<=y&&tp>best&&!t.classList.contains('hide')){best=tp;id=t.id}}mark(id)};
addEventListener('scroll',()=>{if(!tk)tk=requestAnimationFrame(upd)},{passive:true});upd();})();
/* Optional checklist sync via a secret GitHub Gist (checklist.json, one key per game).
   Merge rule: on load, checked = union(local, Gist); writes replace only this game's key.
   Token only ever travels in the Authorization header to api.github.com. */
(()=>{const CF='gg-sync',API='https://api.github.com/gists/',FN='checklist.json',SLUG=String(GG.key).replace(/[^\w-]+$/,'')||'guide';
const $=i=>document.getElementById(i),btn=$('syb'),st=$('sys'),dlg=$('syd');if(!btn||!dlg)return;
const boxes=[...document.querySelectorAll('input[data-k]')],keys=new Set(boxes.map(c=>c.dataset.k));
const ID_RE=/^[0-9a-f]{20,40}$/i,TK_RE=/^[A-Za-z0-9_]{20,255}$/;
const cfg=()=>{try{const c=JSON.parse(localStorage.getItem(CF)||'null');return c&&ID_RE.test(c.id)&&TK_RE.test(c.tok)?c:null}catch(e){return null}};
const say=(t,err)=>{st.textContent=t;st.classList.toggle('err',!!err)};
const hd=c=>({Authorization:'Bearer '+c.tok,Accept:'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'});
async function read(c){const r=await fetch(API+c.id,{headers:hd(c),cache:'no-store'});if(!r.ok)throw r.status;const j=await r.json(),f=j.files&&j.files[FN];
 if(!f||f.truncated)throw 'nofile';let o;try{o=JSON.parse(f.content||'{}')}catch(e){throw 'json'}return o&&typeof o==='object'&&!Array.isArray(o)?o:{}}
const checked=()=>boxes.filter(b=>b.checked).map(b=>b.dataset.k).sort();
const msg=e=>!navigator.onLine||e instanceof TypeError?['ออฟไลน์ ใช้ข้อมูลในเครื่อง',0]:e===401||e===403?['ซิงก์ไม่สำเร็จ: token ไม่ถูกต้องหรือหมดอายุ',1]:e===404?['ซิงก์ไม่สำเร็จ: ไม่พบ Gist',1]:e==='nofile'?['ซิงก์ไม่สำเร็จ: ไม่พบไฟล์ checklist.json ใน Gist',1]:['ซิงก์ไม่สำเร็จ ใช้ข้อมูลในเครื่อง',1];
let busy=false;
async function push(){const c=cfg();if(!c)return;try{const o=await read(c);o[SLUG]=checked();
 const r=await fetch(API+c.id,{method:'PATCH',headers:Object.assign({'Content-Type':'application/json'},hd(c)),body:JSON.stringify({files:{[FN]:{content:JSON.stringify(o,null,1)}}})});
 if(!r.ok)throw r.status;say('ซิงก์แล้ว')}catch(e){const[m,x]=msg(e);say(m,x)}}
let t;const later=()=>{if(!cfg()||busy)return;clearTimeout(t);say('กำลังซิงก์…');t=setTimeout(push,1500)};
boxes.forEach(b=>b.addEventListener('change',later));
async function pull(){const c=cfg();if(!c){say('');return}say('กำลังซิงก์…');try{const o=await read(c),rem=Array.isArray(o[SLUG])?o[SLUG].filter(k=>typeof k==='string'&&keys.has(k)):[];
 busy=true;boxes.forEach(b=>{if(!b.checked&&rem.includes(b.dataset.k)){b.checked=true;b.dispatchEvent(new Event('change'))}});busy=false;
 const now=checked();if(now.length!==rem.length||now.some(k=>!rem.includes(k)))await push();else say('ซิงก์แล้ว')}catch(e){busy=false;const[m,x]=msg(e);say(m,x)}}
const idI=$('syi'),tkI=$('syk'),er=$('sye');
btn.onclick=()=>{const c=cfg();idI.value=c?c.id:'';tkI.value='';tkI.placeholder=c?'บันทึกไว้แล้ว (ใส่ใหม่เพื่อเปลี่ยน)':'';er.textContent='';dlg.showModal();idI.focus()};
dlg.addEventListener('close',()=>{tkI.value='';btn.focus({preventScroll:true})});
$('syf').addEventListener('submit',e=>{if(e.submitter&&e.submitter.value!=='save')return;const id=idI.value.trim(),old=cfg(),tok=tkI.value.trim()||(old&&old.id&&old.tok)||'';
 if(!ID_RE.test(id)){e.preventDefault();er.textContent='Gist ID ต้องเป็นตัวอักษร 0-9 a-f ยาว 20–40 ตัว';idI.focus();return}
 if(!TK_RE.test(tok)){e.preventDefault();er.textContent='รูปแบบ token ไม่ถูกต้อง';tkI.focus();return}
 try{localStorage.setItem(CF,JSON.stringify({id,tok}))}catch(x){e.preventDefault();er.textContent='บันทึกในเบราว์เซอร์นี้ไม่ได้';return}pull()});
$('syx').onclick=()=>{try{localStorage.removeItem(CF)}catch(e){}clearTimeout(t);say('');dlg.close()};
pull()})();
