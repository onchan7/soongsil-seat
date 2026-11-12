'use strict';
const $=id=>document.getElementById(id), FLOORS=['B1','1F','2F','3F','4F','5F','6F'];
let seats=[],floor='B1',selected='B1_001',onlyFree=false,query='',states={},events=[],connected=false,lastUpdate=null,pollTimer,requestGeneration=0;
function saved(key,fallback){try{return JSON.parse(localStorage.getItem(key))??fallback}catch{return fallback}}
function persist(k,v){try{localStorage.setItem(k,JSON.stringify(v))}catch{}}
let settings=saved('seat-settings-v1',{mode:window.SEAT_CONFIG.apiBase?'live':'demo',api:window.SEAT_CONFIG.apiBase||''});
let demo=saved('seat-demo-v1',{owners:{},events:[]});
const statusLabel={available:'이용 가능',occupied:'사용 중',unknown:'미연결'};
function toast(t){$('toast').textContent=t;$('toast').classList.add('visible');clearTimeout(toast.t);toast.t=setTimeout(()=>$('toast').classList.remove('visible'),3200)}
function currentStatus(s){if(settings.mode==='demo')return demo.owners[s.id]?'occupied':'available';return connected?(states[s.id]?.status||'unknown'):'unknown'}
function statusClass(s){return {available:'free',occupied:'busy',unknown:'unknown'}[currentStatus(s)]}
function floorSeats(){return seats.filter(s=>s.floor===floor)}
function time(t){return new Date(t*1000).toLocaleTimeString('ko-KR',{hour:'2-digit',minute:'2-digit'})}
function render(){
 const fs=floorSeats(),free=fs.filter(s=>currentStatus(s)==='available').length,busy=fs.filter(s=>currentStatus(s)==='occupied').length;
 $('floorTitle').textContent=`${floor} 좌석 안내`;$('floorKicker').textContent=`FLOOR ${floor}`;$('freeCount').textContent=free;$('busyCount').textContent=busy;$('totalCount').textContent=fs.length;
 const rate=free+busy?Math.round(busy/(free+busy)*100):0;$('rate').textContent=free+busy?`${rate}%`:'—';$('rateBar').style.width=rate+'%';
 $('floorNav').replaceChildren(...FLOORS.map(f=>{let b=document.createElement('button');b.className=f===floor?'selected':'';b.setAttribute('aria-pressed',f===floor);b.innerHTML=`<strong>${f}</strong><small>${seats.filter(s=>s.floor===f).length}석</small>`;b.onclick=()=>{floor=f;selected=seats.find(s=>s.floor===f).id;render()};return b}));
 $('connection').textContent=settings.mode==='demo'?'시연 모드':connected?'좌석 서버 연결됨':'서버 미연결';$('connection').className='pill '+(settings.mode==='demo'?'':connected?'live':'error');
 $('updated').textContent=settings.mode==='demo'?'시연 데이터 · 실제 이용 현황이 아닙니다':connected?`최근 동기화 ${new Date(lastUpdate).toLocaleTimeString('ko-KR')} · 리더 상태는 좌석별 확인`:'서버에 연결되지 않아 현재 상태를 확인할 수 없습니다';
 const map=$('map');map.innerHTML='<div class="room-outline"></div><div class="map-caption">LIBRARY SEATING PLAN</div><div class="hallway">중앙 통로</div><div class="lounge"><span>▱</span>휴게 공간</div><div class="entry">↓ 출입 동선</div>';
 // One fixed coordinate system for every floor preserves the original relative positions.
 const pos=s=>({x:8+(s.x+65)/105*65,y:65+(s.z+35)/70*300});
 if(floor==='B1'||floor==='2F')for(const [x,t] of [[14,'A · 열람석'],[30,'B · 열람석'],[61,'C · 열람석']]){const l=document.createElement('span');l.className='zone-label';l.style.left=x+'%';l.style.top='44px';l.textContent=t;map.append(l)}
 let matches=0;
 fs.forEach(s=>{const p=pos(s),b=document.createElement('button');const match=(!onlyFree||currentStatus(s)==='available')&&(!query||s.id.toLowerCase().includes(query.toLowerCase())||s.label.includes(query));if(match)matches++;b.className=`seat ${statusClass(s)} ${s.id===selected?'chosen':''} ${match?'':'dim'} ${s.kind==='demo'?'demo-seat':''}`;b.style.left=p.x+'%';b.style.top=p.y+'px';b.textContent=s.label;b.title=`${s.id} · ${statusLabel[currentStatus(s)]}`;b.setAttribute('aria-label',b.title);b.setAttribute('aria-pressed',s.id===selected);b.onclick=()=>{selected=s.id;render()};map.append(b)});
 $('resultCount').textContent=`${matches} / ${fs.length}석 표시`;$('showAll').classList.toggle('active',!onlyFree);$('showFree').classList.toggle('active',onlyFree);
 const s=seats.find(s=>s.id===selected)||fs[0],st=states[s.id];
 $('detail').innerHTML=`<div class="detail-main"><div class="seat-illustration ${statusClass(s)}">${s.label}</div><h3>${s.id==='DEMO_LOBBY'?'로비 시연석':s.floor+' · '+s.label}</h3><span class="status-text ${statusClass(s)}">${statusLabel[currentStatus(s)]}</span></div><div class="detail-meta"><span>좌석 위치</span><b>${s.floor} · ${s.kind==='demo'?'로비 시연석':'학습 좌석'}</b></div><div class="detail-meta"><span>RFID 리더</span><b>${settings.mode==='demo'?'시연':connected&&st?.online?'연결됨':'미연결'}</b></div><p class="detail-note">${settings.mode==='demo'?'아래 버튼으로 카드 A·B의 인식을 체험하세요. 실제 RFID 상태와 분리됩니다.':st?.last_state==='occupied'&&!st?.online?'연결이 끊겼습니다. 마지막 기록은 사용 중이며, 현재 상태는 확인할 수 없습니다.':'이용 시작과 종료는 의자에 설치된 RFID 리더에 카드를 대면 반영됩니다.'}</p>${settings.mode==='demo'?'<div class="demo-actions"><button id="tapA">카드 A 찍기</button><button id="tapB">카드 B 찍기</button></div>':''}`;
 if(settings.mode==='demo'){ $('tapA').onclick=()=>tapDemo(s.id,'A');$('tapB').onclick=()=>tapDemo(s.id,'B') }
 const ev=settings.mode==='demo'?demo.events:events;$('events').replaceChildren();
 if(!ev.length){let l=document.createElement('li');l.textContent='아직 인식 기록이 없어요.';$('events').append(l)}
 ev.slice(0,4).forEach(e=>{let l=document.createElement('li'),t=document.createElement('span'),tm=document.createElement('time');t.textContent=`${e.seat_id.replace('_',' · ')} ${e.action==='check_in'?'이용 시작':e.action==='check_out'?'이용 종료':'인식 거절'}`;tm.textContent=time(e.at);l.append(t,tm);$('events').append(l)});
}
function tapDemo(id,card){let owner=demo.owners[id],other=Object.keys(demo.owners).find(k=>demo.owners[k]===card&&k!==id),action;
 if(owner&&owner!==card){toast('다른 카드가 사용 중인 좌석이에요.');return}if(other){toast(`카드 ${card}는 ${other} 좌석을 사용 중이에요. 먼저 퇴실하세요.`);return}
 if(owner){delete demo.owners[id];action='check_out'}else{demo.owners[id]=card;action='check_in'}
 demo.events.unshift({seat_id:id,action,at:Date.now()/1000});demo.events=demo.events.slice(0,20);persist('seat-demo-v1',demo);render();toast(action==='check_in'?'시연: 이용을 시작했어요.':'시연: 이용을 종료했어요.')}
