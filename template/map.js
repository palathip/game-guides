/* Optional (only in guides with worldMap / unlocks / area / spoiler): in-page links open their target <details>; spoiler reveal */
(()=>{const op=h=>{let id;try{id=decodeURIComponent(h)}catch(e){return}const t=id&&document.getElementById(id);for(let e=t;e;e=e.parentElement)if(e.tagName==='DETAILS')e.open=true};
document.addEventListener('click',e=>{const a=e.target.closest&&e.target.closest('a[href^="#"]');if(a)op(a.getAttribute('href').slice(1))});
addEventListener('hashchange',()=>op(location.hash.slice(1)));if(location.hash)op(location.hash.slice(1));
document.querySelectorAll('.spb').forEach(b=>b.addEventListener('click',()=>{const d=b.closest('details'),c=d.querySelector('.spc');d.classList.add('rev');c.inert=false;c.tabIndex=-1;b.remove();c.focus({preventScroll:true})}));})();
