// Run against the local editor using Playwright on NODE_PATH. Personal records
// are read only; each browser context has disposable filter storage.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const path=require('node:path');
const base=process.env.GAME_LIST_TEST_URL||'http://127.0.0.1:8767/';
let stage='launch';
async function ready(p){await p.locator('#app').waitFor({state:'visible'});await p.locator('#games').waitFor();}
async function state(p){return p.evaluate(()=>({view:document.querySelector('#app').dataset.view,search:document.querySelector('#search').value,fields:Object.fromEntries(['platform','year','genre','sort','owned-filter'].map(id=>[id,document.getElementById(id).value])),interest:document.querySelector('[data-interest].active').dataset.interest,page:document.querySelector('.page-number').textContent,expanded:document.querySelector('#filter-options').classList.contains('expanded')}));}
async function select(p,id,value){await p.locator('#'+id).selectOption(value,{force:true});}
async function openGame(p,platform,title){
 const id=await p.evaluate(({platform,title})=>data.games.find(g=>g.platform===platform&&g.title===title)?.id,{platform,title});
 assert(id,'Test game missing');await p.locator('#reset').click();await p.locator('#search').fill(title);await p.locator('[data-detail="'+id+'"]').click();return id;
}
async function main(){
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try{
  const context=await browser.newContext({viewport:{width:1280,height:900}}),errors=[];let updates=0;
  context.on('page',p=>{p.on('pageerror',e=>errors.push(e.message));p.on('request',r=>{if(r.url().endsWith('/api/update'))updates++;});});
  const p=await context.newPage();await p.goto(base);await ready(p);
  const links=await p.evaluate(()=>fetch('/api/links').then(r=>r.json()));
  stage='PC all filters persist';
  await p.locator('#search').fill('クロノ');await select(p,'platform','family:SFC');await select(p,'year','1995');await select(p,'genre','RPG');await select(p,'sort','new');await select(p,'owned-filter','unknown');await p.locator('[data-interest="unknown"]').click();
  const chosen=await state(p);await p.reload();await ready(p);assert.deepEqual(await state(p),chosen);
  await p.locator('[data-view="owned"]').click();assert.equal((await state(p)).search,'クロノ');assert.deepEqual((await state(p)).fields,chosen.fields);
  const owned=await state(p);await p.reload();await ready(p);assert.deepEqual(await state(p),owned);
  stage='Clear and page restore';
  await p.locator('[data-view="all"]').click();await p.locator('#reset').click();assert.equal((await state(p)).fields.sort,'date');await p.locator('[data-page="next"]').last().click();
  const paged=await state(p),first=await p.locator('[data-detail]').first().getAttribute('data-detail');await p.reload();await ready(p);assert.deepEqual(await state(p),paged);assert.equal(await p.locator('[data-detail]').first().getAttribute('data-detail'),first);
  const other=await context.newPage();await other.goto(base);await ready(other);assert.deepEqual(await state(other),paged);await other.close();
  stage='Detail and cross-platform navigation';
  const id=await openGame(p,'SFC','ファイナルファンタジーIV');
  assert.equal(await p.locator('#detail').getByText('発売情報・別版の記録',{exact:true}).count(),0);assert.equal(await p.locator('#detail').getByText('以前の記録・分類の根拠',{exact:true}).count(),0);
  const remake=await p.evaluate(()=>data.games.find(g=>g.platform==='NDS'&&g.title==='ファイナルファンタジーIV').id);
  assert.match(await p.locator('[data-related="'+remake+'"]').innerText(),/リメイク/);
  await p.locator('#memo').fill('保存しないテスト');p.once('dialog',d=>d.dismiss());await p.locator('[data-related="'+remake+'"]').click();assert.equal(await p.locator('#memo').inputValue(),'保存しないテスト');
  p.once('dialog',d=>d.accept());await p.locator('[data-related="'+remake+'"]').click();assert.match(await p.locator('[data-related="'+id+'"]').innerText(),/原作/);await p.locator('[data-relation-back]').click();
  assert.equal(await p.locator('#search').inputValue(),'ファイナルファンタジーIV');
  await p.screenshot({path:path.join(process.env.TEMP||'/tmp','game-list-persist-pc.png')});await p.mouse.click(1,1);assert.equal(await p.locator('#detail').evaluate(e=>e.open),false);
  stage='Malformed and stale storage';
  await p.evaluate(()=>localStorage.setItem(FILTER_STORAGE,'{invalid'));await p.reload();await ready(p);assert.equal((await state(p)).search,'');
  await p.evaluate(()=>localStorage.setItem(FILTER_STORAGE,JSON.stringify({version:1,view:'missing',interest:'missing',page:999999,search:'<test>',fields:{platform:'missing',year:'0',sort:'missing',genre:'missing','owned-filter':'missing'}})));await p.reload();await ready(p);const stale=await state(p);assert.equal(stale.fields.platform,'');assert.equal(stale.fields.sort,'date');assert.equal(stale.view,'all');assert.equal(stale.page,'1 / 1');
  stage='Mobile readonly and independent filters';
  const mobile=await context.newPage();await mobile.setViewportSize({width:390,height:844});await mobile.goto(new URL(links.preview,base).href);await ready(mobile);assert.equal((await state(mobile)).search,'');
  await mobile.locator('#filter-toggle').click();await mobile.locator('#search').fill('ゼルダ');await select(mobile,'platform','maker:nintendo');await select(mobile,'year','2011');await select(mobile,'sort','title');
  const ms=await state(mobile);await mobile.reload();await ready(mobile);assert.deepEqual(await state(mobile),ms);
  await openGame(mobile,'N64','ゼルダの伝説 時のオカリナ');assert.equal(await mobile.locator('#memo').count(),0);
  const zelda=await mobile.evaluate(()=>data.games.find(g=>g.platform==='3DS'&&g.title==='ゼルダの伝説 時のオカリナ 3D').id);await mobile.locator('[data-related="'+zelda+'"]').click();await mobile.locator('[data-relation-back]').click();
  assert.equal(await mobile.locator('#detail').evaluate(e=>e.scrollWidth<=e.clientWidth+1),true);await mobile.screenshot({path:path.join(process.env.TEMP||'/tmp','game-list-persist-mobile.png')});
  assert.deepEqual(errors,[]);assert.equal(updates,0);
  stage='Browser storage disabled';
  const blocked=await browser.newContext();await blocked.addInitScript(()=>{Storage.prototype.getItem=()=>{throw new DOMException('Denied','SecurityError')};Storage.prototype.setItem=()=>{throw new DOMException('Denied','SecurityError')};});const noStorage=await blocked.newPage();await noStorage.goto(base);await ready(noStorage);await noStorage.locator('#search').fill('クロノ');assert(Number((await noStorage.locator('#result-count').textContent()).replaceAll(',',''))>0);
  console.log('PASS: filters/search/view/page, reload/new tab, mobile independence, clear, malformed/blocked storage, related navigation, hidden audit sections, memo protection. No personal edits.');
 }finally{await browser.close();}
}
main().catch(error=>{console.error('FAIL at '+stage+': '+error.name);process.exit(1);});