async function poll(gen){if(gen!==requestGeneration||settings.mode!=='live')return;try{const response=await fetch((settings.api||'').replace(/\/$/,'')+'/api/seats',{cache:'no-store',signal:AbortSignal.timeout(6000)});if(!response.ok)throw Error();const data=await response.json();if(!Array.isArray(data.seats)||data.protocol!==1)throw Error();if(gen!==requestGeneration)return;states=Object.fromEntries(data.seats.map(s=>[s.id,s]));events=data.events||[];connected=true;lastUpdate=Date.now()}catch{if(gen!==requestGeneration)return;connected=false}render();pollTimer=setTimeout(()=>poll(gen),2000)}
function start(){clearTimeout(pollTimer);requestGeneration++;connected=false;render();if(settings.mode==='live')poll(requestGeneration)}
$('showAll').onclick=()=>{onlyFree=false;render()};$('showFree').onclick=()=>{onlyFree=true;render()};$('search').oninput=e=>{query=e.target.value;render()};
$('settingsBtn').onclick=()=>{$('mode').value=settings.mode;$('apiUrl').value=settings.api;$('settingError').textContent='';$('settings').showModal()};$('closeSettings').onclick=()=>$('settings').close();
$('settingsForm').onsubmit=e=>{e.preventDefault();let api=$('apiUrl').value.trim().replace(/\/$/,'');try{if(api){const u=new URL(api);if(!['http:','https:'].includes(u.protocol)||u.username||u.password||u.search||u.hash)throw Error();if(location.protocol==='https:'&&u.protocol!=='https:')throw Error('https');api=u.origin}}catch(err){$('settingError').textContent=err.message==='https'?'이 페이지에서는 HTTPS 서버 주소를 입력하세요.':'올바른 서버 주소를 입력하세요. (http:// 또는 https://)';return}settings={mode:$('mode').value,api};persist('seat-settings-v1',settings);$('settings').close();start()};
$('resetDemo').onclick=()=>{demo={owners:{},events:[]};persist('seat-demo-v1',demo);render();toast('시연 기록을 초기화했어요.')};
window.addEventListener('storage',e=>{if(e.key==='seat-demo-v1'){demo=saved(e.key,{owners:{},events:[]});render()}});
fetch('seats.json').then(r=>{if(!r.ok)throw Error();return r.json()}).then(data=>{seats=data.seats;start()}).catch(()=>{$('map').innerHTML='<div class="error-empty">좌석 배치를 불러오지 못했습니다. 페이지를 새로고침해 주세요.</div>'});
