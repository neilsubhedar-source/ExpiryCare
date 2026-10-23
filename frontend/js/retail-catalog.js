/* Customer-facing view of the shared retail prototype store. */
(function(){'use strict';
const KEY='expirycareRetailV1', DAY=86400000;
const $=id=>document.getElementById(id);
function read(){try{const d=JSON.parse(localStorage.getItem(KEY)||'null');if(d&&Array.isArray(d.products)&&Array.isArray(d.batches)&&Array.isArray(d.branches))return d;}catch(e){}return null;}
function days(b){if(!b.expiryDate||b.verification!=='Verified')return null;const expiry=Date.parse(b.expiryDate+'T00:00:00Z'),today=Date.parse(new Date().toISOString().slice(0,10)+'T00:00:00Z');if(!Number.isFinite(expiry))return null;return Math.ceil((expiry-today)/DAY);}
function eligible(b){const d=days(b);return d!==null&&d>=0&&Number(b.available)>=0&&Number(b.reserved||0)>=0&&Number(b.available)-Number(b.reserved||0)>0;}
function imageFor(p){
const n=String(p.name||'').toLowerCase(),cat=String(p.category||'').toLowerCase();
if(/milk|dairy|yogurt|curd|cheese|butter/.test(n))return 'https://images.unsplash.com/photo-1563636619-e9143da7973b?auto=format&fit=crop&w=120&h=120&q=80';
if(/cream|cosmetic|makeup|lipstick|serum|sunscreen|shampoo|lotion|skincare|moistur/.test(n)||/personal.?care|cosmetic|beauty/.test(cat))return 'https://images.unsplash.com/photo-1608248543803-ba4f8c70ae0b?auto=format&fit=crop&w=120&h=120&q=80';
if(/tablet|medicine|medicin|paracetamol|syrup|capsule|vitamin|antacid|ointment/.test(n)||/medicine|pharma|health/.test(cat))return 'https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?auto=format&fit=crop&w=120&h=120&q=80';
return 'https://images.unsplash.com/photo-1542838132-92c53300491e?auto=format&fit=crop&w=120&h=120&q=80';
}
function esc(v){return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function render(){const db=read(),body=$('catalog-results');if(!db){body.innerHTML='<tr><td colspan="5" class="catalog-empty">Retail demo data is not available in this browser yet. Open Retail Manager and choose “Load / reset fictional demo” to initialise it.</td></tr>';$('catalog-message').textContent='No inventory data found; availability has not been invented.';$('catalog-branch').innerHTML='<option value="all">All branches</option>';return;}
const branchSelect=$('catalog-branch'),selected=branchSelect.value||'all';branchSelect.innerHTML='<option value="all">All branches</option>'+db.branches.filter(b=>b.active!==false).map(b=>`<option value="${esc(b.id)}">${esc(b.name)}</option>`).join('');branchSelect.value=[...branchSelect.options].some(o=>o.value===selected)?selected:'all';
const q=$('catalog-query').value.trim().toLowerCase(),branchId=branchSelect.value,status=$('catalog-status').value;const rows=[];
db.products.filter(p=>String(p.name||'').toLowerCase().includes(q)).forEach(p=>{db.branches.filter(br=>br.active!==false&&(branchId==='all'||br.id===branchId)).forEach(br=>{const bs=db.batches.filter(b=>b.productId===p.id&&b.branchId===br.id),units=bs.filter(eligible).reduce((n,b)=>n+Math.max(0,Number(b.available)-Number(b.reserved||0)),0),state=units===0?'Out of stock':units<=5?'Low stock':'In stock';if(status!=='all'&&state!==status)return;rows.push({p,br,units,state});});});
body.innerHTML=rows.length?rows.map(r=>`<tr><td><div class="catalog-product-cell"><img src="${imageFor(r.p)}" alt="" loading="lazy" onerror="this.hidden=true"><div><strong>${esc(r.p.name)}</strong><br><span class="catalog-note">${esc(r.p.category||'Uncategorised')}</span></div></div></td><td>${esc(r.br.name)}</td><td>${r.units}</td><td>${Number.isFinite(Number(r.p.price))?'₹'+esc(Number(r.p.price).toFixed(2)):'Not listed'}</td><td><span class="catalog-status">${r.state}</span></td></tr>`).join(''):'<tr><td colspan="5" class="catalog-empty">No matching products or branches. Try another search or filter.</td></tr>';$('catalog-message').textContent=`${rows.length} result(s) · Fictional demo inventory · Updated ${new Date().toLocaleString()}`;
}
document.addEventListener('DOMContentLoaded',()=>{['catalog-query','catalog-branch','catalog-status'].forEach(id=>$(id).addEventListener(id==='catalog-query'?'input':'change',render));render();});
})();
