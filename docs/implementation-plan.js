(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const cards = [...document.querySelectorAll('.day-card')];
  function filterDays() {
    const phase=$('phase-filter').value;
    const query=$('day-search').value.trim().toLocaleLowerCase('ko');
    let count=0;
    for(const card of cards) {
      card.hidden = (phase !== 'all' && card.dataset.phase !== phase) || !card.textContent.toLocaleLowerCase('ko').includes(query);
      if(!card.hidden) count++;
    }
    $('day-count').textContent=`${count}개 작업 · ${count} MD / 기본 40 MD`;
    $('no-days').hidden=count!==0;
  }
  function clearFilters() { $('phase-filter').value='all'; $('day-search').value=''; filterDays(); }
  $('phase-filter').addEventListener('change',filterDays);
  $('day-search').addEventListener('input',filterDays);
  $('reset-filters').addEventListener('click',clearFilters);
  function revealAnchor() {
    if(!/^#day-\d{2}$/.test(location.hash)) return;
    const target=document.getElementById(location.hash.slice(1));
    if(target && target.hidden) { clearFilters(); target.scrollIntoView({block:'start'}); }
  }
  window.addEventListener('hashchange',revealAnchor);
  document.querySelectorAll('a[href^="#day-"]').forEach(a=>a.addEventListener('click',()=>{
    const target=document.getElementById(a.hash.slice(1));
    if(target?.hidden) clearFilters();
  }));
  revealAnchor();
  let printSnapshot=null;
  window.addEventListener('beforeprint',()=>{
    if(printSnapshot) return;
    printSnapshot=cards.map(c=>c.hidden);
    cards.forEach(c=>c.hidden=false); $('no-days').hidden=true;
  });
  window.addEventListener('afterprint',()=>{
    if(!printSnapshot) return;
    cards.forEach((c,i)=>c.hidden=printSnapshot[i]);printSnapshot=null;
    filterDays();
  });
  $('print-plan').addEventListener('click',()=>window.print());
  if('IntersectionObserver' in window) {
    const observer=new IntersectionObserver(entries=>entries.forEach(entry=>{
      if(entry.isIntersecting) document.querySelectorAll('.toc a').forEach(a=>a.classList.toggle('current',a.hash===`#${entry.target.id}`));
    }),{rootMargin:'-10% 0px -70% 0px'});
    document.querySelectorAll('.doc-section').forEach(section=>observer.observe(section));
  }
})();
