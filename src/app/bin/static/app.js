'use strict';

const paths = {
  fan:'<circle cx="12" cy="12" r="2.3"/><path d="M10.4 9.9C5 9.5 4.9 4.1 8.5 3.5c3.3-.6 5.2 2.7 4.2 6.3M14.7 11.5c3.1-4.4 7.8-1.9 6.2 1.5-1.4 3.1-5.2 3.1-7.6.7M10.9 14.5c2.1 4.8-2.4 7.6-4.7 4.8-2.1-2.6-.3-5.9 3-6.6"/><circle cx="12" cy="12" r="10"/>',
  overview:'<rect x="3" y="3" width="7" height="7" rx="1.6"/><rect x="14" y="3" width="7" height="7" rx="1.6"/><rect x="3" y="14" width="7" height="7" rx="1.6"/><rect x="14" y="14" width="7" height="7" rx="1.6"/>',
  curve:'<path d="M4 3v17h17M5 16l5-3 4 1 6-9"/><circle cx="10" cy="13" r="1.3"/><circle cx="14" cy="14" r="1.3"/><circle cx="20" cy="5" r="1.3"/>',
  chip:'<rect x="6" y="6" width="12" height="12" rx="2"/><path d="M9 2v4m6-4v4M9 18v4m6-4v4M2 9h4m-4 6h4M18 9h4m-4 6h4"/><rect x="9" y="9" width="6" height="6" rx=".7"/>',
  cpu:'<rect x="6" y="6" width="12" height="12" rx="2"/><path d="M9 3v3m6-3v3M9 18v3m6-3v3M3 9h3m-3 6h3M18 9h3m-3 6h3"/>',
  disk:'<rect x="4" y="3" width="16" height="18" rx="2"/><circle cx="12" cy="10" r="4"/><circle cx="12" cy="10" r=".5"/><path d="M12 10l4 3M7 18h.1M10 18h7"/>',
  settings:'<path d="M10 3h4l.6 2.3 2 .9 2.1-.7 2 3.5-1.5 1.7v2.6l1.5 1.7-2 3.5-2.1-.7-2 .9L14 21h-4l-.6-2.3-2-.9-2.1.7-2-3.5 1.5-1.7v-2.6L3.3 9l2-3.5 2.1.7 2-.9z"/><circle cx="12" cy="12" r="3"/>',
  list:'<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 8h8M8 12h8M8 16h5"/>',
  shield:'<path d="M12 2.5l8 3v6c0 5-4 8-8 10-4-2-8-5-8-10v-6z"/><path d="M8.5 12l2.5 2.5 4.5-5"/>',
  arrow:'<path d="M4 12h16m-6-6 6 6-6 6"/>',
  chevron:'<path d="m9 5 7 7-7 7"/>',
  refresh:'<path d="M20 7v5h-5M4 17v-5h5M5.3 8a7 7 0 0 1 11.8-3L20 8M4 16l2.9 3a7 7 0 0 0 11.8-3"/>',
  logout:'<path d="M10 4H5v16h5M10 12h11m-4-4 4 4-4 4"/>',
  menu:'<path d="M4 6h16M4 12h16M4 18h16"/>',
  check:'<path d="m5 12 4 4L19 6"/>',
  plus:'<path d="M12 5v14M5 12h14"/>',
  close:'<path d="m6 6 12 12M6 18 18 6"/>',
  alert:'<path d="m10.4 4.3-8 14A1.5 1.5 0 0 0 3.7 21h16.6a1.5 1.5 0 0 0 1.3-2.7l-8-14a1.8 1.8 0 0 0-3.2 0zM12 9v4m0 4h.01"/>',
  info:'<circle cx="12" cy="12" r="9"/><path d="M12 10v6m0-9h.01"/>',
  eye:'<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
  download:'<path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5"/>',
  release:'<path d="M9 7V3H3m0 0 5 5a8 8 0 1 1-2 8"/>',
};
const $ = (selector, root=document) => root.querySelector(selector);
const $$ = (selector, root=document) => [...root.querySelectorAll(selector)];
const icon = name => `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true">${paths[name]||paths.info}</svg>`;
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function hydrate(root=document){$$('[data-icon]',root).forEach(el=>{if(!el.children.length)el.innerHTML=icon(el.dataset.icon);});}
const ignoredAlarmKey='fan-studio:ignored-alarms:v1';
function readIgnoredAlarms(){try{const value=JSON.parse(sessionStorage.getItem(ignoredAlarmKey)||'[]');return new Set(Array.isArray(value)?value.filter(code=>typeof code==='string').slice(0,256):[]);}catch{return new Set();}}
function saveIgnoredAlarms(){try{sessionStorage.setItem(ignoredAlarmKey,JSON.stringify([...state.ignoredAlarms]));}catch{}}
function clearIgnoredAlarms(){state.ignoredAlarms.clear();try{sessionStorage.removeItem(ignoredAlarmKey);}catch{}}
const hiddenHistoryKey='fan-studio:hidden-temperature-series:v1';
function readHiddenHistorySensors(){try{const value=JSON.parse(localStorage.getItem(hiddenHistoryKey)||'[]');return new Set(Array.isArray(value)?value.filter(id=>typeof id==='string').slice(0,256):[]);}catch{return new Set();}}
function saveHiddenHistorySensors(){try{localStorage.setItem(hiddenHistoryKey,JSON.stringify([...state.hiddenHistorySensors].slice(0,256)));}catch{}}
const hiddenHistoryAveragesKey='fan-studio:hidden-temperature-averages:v1';
function readHiddenHistoryAverages(){try{const value=JSON.parse(localStorage.getItem(hiddenHistoryAveragesKey)||'[]');return new Set(Array.isArray(value)?value.filter(id=>id==='cpu'||id==='disk'):[]);}catch{return new Set();}}
function saveHiddenHistoryAverages(){try{localStorage.setItem(hiddenHistoryAveragesKey,JSON.stringify([...state.hiddenHistoryAverages]));}catch{}}
const state = {csrf:'',setup:false,status:null,hardware:null,config:null,history:[],historySpanSeconds:0,historyLoading:null,historyRequest:0,logs:[],page:'overview',online:false,poll:null,window:5,logLevel:'all',curve:[],source:'max',ignoredTemperatureSensors:[],overviewSourceDraft:null,overviewSourceReturnFocus:null,overviewSourceSensorIds:[],overviewSourceKind:null,hiddenHistorySensors:readHiddenHistorySensors(),hiddenHistoryAverages:readHiddenHistoryAverages(),curveDirty:false,busy:false,operation:null,fetching:false,drafts:{},modeDrafts:{},fanEditors:{},openSettings:new Set(),mapping:null,actionErrors:{},authActive:false,ignoredAlarms:readIgnoredAlarms(),suggestion:null,suggestionReturnFocus:null,alarmMarkup:null};
const sourceNames={max:'CPU 与磁盘最高值',cpu:'CPU 温度',disk:'最高磁盘温度'};
const historySensorColors=['#8a6fc0','#d38b3d','#239d95','#ac6e9c','#78a856','#5798c7','#cf7054','#8a9656','#9b78a7','#c18e4d','#4e9a9c','#bd6b86'];
let historyDialogSourceSignature='';
let historyPlotData=null;
let historyHoverPosition=null;
const recommendedCurve=[{temp:30,percent:35},{temp:40,percent:45},{temp:50,percent:55},{temp:60,percent:70},{temp:70,percent:80},{temp:82,percent:90},{temp:95,percent:100}];
const modeNames={monitor:'仅监测',auto:'温控',manual:'手动',full:'全速',failsafe:'50% 兜底'};
const driverModes={0:'驱动全速模式',1:'主板手动模式',2:'主板自动模式',3:'驱动自动模式 3',4:'驱动自动模式 4',5:'驱动自动模式 5'};
const num = (value,decimals=0) => Number.isFinite(value)?Number(value).toFixed(decimals):'—';
const dateTime = seconds => new Date(seconds*1000).toLocaleString('zh-CN',{month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false});
const timeOnly = seconds => new Date(seconds*1000).toLocaleTimeString('zh-CN',{hour:'2-digit',minute:'2-digit',hour12:false});
const reducedMotion=window.matchMedia('(prefers-reduced-motion: reduce)');
const mobileNavigation=window.matchMedia('(max-width:760px)');
const surfaceAnimations=new WeakMap();
function animateSurface(element,kind='page'){
  if(!element||reducedMotion.matches||!element.animate)return;
  surfaceAnimations.get(element)?.cancel();
  const frames=kind==='disclosure'?[{opacity:.55,clipPath:'inset(0 0 12px 0)'},{opacity:1,clipPath:'inset(0 0 0 0)'}]:[{opacity:.65,filter:'blur(.4px)'},{opacity:1,filter:'blur(0)'}];
  const animation=element.animate(frames,{duration:kind==='disclosure'?190:150,easing:'cubic-bezier(.16,1,.3,1)'});
  surfaceAnimations.set(element,animation);
  animation.finished.then(()=>{if(surfaceAnimations.get(element)===animation)surfaceAnimations.delete(element);}).catch(()=>{});
}
function setDisclosure(body,button,open){
  surfaceAnimations.get(body)?.cancel();
  button.setAttribute('aria-expanded',String(open));
  if(!open&&body.contains(document.activeElement))button.focus({preventScroll:true});
  body.inert=!open;
  if(reducedMotion.matches||!body.animate){body.hidden=!open;return;}
  body.hidden=false;
  const frames=open?[{opacity:.5,clipPath:'inset(0 0 12px 0)'},{opacity:1,clipPath:'inset(0)'}]:[{opacity:1,clipPath:'inset(0)'},{opacity:0,clipPath:'inset(0 0 12px 0)'}];
  const animation=body.animate(frames,{duration:open?190:100,easing:'cubic-bezier(.16,1,.3,1)'});
  surfaceAnimations.set(body,animation);
  animation.finished.then(()=>{if(surfaceAnimations.get(body)!==animation)return;body.hidden=!open;body.inert=!open;surfaceAnimations.delete(body);}).catch(()=>{});
}
function setSidebar(open=false,returnFocus=false){
  const sidebar=$('#sidebar'),button=$('#menu-toggle');
  sidebar.classList.toggle('is-open',open&&mobileNavigation.matches);
  sidebar.inert=mobileNavigation.matches&&!open;
  button.setAttribute('aria-expanded',String(open&&mobileNavigation.matches));
  button.setAttribute('aria-label',open?'收起导航':'展开导航');
  if(returnFocus)button.focus({preventScroll:true});
}
function setControlJump(id='global-curve'){
  $$('.control-jumps a').forEach(link=>{const selected=link.getAttribute('href')===`#control/${id}`;if(selected)link.setAttribute('aria-current','location');else link.removeAttribute('aria-current');});
}
function toast(message,error=false){
  const host=$('#toast-region'),origin=document.activeElement,el=document.createElement('div');
  el.className=`toast${error?' error':''}`;
  el.innerHTML=icon(error?'alert':'check')+`<span>${esc(message)}</span><button type="button" class="toast-dismiss" aria-label="关闭通知">${icon('close')}</button>`;
  let timer,leaving=false,remaining=error?9000:5000,started=0;
  const dismiss=()=>{if(leaving)return;leaving=true;clearTimeout(timer);const restore=el.contains(document.activeElement);el.classList.add('is-leaving');setTimeout(()=>{el.remove();if(restore&&origin?.isConnected)origin.focus({preventScroll:true});},reducedMotion.matches?0:150);};
  const pause=()=>{clearTimeout(timer);if(started){remaining=Math.max(0,remaining-(performance.now()-started));started=0;}};
  const resume=()=>{if(leaving||el.contains(document.activeElement))return;clearTimeout(timer);started=performance.now();timer=setTimeout(dismiss,remaining);};
  $('.toast-dismiss',el).addEventListener('click',dismiss);
  el.addEventListener('pointerenter',pause);el.addEventListener('pointerleave',resume);
  el.addEventListener('focusin',pause);el.addEventListener('focusout',event=>{if(!el.contains(event.relatedTarget))resume();});
  while(host.children.length>=4)host.firstElementChild.remove();
  host.append(el);resume();return el;
}
async function api(path,body){const headers={};if(body!==undefined){headers['Content-Type']='application/json';if(state.csrf)headers['X-CSRF-Token']=state.csrf;}let res;try{res=await fetch(path,{method:body===undefined?'GET':'POST',headers,body:body===undefined?undefined:JSON.stringify(body),credentials:'same-origin',cache:'no-store',signal:AbortSignal.timeout(12000)});}catch(error){throw new Error(error.name==='TimeoutError'?'服务响应超时，请检查风栖是否正在运行。':'无法连接风栖服务，请检查网络或应用状态。');}let data;try{data=await res.json();}catch{throw new Error('服务返回了无法识别的数据，请刷新后重试。');}if(!res.ok||data.ok===false){if(res.status===401&&path!=='/api/login'&&path!=='/api/auth/status'){showAuth({setup_required:false});}const error=new Error(data.error||'请求未成功，请稍后重试。');error.code=data.code;throw error;}return data;}

function showAuth(result){closeSuggestion(false);clearIgnoredAlarms();clearTimeout(state.poll);state.csrf='';state.online=false;state.authActive=true;state.setup=!!result.setup_required;$('#initial-loading').hidden=true;$('#application').hidden=true;$('#auth-view').hidden=false;$('#auth-demo').hidden=!result.demo;$('#auth-title').textContent=state.setup?'为风栖设置访问密码':'连接你的设备';$('#auth-description').textContent=state.setup?'首次使用请设置密码，保护这台 NAS 的控制权限。':'输入访问密码，进入风扇管理台。';$('#auth-submit').innerHTML=`${state.setup?'创建密码并进入':'登录'}<span data-icon="arrow"></span>`;$('#confirm-wrap').hidden=!state.setup;$('#auth-password').autocomplete=state.setup?'new-password':'current-password';$('#auth-password').minLength=state.setup?10:1;$('#auth-password').maxLength=128;$('#auth-confirm').required=state.setup;$('#password-hint').textContent=state.setup?'使用 10 至 128 个字符。请妥善保存此密码。':'密码仅用于访问这台 NAS 上的风栖。';$('#auth-error').textContent='';hydrate($('#auth-view'));updateMutationAvailability();setTimeout(()=>$('#auth-password').focus(),50);}
async function initialize(){try{$('#initial-error').textContent='';$('#initial-retry').hidden=true;const result=await api('/api/auth/status');if(!result.authenticated){showAuth(result);return;}state.csrf=result.csrf_token;await openApplication();}catch(error){$('#initial-error').textContent=error.message;$('#initial-retry').hidden=false;}}
async function openApplication(){state.authActive=false;$('#auth-view').hidden=true;$('#initial-loading').hidden=true;$('#application').hidden=false;navigate(location.hash.slice(1)||'overview');await refresh(true);}
function navigate(route){
  if(route==='curve'){history.replaceState(null,'','#control/global-curve');route='control/global-curve';}
  const [requested,anchor]=route.split('/'),page=['overview','control','hardware','events','settings'].includes(requested)?requested:'overview';
  const changed=state.page!==page,drawerFocused=mobileNavigation.matches&&$('#sidebar').contains(document.activeElement);
  if(page!=='overview'&&historyHoverPosition){historyHoverPosition=null;$('#history-hover-overlay').innerHTML='';$('#history-tooltip').hidden=true;}
  state.page=page;$$('.page').forEach(el=>el.hidden=el.id!==`page-${page}`);$$('.nav-link').forEach(el=>{el.classList.toggle('active',el.dataset.page===page);if(el.dataset.page===page)el.setAttribute('aria-current','page');else el.removeAttribute('aria-current');});
  const title={overview:'设备概览',control:'风扇与温控',hardware:'设备与传感器',events:'事件记录',settings:'设置'}[page];
  $('#breadcrumb').textContent=title;document.title=`${title} · 风栖`;setSidebar();renderPage();
  if(drawerFocused){const heading=$(`#page-${page} h1`);heading?.setAttribute('tabindex','-1');heading?.focus({preventScroll:true});}
  if(changed){window.scrollTo({top:0,behavior:'instant'});if(state.status)animateSurface($(`#page-${page}`));}
  if(page==='control')setControlJump(['global-curve','fans','pwm'].includes(anchor)?anchor:'global-curve');
  if(page==='control'&&['global-curve','fans','pwm'].includes(anchor))requestAnimationFrame(()=>{const target=document.getElementById(anchor);target?.scrollIntoView({block:'start',behavior:reducedMotion.matches?'instant':'smooth'});});
}
async function refresh(initial=false){if(state.fetching||state.authActive)return;clearTimeout(state.poll);state.fetching=true;$('#refresh').classList.add('busy');$('#refresh').setAttribute('aria-busy','true');$('#refresh').disabled=true;const historyWindow=state.window,historyRequest=state.historyRequest;try{const requests=await Promise.all([api('/api/status'),api('/api/hardware'),api('/api/config'),api(`/api/history?minutes=${historyWindow}`),api('/api/logs')]);[state.status,state.hardware]=requests;state.config=requests[2].config;if(historyWindow===state.window&&historyRequest===state.historyRequest){state.history=requests[3].items||[];state.historySpanSeconds=Number(requests[3].available_span_seconds)||0;state.historyLoading=null;}state.logs=requests[4].items||[];state.online=true;const version=`v${state.status.version||'—'}`;$('#app-version').textContent=version;$('#about-version').textContent=version;if(!state.curveDirty){state.curve=state.config.curve.map(p=>({...p}));state.source=state.config.temperature_source;state.ignoredTemperatureSensors=[...(state.config.ignored_temperature_sensor_ids||[])];}renderShared();renderPage();}catch(error){state.online=false;$('#connection-error').hidden=false;$('#connection-error-message').textContent=state.status?`${error.message} 下方保留最后一次成功获取的数据。`:error.message;if(initial&&!state.authActive)toast(error.message,true);}finally{state.fetching=false;$('#refresh').classList.remove('busy');$('#refresh').removeAttribute('aria-busy');$('#refresh').disabled=false;renderConnection();if(!state.authActive)state.poll=setTimeout(()=>refresh(),state.status?.pwm_test?1000:Math.max(2000,(state.config?.poll_interval||3)*1000));}}
function renderConnection(){updateMutationAvailability();$('#connection').className=`connection${state.online?'':' offline'}`;$('#connection-text').textContent=state.online?'实时连接':'连接中断';$('#sidebar-mode').textContent=state.online?(state.status?.pwm_test?'PWM 正在测试 · 后台计时':state.status?.demo?'演示环境 · 模拟硬件':'运行中 · 仅本地访问'):'等待服务恢复';}
function channelProtected(channel){return !!(channel.owned&&channel.effective_mode==='failsafe'&&!channel.error);}
function channelPending(channel){if(channel?.ignored||channel?.testing||state.status?.pwm_test?.id===channel?.id)return false;return !!(channel?.pending||(channel?.owned&&channel.mode==='monitor'));}
function groupHasActiveOutput(group,channels=state.status?.channels||[]){return !!group&&group.pwm_ids.some(id=>channels.some(channel=>channel.id===id&&channel.owned&&channel.mode!=='monitor'));}
function controlStateDescription(){
  if(state.status?.pwm_test)return `正在对 ${shortPwm(state.status.channels.find(channel=>channel.id===state.status.pwm_test.id))} 全速测试，剩余 ${Math.ceil(state.status.pwm_test.remaining_seconds)} 秒后由后台恢复；其他 FAN 保持各自状态。`;
  const groups=state.status?.fan_groups||[],owned=groups.filter(group=>group.owned&&!group.pending),protectedGroups=owned.filter(channelProtected);
  const pending=(state.status?.pending_recovery_ids||[]).length,errors=owned.filter(group=>group.error).length;
  if(state.status?.recovery_blocked)return '恢复记录损坏，已暂停所有接管。请检查事件记录。';
  if(!owned.length&&pending)return `有 ${pending} 路 PWM 仍待恢复；其他 FAN 组可继续单独操作。`;
  if(!owned.length)return '当前仅监测，尚未接管任何风扇。提醒不会自动改变风扇设置。';
  let text=`当前已接管 ${owned.length} 个 FAN 组`;
  if(protectedGroups.length)text+=`，其中 ${protectedGroups.length} 组按 50% 兜底`;
  if(pending)text+=`，${pending} 路 PWM 待恢复`;
  if(errors)text+=`，${errors} 路存在控制错误`;
  return text+'。此提醒不会接管其他 FAN 组。';
}
function alarmSuggestion(alarm){
  const code=alarm.code||'';
  if(code==='disk_hot')return {title:alarm.message,detail:'建议检查磁盘散热与机箱风道，也可选择已配置的 FAN 组应用已保存温控曲线。',kind:'control'};
  if(code==='cpu_hot')return {title:alarm.message,detail:'建议检查 CPU 散热，也可选择已配置的 FAN 组应用已保存温控曲线。',kind:'control'};
  if(code==='temperature_unavailable')return {title:'温度读取失败',detail:'建议先检查温度传感器与驱动。启用调速无法修复缺失的温度读数。',kind:'hardware'};
  if(code.startsWith('fan_stall:')){
    const group=state.status?.fan_groups.find(item=>item.id===code.slice('fan_stall:'.length));
    return {title:`FAN 组转速反馈异常${group?'：'+group.name:''}`,detail:'建议检查实体风扇、RPM 接线与组内 PWM 归属；异常时已接管输出按 50% 兜底。',kind:'control-inspect'};
  }
  if(code==='recovery_record_invalid')return {title:'恢复记录异常，已禁止新接管',detail:'建议查看事件记录并处理恢复记录错误。记录恢复前无法应用调速方案。',kind:'events'};
  if(code==='pending_recovery')return {title:'有 PWM 输出仍待恢复',detail:'建议查看 FAN 分组与事件记录，逐路确认原始状态恢复情况。',kind:'control-inspect'};
  return {title:alarm.message||'设备状态需要检查',detail:'建议检查设备读数与事件记录，再决定是否调整风扇。',kind:'hardware'};
}
function renderShared(){
  if(!state.status)return;
  $('#connection-error').hidden=state.online;$('#demo-label').hidden=!state.status.demo;$('#demo-banner').hidden=!state.status.demo;
  $('#host-label').textContent=state.status.demo?'模拟设备':'本地 NAS';
  const alarms=state.status.alarms||[],activeCodes=new Set(alarms.map(a=>a.code));
  let changed=false;for(const code of state.ignoredAlarms){if(!activeCodes.has(code)){state.ignoredAlarms.delete(code);changed=true;}}if(changed)saveIgnoredAlarms();
  const cards=alarms.filter(a=>!state.ignoredAlarms.has(a.code)).map(a=>{const suggestion=alarmSuggestion(a);return `<section class="notice danger suggestion-card" data-alarm-code="${esc(a.code)}" aria-label="${esc(suggestion.title)}"><span data-icon="alert"></span><div class="suggestion-copy"><strong>${esc(suggestion.title)}</strong><p>${esc(suggestion.detail)}</p><p class="suggestion-status">${esc(controlStateDescription())}</p></div><div class="suggestion-actions"><button class="button small primary" type="button" data-alarm-action="apply">应用建议方案</button><button class="button small" type="button" data-alarm-action="ignore">忽略</button></div></section>`;}).join('');
  if(state.alarmMarkup!==cards){
    const active=document.activeElement,focusedCode=active.closest?.('[data-alarm-code]')?.dataset.alarmCode,focusedAction=active.dataset?.alarmAction;
    replacePanel($('#alarm-region'),cards);state.alarmMarkup=cards;
    if(focusedCode&&focusedAction&&!$('#suggestion-dialog').open){const card=$$('[data-alarm-code]',$('#alarm-region')).find(el=>el.dataset.alarmCode===focusedCode);const target=card&&$(`[data-alarm-action="${focusedAction}"]`,card);target?.focus({preventScroll:true});}
  }
  const count=state.logs.filter(l=>l.level==='warning'||l.level==='error').length;$('#event-count').textContent=count;$('#event-count').hidden=!count;
  $('#release-all').disabled=!state.status.channels.some(c=>c.owned&&!c.ignored)||!state.online;
  hydrate($('#alarm-region'));renderSuggestion();updateMutationAvailability();
}
function selectedSuggestionChannel(){return state.status?.fan_groups.find(group=>group.id===$('#suggestion-channel').value);}
function suggestionUnavailable(){
  if(!state.online||state.authActive)return '当前连接中断，请恢复连接后再应用。';
  if(state.busy)return '正在处理其他操作，请稍候。';
  if(!state.status?.alarms.some(a=>a.code===state.suggestion?.code))return '本次提醒已解除，无需应用建议。';
  if(state.status.recovery_blocked)return '恢复记录损坏，已暂停所有接管。请先查看事件记录。';
  if(!state.status.fan_groups.some(group=>group.ready&&!group.pending&&!group.testing&&group.writable))return '没有配置完整且已手动验证的 FAN 组；请先在风扇控制页面完成实体映射。';
  const group=selectedSuggestionChannel();
  if(!group)return '请先选择一个已配置且已验证 PWM 输出的 FAN 组。';
  if(!group.ready||!group.writable||group.pending||group.testing)return '所选 FAN 组当前不具备接管条件，请检查 PWM 分组和待恢复记录。';
  return '';
}
function renderSuggestion(){
  if(!state.suggestion||!$('#suggestion-dialog').open)return;
  const alarm=state.status?.alarms.find(a=>a.code===state.suggestion.code);
  const suggestion=alarm?alarmSuggestion(alarm):state.suggestion;
  const isControl=suggestion.kind==='control';
  $('#suggestion-title').textContent=isControl?'为一个 FAN 组应用建议方案':'先检查异常来源';
  $('#suggestion-description').textContent=suggestion.detail;
  $('#suggestion-controls').hidden=!isControl;
  $('#suggestion-inspect').hidden=isControl;
  if(isControl){
    const select=$('#suggestion-channel'),selected=select.value;
    const options='<option value="">请选择 FAN 组</option>'+state.status.fan_groups.map(group=>{
      const status=channelPending(group)?'待恢复':channelProtected(group)?'50% 兜底':group.owned?'已接管':'未接管';
      const outputSummary=`${group.verified_pwm_ids.length}/${group.pwm_ids.length} 路 PWM 已手动验证`;
      return `<option value="${esc(group.id)}" ${!group.ready||!group.writable||channelPending(group)||group.testing?'disabled':''}>${esc(group.name)} · ${status} · ${outputSummary}</option>`;
    }).join('');
    if(state.suggestion.optionsMarkup!==options&&document.activeElement!==select){select.innerHTML=options;select.value=selected;state.suggestion.optionsMarkup=options;}
    const group=selectedSuggestionChannel(),settings=group?.curve_mode==='custom'?group:state.config;
    $('#suggestion-source').textContent=(group?.curve_mode==='custom'?'独立方案 · ':'全局方案 · ')+(sourceNames[settings?.temperature_source]||'已保存的温度来源');
    $('#suggestion-curve').textContent=(settings?.curve||[]).map(p=>`${p.temp}°C / ${p.percent}%`).join(' → ');
    $('#suggestion-channel-note').textContent=group?`${group.name}：将同步控制 ${group.pwm_ids.length} 路已验证 PWM。${group.rpm_verified?` RPM 来源为 ${group.rpm_name}。`:'未确认 RPM 输入，无法检测风扇停转。'}`:'只作用于你选择的 FAN 组及组内已验证 PWM。不会自动接管其他风扇。';
    $('#suggestion-submit').textContent='应用并启用';
  }else{
    const target=suggestion.kind==='hardware'?'设备与传感器':suggestion.kind==='events'?'事件记录':'风扇控制';
    $('#suggestion-inspect').textContent=`此建议会打开“${target}”，供你检查异常；不会修改任何通道或设置。`;
    $('#suggestion-submit').textContent=`查看${target}`;
  }
  const resolved=!alarm;
  const reason=isControl?suggestionUnavailable():resolved?'本次提醒已解除，无需继续处理。':'';
  $('#suggestion-unavailable').textContent=reason;
  $('#suggestion-unavailable').hidden=!reason;
  updateSuggestionAvailability();
}
function updateSuggestionAvailability(){
  if(!state.suggestion||!$('#suggestion-dialog').open)return;
  const isControl=state.suggestion.kind==='control',blocked=!state.online||state.authActive||state.busy;
  $('#suggestion-channel').disabled=blocked||!!state.status?.recovery_blocked;
  $('#suggestion-cancel').disabled=state.busy;
  const reason=isControl?suggestionUnavailable():!state.status?.alarms.some(a=>a.code===state.suggestion.code)?'本次提醒已解除，无需继续处理。':'';
  $('#suggestion-unavailable').textContent=reason;$('#suggestion-unavailable').hidden=!reason;
  $('#suggestion-submit').disabled=isControl?!!reason:state.busy||!!reason;
}
function openSuggestion(code,trigger){
  const alarm=state.status?.alarms.find(a=>a.code===code);if(!alarm)return;
  state.suggestion={...alarmSuggestion(alarm),code};state.suggestionReturnFocus=trigger;
  $('#suggestion-channel').value='';$('#suggestion-error').textContent='';
  $('#suggestion-dialog').showModal();$('#suggestion-cancel').focus();renderSuggestion();animateSurface($('#suggestion-dialog'),'disclosure');
}
function closeSuggestion(restoreFocus=true){
  const dialog=$('#suggestion-dialog');if(dialog?.open)dialog.close();
  const trigger=state.suggestionReturnFocus;state.suggestion=null;state.suggestionReturnFocus=null;
  if(restoreFocus&&!state.authActive)(trigger?.isConnected?trigger:$('#refresh')).focus();
}
function sameIdSet(left=[],right=[]){const a=[...new Set(left)].sort(),b=[...new Set(right)].sort();return a.length===b.length&&a.every((value,index)=>value===b[index]);}
function overviewSourceChanged(){
  if(!state.overviewSourceDraft||!state.config)return false;
  const scope=new Set(state.overviewSourceSensorIds),draft=state.overviewSourceDraft.filter(id=>scope.has(id));
  const current=(state.config.ignored_temperature_sensor_ids||[]).filter(id=>scope.has(id));
  return !sameIdSet(draft,current);
}
function overviewSourcePayload(){
  const scope=new Set(state.overviewSourceSensorIds),current=state.config?.ignored_temperature_sensor_ids||[];
  return [...new Set([...current.filter(id=>!scope.has(id)),...(state.overviewSourceDraft||[]).filter(id=>scope.has(id))])];
}
function openOverviewSourceDialog(trigger,kind,onlySensorIds=null,deviceName=''){
  if(!state.config||!state.hardware)return;
  const sensors=(state.hardware.temperature_sensors||[]).filter(sensor=>sensor.kind===kind&&(!onlySensorIds||onlySensorIds.includes(sensor.id)));
  state.overviewSourceReturnFocus=trigger;state.overviewSourceKind=kind;state.overviewSourceSensorIds=sensors.map(sensor=>sensor.id);state.overviewSourceDraft=[...(state.config.ignored_temperature_sensor_ids||[])];
  const kindLabel=kind==='cpu'?'CPU':'硬盘',singleDisk=kind==='disk'&&sensors.length===1&&deviceName;
  $('#overview-source-title').textContent=singleDisk?`忽略 ${deviceName} 温度来源`:`忽略${kindLabel}温度来源`;
  $('#overview-source-dialog-heading').textContent=singleDisk?`${deviceName} 温度节点`:`${kindLabel}温度节点`;
  $('#overview-source-sensor-exclusions h4').textContent=singleDisk?'此硬盘的温度节点':`可单独开关的${kindLabel}传感器`;
  $('#overview-source-description').textContent='勾选表示排除。CPU 与硬盘分别统计；硬盘列表还可逐盘设置。已排除节点不参与对应类别的概览最高温、温度走势、全局温控或传感器健康判断。设备详情仍保留原始读数，高温提醒也继续按原始读数触发。';
  $('#overview-source-error').textContent='';
  replacePanel($('#overview-source-sensor-list'),sensorExclusionMarkup(kind,state.overviewSourceDraft,'overview',state.overviewSourceSensorIds));
  const dialog=$('#overview-source-dialog');dialog.showModal();updateMutationAvailability();
  ($('#overview-source-sensor-list input')||$('#overview-source-cancel')).focus();animateSurface(dialog,'disclosure');
}
function closeOverviewSourceDialog(restoreFocus=true){
  const dialog=$('#overview-source-dialog');if(dialog?.open)dialog.close();
  const trigger=state.overviewSourceReturnFocus;state.overviewSourceDraft=null;state.overviewSourceReturnFocus=null;state.overviewSourceSensorIds=[];state.overviewSourceKind=null;$('#overview-source-error').textContent='';
  if(restoreFocus&&!state.authActive)(trigger?.isConnected?trigger:$('#refresh')).focus();
}

function renderPage(){updateMutationAvailability();if(!state.status)return;if(state.page==='overview')renderOverview();if(state.page==='control')renderControl();if(state.page==='hardware')renderHardware();if(state.page==='events')renderEvents();if(state.page==='settings')renderSettings();updateMutationAvailability();hydrate($('#workspace'));}
function temperatureDetail(temp,kind){
  if(temp===null||temp===undefined){
    const available=(state.hardware?.temperature_sensors||[]).filter(sensor=>sensor.kind===kind&&Number.isFinite(sensor.temperature));
    const ignored=new Set(state.config?.ignored_temperature_sensor_ids||[]);
    if(available.length&&available.every(sensor=>ignored.has(sensor.id)))return kind==='cpu'?'可读 CPU 来源均已排除 · 原始值仍保留提醒':'可读硬盘来源均已排除 · 原始值见硬盘列表';
    return '未检测到可用读数';
  }
  if(kind==='disk'&&temp>=60)return '未排除硬盘最高值 · 温度偏高';
  if(kind==='cpu'&&temp>=85)return '未排除 CPU 最高值 · 温度偏高';
  return kind==='cpu'?'未排除 CPU 传感器最高读数':'未排除硬盘传感器最高读数';
}
function renderOverview(){
  const system=state.status.system,channels=state.status.channels||[],groups=state.status.fan_groups||[],owned=groups.filter(group=>group.owned&&!group.pending),protectedCount=owned.filter(channelProtected).length,pendingCount=(state.status.pending_recovery_ids||[]).length;
  $('#mode-summary').textContent=state.status.pwm_test?`PWM 测试中 · ${Math.ceil(state.status.pwm_test.remaining_seconds)} 秒后恢复`:state.status.recovery_blocked?'接管暂停 · 恢复记录异常':pendingCount?`${pendingCount} 路 PWM 待恢复`:protectedCount?`${protectedCount} 个 FAN 组按 50% 兜底`:owned.length?`${owned.length} 个 FAN 组已接管`:'仅监测 · 保持原状';
  $('#mode-description').textContent=state.status.pwm_test?'正在临时全速测试单路接口；计时与恢复由后台执行。':state.status.recovery_blocked?'恢复记录损坏；请检查事件记录。':pendingCount?'待恢复的 PWM 已单独暂停，其他 FAN 组仍可操作。':owned.length?'只控制已启用 FAN 组中的已验证 PWM。':'风栖正在观察，尚未更改风扇。';
  $('#source-pill').textContent=`全局温控：${sourceNames[system.temperature_source]||'最高温度'}`;
  for(const key of ['cpu','disk']){const value=system[`${key}_temp`],button=$(`[data-overview-source-edit="${key}"]`),limit=key==='disk'?60:85;$('#'+key+'-value').textContent=num(value);button.classList.toggle('hot',Number.isFinite(value)&&value>=limit);$('#'+key+'-detail').textContent=temperatureDetail(value,key);button.setAttribute('aria-label',`${key==='cpu'?'CPU':'硬盘'}未忽略温度最高值 ${num(value)} 摄氏度，点击管理此类忽略来源`);}
  const ignored=new Set(state.config?.ignored_temperature_sensor_ids||[]),temperatureSensors=state.hardware?.temperature_sensors||[];
  const ignoredCount=kind=>temperatureSensors.filter(sensor=>sensor.kind===kind&&ignored.has(sensor.id)).length,totalCount=kind=>temperatureSensors.filter(sensor=>sensor.kind===kind).length;
  $('#overview-source-ignored').textContent=`CPU 忽略 ${ignoredCount('cpu')}/${totalCount('cpu')} 个；硬盘忽略 ${ignoredCount('disk')}/${totalCount('disk')} 个。概览与走势只统计未忽略节点；硬盘列表和高温提醒保留原始读数。`;
  $('#last-updated').textContent=`更新于 ${new Date(state.status.time*1000).toLocaleTimeString('zh-CN',{hour12:false})}`;renderHistory();renderDiskList($('#overview-disks'),state.hardware?.disks||[]);
  if(!groups.length){$('#overview-channels').innerHTML=channels.length?`<div class="empty-state"><span data-icon="fan"></span><h3>尚无 FAN 风扇</h3><p>检测到 ${state.status.rpm_inputs?.length||0} 路 RPM 转速输入和 ${channels.length} 路 PWM 输出。可在风扇与温控页面添加 FAN，再逐路测试并关联 PWM。</p><a class="button small" href="#control">设置 FAN 分组</a></div>`:emptyHardware();return;}
  $('#overview-channels').innerHTML='<div class="fan-overview-header"><span>实体风扇</span><span>RPM 输入</span><span>PWM 输出与占空比</span><span>状态</span></div>'+groups.map(group=>{const duty=group.outputs.map(output=>`${esc(output.name.split('·').pop().trim())} ${num(output.percent)}%`).join(' · ')||'尚未分配 PWM';const status=channelPending(group)?'待恢复':group.error?'控制异常':channelProtected(group)?'50% 兜底':group.testing?'PWM 测试中':group.owned?modeNames[group.mode]||'已接管':group.ready?'仅监测':'待关联 PWM';return `<div class="fan-overview-row"><div class="channel-name"><span class="fan-symbol${group.owned?' owned':''}" data-icon="fan"></span><div><strong>${esc(group.name)}</strong><small>${group.pwm_ids.length} 路 PWM · ${group.verified_pwm_ids.length} 路已验证</small></div></div><div class="rpm-value">${group.rpm_id?num(group.rpm):'—'}<small>${group.rpm_id?'RPM':'未关联 RPM'}</small></div><div class="fan-duty-list">${duty}</div><span><span class="pill ${channelPending(group)||group.error?'warning':channelProtected(group)?'danger':group.owned?'success':'neutral'}">${esc(status)}</span></span><a href="#control" class="row-arrow" aria-label="管理 ${esc(group.name)}" data-icon="chevron"></a></div>`;}).join('');
}
function chartBase(width,height,yTicks,xTicks,yMin,yMax,pad={l:31,r:12,t:12,b:24}){const sx=v=>pad.l+v*(width-pad.l-pad.r),sy=v=>height-pad.b-(v-yMin)/(yMax-yMin)*(height-pad.t-pad.b);let body='';for(const tick of yTicks)body+=`<line class="chart-line" x1="${pad.l}" y1="${sy(tick)}" x2="${width-pad.r}" y2="${sy(tick)}"/><text class="chart-text" x="${pad.l-10}" y="${sy(tick)+3}" text-anchor="end">${tick}</text>`;for(const tick of xTicks)body+=`<text class="chart-text" x="${sx(tick.at)}" y="${height-4}" text-anchor="${tick.at===0?'start':tick.at===1?'end':'middle'}">${esc(tick.label)}</text>`;return{body,sx,sy};}
function pathFor(items,x,y,key){let path='',connected=false;items.forEach(p=>{if(!Number.isFinite(p[key])){connected=false;return;}path+=`${connected?'L':'M'}${x(p).toFixed(1)},${y(p[key]).toFixed(1)} `;connected=true;});return path;}
function historySeriesList(){
  const ignored=new Set(state.config?.ignored_temperature_sensor_ids||[]),order={cpu:0,disk:1};
  return (state.hardware?.temperature_sensors||[]).filter(sensor=>['cpu','disk'].includes(sensor.kind))
    .sort((a,b)=>(order[a.kind]-order[b.kind])||a.name.localeCompare(b.name,'zh-CN')||a.id.localeCompare(b.id))
    .map((sensor,index)=>({...sensor,color:historySensorColors[index%historySensorColors.length]}))
    .filter(sensor=>!ignored.has(sensor.id));
}
function historySensorValue(point,sensor){const value=point.temperatures?.[sensor.kind]?.[sensor.id];return Number.isFinite(value)?value:null;}
function historySensorPath(items,x,y,sensor){let path='',connected=false;for(const point of items){const value=historySensorValue(point,sensor);if(!Number.isFinite(value)){connected=false;continue;}path+=`${connected?'L':'M'}${x(point).toFixed(1)},${y(value).toFixed(1)} `;connected=true;}return path;}
function historyAverageValue(point,sensors){const values=sensors.map(sensor=>historySensorValue(point,sensor)).filter(Number.isFinite);return values.length?values.reduce((sum,value)=>sum+value,0)/values.length:null;}
function historyAveragePath(items,x,y,sensors){let path='',connected=false;for(const point of items){const value=historyAverageValue(point,sensors);if(!Number.isFinite(value)){connected=false;continue;}path+=`${connected?'L':'M'}${x(point).toFixed(1)},${y(value).toFixed(1)} `;connected=true;}return path;}
function historyTimeLabel(seconds,span){const options={hour:'2-digit',minute:'2-digit',hour12:false};if(span<300)options.second='2-digit';return new Date(seconds*1000).toLocaleTimeString('zh-CN',options);}
function renderHistoryLegend(series,means){
  const root=$('#history-series-legend'),active=document.activeElement,keepSensor=root.contains(active)?active.dataset.historyLegendSensor:null,keepMean=root.contains(active)?active.dataset.historyLegendMean:null;
  const meanMarkup=means.map(group=>{const values=group.sensors.map(sensor=>sensor.temperature).filter(Number.isFinite),value=values.length?values.reduce((sum,temp)=>sum+temp,0)/values.length:null,hidden=state.hiddenHistoryAverages.has(group.kind);return `<button class="history-legend-item history-legend-mean${hidden?' is-hidden':''}" type="button" data-history-legend-mean="${group.kind}" aria-pressed="${!hidden}" aria-label="${hidden?'显示':'隐藏'}${group.name}曲线" title="${esc(group.name)} · ${num(value,1)}°C"><i style="--legend-color:${group.color}" aria-hidden="true"></i><small>${group.kind==='cpu'?'CPU':'硬盘'}</small><strong>平均</strong><b>${num(value,1)}°C</b></button>`;}).join('');
  const sensorMarkup=series.map(sensor=>{const hidden=state.hiddenHistorySensors.has(sensor.id),kind=sensor.kind==='cpu'?'CPU':'硬盘';return `<button class="history-legend-item history-legend-sensor${hidden?' is-hidden':''}" type="button" data-history-legend-sensor="${esc(sensor.id)}" aria-pressed="${!hidden}" aria-label="${hidden?'显示':'隐藏'}${kind}传感器 ${esc(sensor.name)} 曲线" title="${kind} · ${esc(sensor.name)} · ${num(sensor.temperature,1)}°C"><i style="--legend-color:${sensor.color}" aria-hidden="true"></i><small>${kind}</small><strong>${esc(sensor.name)}</strong><b>${num(sensor.temperature,1)}°C</b></button>`;}).join('');
  root.innerHTML=meanMarkup+sensorMarkup||'<span class="history-legend-empty">没有可显示的温度传感器</span>';
  if(keepSensor){$$('[data-history-legend-sensor]',root).find(button=>button.dataset.historyLegendSensor===keepSensor)?.focus({preventScroll:true});}
  else if(keepMean){$$('[data-history-legend-mean]',root).find(button=>button.dataset.historyLegendMean===keepMean)?.focus({preventScroll:true});}
}
function updateHistoryHover(clientX,clientY){
  const chart=$('#history-chart'),overlay=$('#history-hover-overlay'),tooltip=$('#history-tooltip'),frame=$('#history-chart-frame'),plot=historyPlotData;
  if(!plot||!plot.items.length||!plot.visible.length&&!plot.visibleMeans.length){overlay.innerHTML='';tooltip.hidden=true;return;}
  const rect=frame.getBoundingClientRect(),width=plot.width,height=plot.height,pad={l:31,r:12,t:12,b:24},scaleX=width/Math.max(1,chart.clientWidth),scaleY=height/Math.max(1,chart.clientHeight);
  const localX=Math.max(0,Math.min(rect.width,clientX-rect.left)),localY=Math.max(0,Math.min(rect.height,clientY-rect.top));
  const svgX=localX*scaleX,plotStartX=pad.l,plotEndX=width-pad.r,targetRatio=Math.max(0,Math.min(1,(svgX-plotStartX)/(plotEndX-plotStartX))),targetTime=plot.plotStart+targetRatio*plot.plotSpan;
  let low=0,high=plot.items.length-1;while(low<high){const mid=(low+high)>>1;if(plot.items[mid].time<targetTime)low=mid+1;else high=mid;}
  const point=low>0&&Math.abs(plot.items[low-1].time-targetTime)<=Math.abs(plot.items[low].time-targetTime)?plot.items[low-1]:plot.items[low];
  const pointX=plot.sx(point),y=value=>plot.sy(Math.max(30,Math.min(90,value))),entries=[];
  for(const group of plot.visibleMeans){const value=historyAverageValue(point,group.sensors);if(Number.isFinite(value))entries.push({name:group.name,color:group.color,value,mean:true});}
  for(const sensor of plot.visible){const value=historySensorValue(point,sensor);if(Number.isFinite(value))entries.push({name:sensor.name,color:sensor.color,value});}
  let marks='';for(const entry of entries)marks+=`<circle cx="${pointX.toFixed(1)}" cy="${y(entry.value).toFixed(1)}" r="${entry.mean?'3.4':'2.8'}" fill="${entry.color}" stroke="#fff" stroke-width="1.3"/>`;
  overlay.innerHTML=`<svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" aria-hidden="true"><line x1="${pointX.toFixed(1)}" y1="${pad.t}" x2="${pointX.toFixed(1)}" y2="${height-pad.b}" stroke="#52665e" stroke-opacity=".48" stroke-width="1" stroke-dasharray="3 3"/>${marks}</svg>`;
  tooltip.innerHTML=`<strong class="history-tooltip-time">${esc(dateTime(point.time))}</strong><div class="history-tooltip-values">${entries.map(entry=>`<div class="history-tooltip-row${entry.mean?' is-average':''}"><i style="--tooltip-color:${entry.color}" aria-hidden="true"></i><span>${esc(entry.name)}</span><b>${num(entry.value,1)}°C</b></div>`).join('')||'<span class="history-tooltip-empty">该采样点暂无可显示读数</span>'}</div>`;
  tooltip.hidden=false;
  const tipWidth=tooltip.offsetWidth,tipHeight=tooltip.offsetHeight;let left=clientX+14,top=clientY+14;
  if(left+tipWidth>window.innerWidth-8)left=clientX-tipWidth-14;if(top+tipHeight>window.innerHeight-8)top=clientY-tipHeight-14;
  tooltip.style.left=`${Math.max(8,Math.min(window.innerWidth-tipWidth-8,left))}px`;tooltip.style.top=`${Math.max(8,Math.min(window.innerHeight-tipHeight-8,top))}px`;
}
function renderHistory(){
  const {width,height}=chartDimensions($('#history-chart')),firstHistoryTime=state.history[0]?.time,lastHistoryTime=state.history.at(-1)?.time,availableHistorySpan=state.historySpanSeconds,end=Math.max(state.status.time,Number.isFinite(lastHistoryTime)?lastHistoryTime:state.status.time),start=end-state.window*60;
  const items=state.history.filter(point=>point.time>=start&&point.time<=end).sort((a,b)=>a.time-b.time),plotStart=items.length?Math.max(start,items[0].time):start,plotSpan=Math.max(1,end-plotStart),series=historySeriesList(),visible=series.filter(sensor=>!state.hiddenHistorySensors.has(sensor.id));
  const means=[{kind:'cpu',name:'CPU 平均',color:'#bf4652',sensors:series.filter(sensor=>sensor.kind==='cpu')},{kind:'disk',name:'硬盘平均',color:'#3e77b5',sensors:series.filter(sensor=>sensor.kind==='disk')}].filter(group=>group.sensors.length);
  const visibleMeans=means.filter(group=>!state.hiddenHistoryAverages.has(group.kind));
  const measured=[...items.flatMap(point=>visible.map(sensor=>historySensorValue(point,sensor))),...items.flatMap(point=>visibleMeans.map(group=>historyAverageValue(point,group.sensors)))].filter(Number.isFinite);
  const yMin=30,yMax=90,yTicks=[30,40,50,60,70,80,90];
  const xTicks=[{at:0,label:historyTimeLabel(plotStart,plotSpan)},{at:.5,label:historyTimeLabel(plotStart+plotSpan/2,plotSpan)},{at:1,label:historyTimeLabel(plotStart+plotSpan,plotSpan)}];
  const base=chartBase(width,height,yTicks,xTicks,yMin,yMax);let body=base.body;const x=point=>base.sx(Math.min(1,Math.max(0,(point.time-plotStart)/plotSpan))),plotY=value=>base.sy(Math.min(yMax,Math.max(yMin,value)));
  for(const sensor of visible){
    const path=historySensorPath(items,x,plotY,sensor);if(!path)continue;
    body+=`<path d="${path}" fill="none" stroke="${sensor.color}" stroke-opacity=".78" stroke-width="1.15" stroke-dasharray="4 3" stroke-linecap="round" stroke-linejoin="round"/>`;
  }
  for(const group of visibleMeans){
    const path=historyAveragePath(items,x,plotY,group.sensors);if(!path)continue;
    body+=`<path d="${path}" fill="none" stroke="${group.color}" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"/>`;
    const last=[...items].reverse().find(point=>Number.isFinite(historyAverageValue(point,group.sensors))),value=last&&historyAverageValue(last,group.sensors);
    if(last)body+=`<circle cx="${x(last)}" cy="${plotY(value)}" r="3" fill="${group.color}"/>`;
  }
  const emptyText=!series.length?((state.hardware?.temperature_sensors||[]).some(sensor=>['cpu','disk'].includes(sensor.kind))?'CPU 与硬盘温度节点均已忽略；取消忽略后可查看走势。':'未发现可用的 CPU 或硬盘温度节点。'):!visible.length&&!visibleMeans.length?'所有曲线已关闭；打开曲线设置重新开启。':!measured.length?'所选来源尚无本次服务运行期间的采样记录。':'';
  if(emptyText)body+=`<text class="chart-text" x="${width/2}" y="${height/2}" text-anchor="middle">${esc(emptyText)}</text>`;
  const visibleNames=[...visibleMeans.map(group=>group.name),...visible.map(sensor=>sensor.name)];
  $('#history-chart').setAttribute('aria-label',visibleNames.length?`显示 ${visibleNames.join('、')} 的温度走势`:'未启用任何温度曲线');
  $('#history-chart').innerHTML=`<svg viewBox="0 0 ${width} ${height}" aria-hidden="true">${body}</svg>`;
  historyPlotData={items,visible,visibleMeans,plotStart,plotSpan,width,height,sx:point=>base.sx(Math.min(1,Math.max(0,(point.time-plotStart)/plotSpan))),sy:base.sy};
  if(historyHoverPosition)updateHistoryHover(historyHoverPosition.x,historyHoverPosition.y);else{$('#history-hover-overlay').innerHTML='';$('#history-tooltip').hidden=true;}
  const legacy=items.some(point=>!point.temperatures);
  const recordedSpan=items.length>1?items.at(-1).time-items[0].time:0,recordedSpanLabel=recordedSpan<60?`${Math.max(1,Math.round(recordedSpan))} 秒`:`${Math.max(1,Math.round(recordedSpan/60))} 分钟`;
  $('#history-caption').textContent=state.historyLoading===state.window?`正在读取 ${state.window} 分钟的历史记录…`:legacy?'旧采样没有传感器明细，不绘入单传感器曲线；新采样会逐步补齐。':items.length?`${state.window} 分钟视图 · 已记录 ${recordedSpanLabel} · ${items.length} 次采样${availableHistorySpan<300?' · 本次运行记录未满 5 分钟，两个范围暂相同':''}`:'正在记录，温度走势将随采样逐渐出现。';
  renderHistoryLegend(series,means);
  if($('#history-series-dialog').open){const signature=series.map(sensor=>sensor.id).join('|')+'#'+means.map(group=>group.kind).join('|');if(signature!==historyDialogSourceSignature)renderHistorySeriesDialog(series,means);}
  const ignoredIds=new Set(state.config?.ignored_temperature_sensor_ids||[]),ignoredCount=(state.hardware?.temperature_sensors||[]).filter(sensor=>['cpu','disk'].includes(sensor.kind)&&ignoredIds.has(sensor.id)).length;
  $('#history-footnote').textContent=`数据仅记录于本次服务运行期间${ignoredCount?' · 忽略来源不显示且不参与平均':''} · 显示范围 30–90°C，超出范围贴边显示 · 每 ${state.config.poll_interval} 秒采样`;
}
function renderHistorySeriesDialog(series=historySeriesList(),means=['cpu','disk'].map(kind=>({kind,name:kind==='cpu'?'CPU 平均':'硬盘平均',sensors:series.filter(sensor=>sensor.kind===kind)})).filter(group=>group.sensors.length)){
  const meanMarkup=means.map(group=>`<label class="history-dialog-toggle history-mean-toggle" style="--mean-color:${group.color|| (group.kind==='cpu'?'#bf4652':'#3e77b5')}"><input type="checkbox" data-history-mean-toggle="${group.kind}" ${state.hiddenHistoryAverages.has(group.kind)?'':'checked'}><span class="history-dialog-line"></span><span><strong>${group.name}</strong><small>逐采样平均有读数的 ${group.sensors.length} 个未忽略来源</small></span></label>`).join('');
  const sensorsMarkup=['cpu','disk'].map(kind=>{const sensors=series.filter(sensor=>sensor.kind===kind);if(!sensors.length)return '';const label=kind==='cpu'?'CPU 传感器':'硬盘传感器';return `<section class="history-dialog-group"><h3>${label}<span>${sensors.length}</span></h3>${sensors.map(sensor=>`<label class="history-dialog-toggle"><input type="checkbox" data-history-sensor-toggle="${esc(sensor.id)}" ${state.hiddenHistorySensors.has(sensor.id)?'':'checked'}><span class="history-dialog-line" style="--series-color:${sensor.color}"></span><span><strong>${esc(sensor.name)}</strong><small>当前 ${num(sensor.temperature,1)}°C</small></span></label>`).join('')}</section>`;}).join('');
  $('#history-mean-settings').innerHTML=meanMarkup||'<p class="history-dialog-empty">当前没有可计算的平均值。</p>';
  $('#history-sensor-settings').innerHTML=sensorsMarkup||'<p class="history-dialog-empty">没有未忽略的传感器可显示。</p>';
  historyDialogSourceSignature=series.map(sensor=>sensor.id).join('|')+'#'+means.map(group=>group.kind).join('|');
}
function emptyHardware(){return `<div class="empty-state"><span data-icon="fan"></span><h3>还没有可控制的 PWM 输出</h3><p>请确认主板驱动已暴露 pwm 与 pwm_enable 属性。检测到的 PWM 是逻辑输出，不代表实体风扇插座。</p><a class="button small" href="#hardware">查看设备与传感器</a></div>`;}
function diskAvailability(disk){if(disk.status==='reading')return disk.detail||'正在读取';if(disk.status==='sleeping')return '设备休眠，未唤醒';return disk.detail||'暂无温度';}
function diskTemperatureSensors(disk){
  const sensors=(state.hardware?.temperature_sensors||[]).filter(sensor=>sensor.kind==='disk');
  const matched=sensors.filter(sensor=>(sensor.block_devices||[]).includes(disk.name)||(disk.sensor_id&&sensor.id===disk.sensor_id));
  if(matched.length)return matched;
  if(String(disk.id||'').startsWith('disk:unknown:')){const deviceId=String(disk.id).split(':').slice(2).join(':');return sensors.filter(sensor=>sensor.device_id===deviceId);}
  return [];
}
function renderDiskList(host,disks){
  if(!host)return;
  if(!disks.length){replacePanel(host,'<p class="muted small-text">未发现物理硬盘。</p>');return;}
  const ignored=new Set(state.config?.ignored_temperature_sensor_ids||[]);
  replacePanel(host,disks.map(disk=>{
    const sensors=diskTemperatureSensors(disk),excluded=sensors.filter(sensor=>ignored.has(sensor.id)),active=sensors.filter(sensor=>!ignored.has(sensor.id)&&Number.isFinite(sensor.temperature));
    const allExcluded=sensors.length>0&&excluded.length===sensors.length,partial=excluded.length>0&&!allExcluded;
    const value=active.length?Math.max(...active.map(sensor=>sensor.temperature)):allExcluded?disk.temperature:sensors.length?null:disk.temperature;
    const status=allExcluded?'已排除 · 原始读数':partial?`部分排除 ${excluded.length}/${sensors.length} 个节点`:sensors.length?'参与统计与走势':diskAvailability(disk);
    const source=disk.source==='hwmon'?'hwmon':disk.source==='smartctl'?'SMART':diskAvailability(disk);
    return `<div class="disk-temperature-row"><div class="disk-temperature-identity"><strong>${esc(disk.name)}</strong><small>${esc(disk.model||disk.name)}</small></div><strong class="disk-temperature-value${!allExcluded&&Number.isFinite(value)&&value>=60?' sensor-hot':''}${allExcluded?' is-excluded':''}">${num(value,1)}<small>°C</small></strong><div class="disk-temperature-status"><span class="disk-source">${esc(source)}</span><span class="disk-ignore-state${allExcluded?' is-excluded':''}">${esc(status)}</span></div><button type="button" class="button small disk-ignore-button" data-disk-ignore="${esc(disk.id)}" aria-haspopup="dialog" aria-controls="overview-source-dialog" ${sensors.length?'':'disabled'}>${sensors.length?'排除设置':'无可忽略节点'}</button></div>`;
  }).join(''));
}
function shortPwm(channel){return channel?.name?.split('·').at(-1).trim()||channel?.id||'PWM';}
function panelNodeKey(node){
  if(node.nodeType!==1)return null;
  for(const name of ['id','data-fan-control','data-pwm','data-fan-settings','data-alarm-code','data-focus','data-point-index','data-point','data-icon'])if(node.hasAttribute(name))return `${node.nodeName}:${name}:${node.getAttribute(name)}`;
  for(const name of ['data-action','data-pwm-action','data-alarm-action','data-test-stop','data-dismiss-test'])if(node.hasAttribute(name))return `${node.nodeName}:${name}:${node.getAttribute(name)}:${node.getAttribute('data-mode')||node.getAttribute('data-index')||''}`;
  return null;
}
function compatiblePanelNode(current,next){return current.nodeType===next.nodeType&&(current.nodeType!==1||(current.nodeName===next.nodeName&&current.namespaceURI===next.namespaceURI));}
function syncPanelNode(current,next){
  if(current.nodeType!==1){if(current.nodeValue!==next.nodeValue)current.nodeValue=next.nodeValue;return;}
  const focused=current===document.activeElement;
  for(const attribute of [...current.attributes])if(!next.hasAttribute(attribute.name))current.removeAttribute(attribute.name);
  for(const attribute of [...next.attributes]){
    if(focused&&attribute.name==='value')continue;
    if(current.getAttribute(attribute.name)!==attribute.value)current.setAttribute(attribute.name,attribute.value);
  }
  // Icon SVG is hydrated once; polling only changes the icon when its key changes.
  if(!(current.hasAttribute('data-icon')&&!next.childNodes.length))syncPanelChildren(current,next);
  if(current.nodeName==='INPUT'){
    if(!focused&&current.value!==next.value)current.value=next.value;
    if(current.type==='checkbox'||current.type==='radio')current.checked=next.checked;
  }else if(current.nodeName==='SELECT'&&!focused&&current.value!==next.value)current.value=next.value;
}
function syncPanelChildren(current,next){
  const children=[...current.childNodes],used=new Set(),keyed=new Map(children.map(node=>[panelNodeKey(node),node]).filter(([key])=>key));
  let index=0;
  for(const desired of [...next.childNodes]){
    const key=panelNodeKey(desired),at=current.childNodes[index]||null;
    let matching=key?keyed.get(key):at&&!used.has(at)&&!panelNodeKey(at)&&compatiblePanelNode(at,desired)?at:null;
    if(matching&&(!compatiblePanelNode(matching,desired)||used.has(matching)))matching=null;
    if(!matching&&!key)matching=children.find(node=>!used.has(node)&&!panelNodeKey(node)&&compatiblePanelNode(node,desired));
    if(!matching){matching=desired.cloneNode(true);current.insertBefore(matching,at);}else{if(matching!==at)current.insertBefore(matching,at);syncPanelNode(matching,desired);}
    used.add(matching);index++;
  }
  for(const child of [...current.childNodes])if(!used.has(child))child.remove();
}
function replacePanel(host,markup){
  const template=document.createElement('template');template.innerHTML=markup;
  syncPanelChildren(host,template.content);hydrate(host);
}
function currentFanConfig(id){return state.config.fan_groups.find(group=>group.id===id);}
function fanEditor(group){
  if(!state.fanEditors[group.id])state.fanEditors[group.id]={name:group.name,rpm_id:group.rpm_id||'',rpm_verified:!!group.rpm_verified,curve_mode:group.curve_mode||'global',temperature_source:group.temperature_source||state.config.temperature_source,ignored_temperature_sensor_ids:[...(group.ignored_temperature_sensor_ids||[])],curve:(group.curve||state.config.curve).map(point=>({...point})),dirty:false,error:''};
  return state.fanEditors[group.id];
}
function updateManualDraftState(card,id){
  const group=state.status?.fan_groups.find(item=>item.id===id),label=$('.manual-draft-status',card);
  if(!group||!label)return;
  const value=state.drafts[id]??group.saved_percent??50;
  label.hidden=!!(group.owned&&group.mode==='manual'&&Number(value)===Number(group.saved_percent));
}
function fanControlReason(group){
  if(!state.online)return '服务连接中断，请恢复连接后重试。';
  if(state.status.recovery_blocked)return '恢复记录异常，暂不能接管。请查看事件记录。';
  if(group.testing)return '组内 PWM 正在测试，请等待恢复或立即结束测试。';
  if(channelPending(group))return '组内 PWM 仍待恢复，请先重试释放此 FAN。';
  if(!group.pwm_ids.length)return '尚未关联 PWM。请到下方测试接口，再添加到此 FAN。';
  if(!group.ready)return 'PWM 归属尚未完成验证，或已保存的接口当前不可用。请在下方检查。';
  if(!group.writable)return '本组接口当前不可写，请检查驱动。';
  return '';
}
function renderControl(){
  const notice=$('#pending-recovery-notice'),pending=state.status.pending_recovery_ids||[];
  notice.hidden=!pending.length;
  if(pending.length){const names=pending.map(id=>shortPwm(state.status.channels.find(channel=>channel.id===id))||id);notice.innerHTML=`<span data-icon="alert"></span><div><strong>${pending.length} 路 PWM 仍待恢复</strong><p>${names.map(esc).join('、')} 已暂停；其他 FAN 与独立 PWM 仍可操作。可在下方点击“重试恢复”；若需要停止访问，也可勾选“忽略”，恢复记录仍会保留。</p></div>`;hydrate(notice);}
  if(!$('#global-curve').contains(document.activeElement)&&!drag)renderCurve();
  const rpms=state.status.rpm_inputs||[];$('#fan-scan-summary').textContent=`检测到 ${rpms.length} 路 RPM 输入，以此建立默认 FAN；名称、PWM 归属和附加 FAN 均可调整。`;
  renderFanGroupControls();renderPwmTest();renderPwmInterfaces();renderLegacyMappings();
}
function customCurveMarkup(id,draft){
  if(draft.curve_mode!=='custom')return `<p class="curve-follow-note">跟随全局：${esc(sourceNames[state.config.temperature_source])} · ${(state.config.curve||[]).map(point=>`${point.temp}°C / ${point.percent}%`).join(' → ')}</p>`;
  return `<div class="fan-custom-curve"><label class="fan-field">独立温度来源<select data-edit="temperature_source" data-focus="${esc(id)}-source" aria-label="${esc(draft.name)} 独立温度来源">${Object.entries(sourceNames).map(([value,name])=>`<option value="${value}" ${draft.temperature_source===value?'selected':''}>${name}</option>`).join('')}</select></label><div class="sensor-exclusions custom-sensor-exclusions"><h4>排除温度节点</h4><p>仅影响此 FAN 的独立曲线与健康判断；概览和高温提醒仍显示该温度。没有剩余可读温度时按 50% 兜底。</p>${sensorExclusionMarkup(draft.temperature_source,draft.ignored_temperature_sensor_ids,'group')}</div><div class="fan-custom-heading"><h3>独立曲线节点</h3><button class="button small" data-action="custom-add" ${draft.curve.length>=12?'disabled':''}>添加节点</button></div><div class="custom-curve-points">${draft.curve.map((point,index)=>`<div class="custom-curve-point"><span>节点 ${index+1}</span><label><input type="number" min="0" max="100" value="${Number.isFinite(point.temp)?point.temp:''}" data-custom-index="${index}" data-custom-key="temp" data-focus="${esc(id)}-temp-${index}" aria-label="${esc(draft.name)} 节点 ${index+1}温度" >°C</label><label><input type="number" min="35" max="100" value="${Number.isFinite(point.percent)?point.percent:''}" data-custom-index="${index}" data-custom-key="percent" data-focus="${esc(id)}-percent-${index}" aria-label="${esc(draft.name)} 节点 ${index+1}占空比" >%</label><button class="icon-button" data-action="custom-remove" data-index="${index}" aria-label="删除节点 ${index+1}" ${draft.curve.length<=2?'disabled':''}>${icon('close')}</button></div>`).join('')}</div><p class="field-hint">温度递增，占空比随温度保持或升高（35%–100%）；末端可自定义。</p></div>`;
}
function renderFanGroupControls(){
  const host=$('#fan-group-controls'),groups=state.status.fan_groups||[],rpmInputs=state.status.rpm_inputs||[];
  if(!groups.length){replacePanel(host,`<section class="panel"><div class="empty-state"><span data-icon="fan"></span><h3>未检测到 RPM 输入</h3><p>可以手动添加 FAN，再测试并关联 PWM。没有 RPM 反馈时仍可调速，但无法检测停转。</p><button class="button" data-action="add-group">添加 FAN</button></div></section>`);return;}
  const markup=groups.map(group=>{
    const cfg=currentFanConfig(group.id)||group,draft=fanEditor(cfg),pending=channelPending(group),reason=fanControlReason(group),value=state.drafts[group.id]??group.saved_percent??50;
    const manual=state.modeDrafts[group.id]==='manual'||(state.modeDrafts[group.id]===undefined&&group.mode==='manual');
    const manualUnapplied=manual&&(!group.owned||group.mode!=='manual'||Number(value)!==Number(group.saved_percent));
    const label=pending?'待恢复':group.startup_error?'恢复设置失败 · 仅监测':group.error?'控制异常':group.testing?'PWM 测试中':channelProtected(group)?'50% 兜底':group.owned?modeNames[group.mode]||'已接管':group.ready?'仅监测':'待关联 PWM';
    const activeMapping=groupHasActiveOutput(cfg)||(state.status.pwm_test&&cfg.pwm_ids.includes(state.status.pwm_test.id));
    const settingsOpen=state.openSettings.has(group.id),settingsBodyId=`fan-settings-body-${group.id.replace(/[^a-zA-Z0-9_-]/g,'-')}`;
    const detected=/^fan-[a-f0-9]{20}$/.test(group.id);
    return `<section class="control-channel fan-group-card${group.owned?' is-owned':''}" data-fan-control="${esc(group.id)}">
      <div class="control-channel-header"><span class="fan-symbol${group.owned?' owned':''}" data-icon="fan"></span><div class="control-channel-title"><h3>${esc(group.name)}</h3><p><span class="pill ${pending||group.startup_error||group.error?'warning':group.owned?'success':'neutral'}">${esc(label)}</span></p></div><div class="control-channel-readings"><div class="compact-reading"><span>${esc(group.rpm_name||'RPM 输入')}</span><strong>${group.rpm_id?num(group.rpm):'—'}<small>${group.rpm_id?'RPM':'未关联'}</small></strong></div><div class="compact-reading"><span>当前输出</span><strong>${group.target_percent===null?'—':num(group.target_percent)}<small>${group.target_percent===null?'':'%'}</small></strong></div></div></div>
      <div class="fan-bound-outputs">${group.pwm_ids.length?(group.outputs||[]).map(output=>`<span>${esc(shortPwm(output))} <strong>${num(output.percent)}%</strong>${cfg.verified_pwm_ids.includes(output.id)?'':' · 待验证'}</span>`).join(''):'未关联 PWM 控制输出'}${group.pwm_ids.length>(group.outputs||[]).length?'<span class="field-error">有已保存 PWM 当前缺失</span>':''}</div>
      <div class="fan-mode-controls"><div class="segmented" role="group" aria-label="${esc(group.name)} 控制模式"><button data-action="mode" data-mode="auto" data-focus="${esc(group.id)}-auto" class="${group.owned&&group.mode==='auto'?'selected':''}" aria-pressed="${!!(group.owned&&group.mode==='auto')}" ${reason?'disabled':''}>温控</button><button data-action="mode" data-mode="full" data-focus="${esc(group.id)}-full" class="${group.owned&&group.mode==='full'?'selected':''}" aria-pressed="${!!(group.owned&&group.mode==='full')}" ${reason?'disabled':''}>全速</button><button data-action="mode" data-mode="manual" data-focus="${esc(group.id)}-manual" aria-controls="manual-control-${esc(group.id)}" aria-expanded="${manual}" title="展开手动设置，点击应用后生效" class="${manual?'selected':''}" aria-pressed="${manual}" ${reason?'disabled':''}>手动</button></div><button class="button small" data-action="release" data-focus="${esc(group.id)}-release" ${!group.owned&&!pending?'disabled':''}>${pending?'重试释放':'释放接管'}</button></div>
      ${manual?`<div class="manual-control" id="manual-control-${esc(group.id)}"><label class="sr-only" for="duty-range-${esc(group.id)}">${esc(group.name)} 手动 PWM 百分比</label><input id="duty-range-${esc(group.id)}" type="range" min="25" max="100" step="1" value="${value}" data-action="duty" data-focus="${esc(group.id)}-range" ${reason?'disabled':''}><label class="manual-number"><input type="number" min="25" max="100" step="1" value="${value}" data-action="duty-number" data-focus="${esc(group.id)}-number" aria-label="${esc(group.name)} 手动占空比百分数" ${reason?'disabled':''}><span>%</span></label><button class="button primary" data-action="apply-duty" ${reason?'disabled':''}>应用</button><p class="field-hint"><span class="manual-draft-status" ${manualUnapplied?'':'hidden'}>修改尚未应用 · </span>输入 25%–100%，点击应用后同步控制本 FAN 的全部 PWM。</p></div>`:''}
      <p class="control-explanation">${reason?esc(reason):channelProtected(group)?'温度或已确认 RPM 反馈异常，本组已接管 PWM 正按 50% 兜底。':group.owned&&group.mode==='auto'?`温控使用${cfg.curve_mode==='custom'?'独立曲线':'全局曲线'} · ${esc(sourceNames[cfg.curve_mode==='custom'?cfg.temperature_source:state.config.temperature_source])} · 温度 ${num(group.source_temp)}°C`:group.owned&&group.mode==='full'?'已明确选择全速，本 FAN 的全部 PWM 目标为 100%。':group.owned&&group.mode==='manual'?`当前生效的手动输出为 ${num(group.target_percent)}%；重启后恢复已保存值。${manualUnapplied?' 修改后需点击“应用”才生效。':''}`:'选择上方模式开始控制；重启后恢复已保存的模式。'} ${!group.pwm_ids.length||!group.ready?'<a class="text-link" href="#control/pwm">前往 PWM 测试与关联'+icon('arrow')+'</a>':''}</p>
      ${group.startup_error?`<p class="field-error" role="status">启动恢复失败：${esc(group.startup_error)}。${pending?'本 FAN 已停止调速，PWM 仍待恢复，请重试释放。':'本 FAN 已转为监测；处理问题后可重新选择模式。'}</p>`:''}${group.error?`<p class="field-error">${esc(group.error)}</p>`:''}${state.actionErrors[group.id]?`<p class="field-error" role="alert">${esc(state.actionErrors[group.id])}</p>`:''}
      <section class="fan-settings" data-fan-settings="${esc(group.id)}"><button type="button" class="fan-settings-toggle" data-action="toggle-settings" aria-expanded="${settingsOpen}" aria-controls="${esc(settingsBodyId)}"><span>风扇设置</span><span class="fan-settings-chevron" data-icon="chevron" aria-hidden="true"></span></button><div class="fan-settings-body" id="${esc(settingsBodyId)}" ${settingsOpen?'':'hidden inert'}><div class="fan-field-grid"><label class="fan-field">FAN 名称<input maxlength="64" data-edit="name" data-focus="${esc(group.id)}-name" value="${esc(draft.name)}"></label><label class="fan-field">RPM 转速输入<select data-edit="rpm_id" data-focus="${esc(group.id)}-rpm" aria-label="${esc(draft.name)} RPM 转速输入" ${activeMapping?'disabled':''}><option value="">不关联 RPM</option>${rpmInputs.map(input=>`<option value="${esc(input.id)}" ${draft.rpm_id===input.id?'selected':''}>${esc(input.name)} · ${num(input.rpm)} RPM</option>`).join('')}</select></label></div><label class="confirmation-label"><input type="checkbox" data-edit="rpm_verified" data-focus="${esc(group.id)}-rpm-verify" ${draft.rpm_verified?'checked':''} ${activeMapping||!draft.rpm_id?'disabled':''}><span>我已确认此 RPM 输入属于这把风扇，启用停转检测</span></label>${activeMapping?'<p class="field-hint">更换 RPM 或 PWM 归属前，请先释放此 FAN；名称和温控方案仍可修改。</p>':''}<label class="fan-field curve-mode-field">温控方案<select data-edit="curve_mode" data-focus="${esc(group.id)}-curve-mode" aria-label="${esc(draft.name)} 温控方案"><option value="global" ${draft.curve_mode!=='custom'?'selected':''}>跟随全局温控曲线</option><option value="custom" ${draft.curve_mode==='custom'?'selected':''}>使用独立温控曲线</option></select></label>${customCurveMarkup(group.id,draft)}<div class="fan-settings-footer"><button class="quiet-button" data-action="delete-group" ${group.owned||pending||group.testing?'disabled':''}>删除风扇${detected?' · 默认':''}</button>${detected?'<span class="detected-fan-note">检测到的 RPM 输入</span>':''}<span class="settings-save-state">${draft.dirty?'有未保存修改':'设置已保存'}</span><button class="button primary" data-action="save-group">保存设置</button></div><p class="field-error" data-role="group-error" role="alert">${esc(draft.error||'')}</p></div></section>
    </section>`;
  }).join('');
  replacePanel(host,markup);
}
function pwmUnavailable(channel){
  if(channel?.ignored)return '此 PWM 已忽略';
  if(!state.online)return '服务连接中断';
  if(state.status.recovery_blocked)return '恢复记录异常，请查看事件记录';
  if(channelPending(channel)||(state.status.pending_recovery_ids||[]).includes(channel.id))return '此路待恢复；可重试恢复，也可勾选忽略停止访问（恢复记录保留）';
  if(state.status.pwm_test?.id===channel.id)return '此路正在测试';
  if(state.status.pwm_test)return '另一路 PWM 正在测试，请等待结束';
  if(channel.owned)return '正在由 FAN 控制，请先释放所属 FAN';
  if(!channel.writable)return '驱动未开放写入';
  return '';
}
function mappingMarkup(channel,assigned){
  if(state.mapping?.id!==channel.id)return '';
  const mapping=state.mapping,groups=state.config.fan_groups||[],target=groups.find(group=>group.id===mapping.target),active=target&&groupHasActiveOutput(target);
  return `<div class="pwm-mapping-editor"><h3>将 ${esc(shortPwm(channel))} 添加到 FAN</h3><p>测试后观察实体风扇或 RPM 变化，确认归属；软件不会根据接口编号自动判断。</p><div class="mapping-select-row"><label class="fan-field">选择 FAN<select data-mapping="target" data-focus="mapping-target"><option value="">请选择 FAN</option>${groups.map(group=>`<option value="${esc(group.id)}" ${mapping.target===group.id?'selected':''} ${groupHasActiveOutput(group)?'disabled':''}>${esc(group.name)}${groupHasActiveOutput(group)?' · 请先释放':''}</option>`).join('')}</select></label><a class="text-link" href="#control/fans">添加或管理 FAN</a></div><label class="confirmation-label"><input type="checkbox" data-mapping="confirmed" data-focus="mapping-confirmed" ${mapping.confirmed?'checked':''}>我已手动测试，确认此 PWM 控制所选 FAN</label>${assigned&&assigned.id!==mapping.target?`<p class="field-hint">保存后将从 ${esc(assigned.name)} 移至所选 FAN。</p>`:''}<div class="mapping-actions"><button class="button primary" data-pwm-action="save-map" ${!mapping.target||!mapping.confirmed||active?'disabled':''}>确认添加</button>${assigned?'<button class="button" data-pwm-action="remove-map">解除关联</button>':''}<button class="quiet-button" data-pwm-action="cancel-map">取消</button></div><p class="field-error" role="alert">${esc(mapping.error||'')}</p></div>`;
}
function renderPwmInterfaces(){
  const channels=state.status.channels||[],groups=state.config.fan_groups||[],ignoredCount=channels.filter(channel=>channel.ignored).length;$('#pwm-count').textContent=`${channels.length} 路已识别 · ${channels.length-ignoredCount} 路监控${ignoredCount?' · '+ignoredCount+' 路已忽略':''}`;
  if(!channels.length){replacePanel($('#pwm-interfaces'),emptyHardware());return;}
  const rows=channels.map(channel=>{
    const assigned=groups.find(group=>group.pwm_ids.includes(channel.id)),pending=channelPending(channel)||(state.status.pending_recovery_ids||[]).includes(channel.id),testing=state.status.pwm_test?.id===channel.id,reason=pwmUnavailable(channel);
    const ignored=!!channel.ignored;
    if(ignored){const recovery=channel.owned?'恢复失败记录保留；取消勾选可手动重试恢复':'此接口当前完全忽略';return `<article class="pwm-interface pwm-interface-ignored" data-pwm="${esc(channel.id)}"><div class="pwm-interface-main"><div class="pwm-identity"><strong>${esc(shortPwm(channel))}</strong><small>${esc(channel.name)}</small></div><div class="pwm-reading"><strong>已忽略</strong><span>不读取状态</span></div><div class="pwm-assignment"><span>不参与 FAN 控制</span><small>${recovery}</small></div><div class="pwm-actions"><div class="pwm-ignore-control"><label class="pwm-ignore-toggle"><input type="checkbox" data-pwm-ignore="${esc(channel.id)}" checked><span>忽略已开启</span></label><small>取消勾选＝解除忽略</small></div></div></div><p class="pwm-ignore-explanation">不读取数值、模式、权限或健康状态；不测试、不控制。${channel.owned?'不会改动硬件，当前输出保持原状，恢复快照继续保留。':''}</p></article>`;}
    const assignedActive=assigned&&groupHasActiveOutput(assigned),canMap=!reason&&!assignedActive;
    const ignoreHelp=pending?'待恢复。勾选后不再访问，硬件保持当前状态；低占空比下风扇可能慢转或停转，恢复记录保留。':'未勾选：正在监测';
    return `<article class="pwm-interface" data-pwm="${esc(channel.id)}"><div class="pwm-interface-main"><div class="pwm-identity"><strong>${esc(shortPwm(channel))}</strong><small>${esc(channel.name)}</small></div><div class="pwm-reading"><strong>${num(channel.percent)}<small>%</small></strong><span>${esc(driverModes[channel.enable]||`模式 ${channel.enable}`)}</span></div><div class="pwm-assignment"><span>${assigned?esc(assigned.name):'未添加到 FAN'}</span><small>${pending?'待恢复 · 控制已暂停':testing?'全速测试中':assigned?.verified_pwm_ids.includes(channel.id)?'已手动确认归属':channel.owned?'已接管':channel.writable?'正在监控 · 可测试':'只读'}</small></div><div class="pwm-actions"><div class="pwm-ignore-control"><label class="pwm-ignore-toggle"><input type="checkbox" data-pwm-ignore="${esc(channel.id)}"><span>勾选以忽略</span></label><small>${ignoreHelp}</small></div>${pending?'<button class="button small" data-pwm-action="retry">重试恢复</button>':testing?'<button class="button small danger" data-pwm-action="stop">立即结束</button>':`<button class="button small" data-pwm-action="test" ${reason?'disabled':''}>测试 · 10 秒</button>`}<button class="button small" data-pwm-action="map" ${!canMap?'disabled':''}>${assigned?'管理归属':'添加到 FAN'}</button></div></div>${reason&&!testing?`<p class="pwm-reason">${esc(reason)}${assignedActive?' · 请在上方释放 '+esc(assigned.name):''}</p>`:''}${channel.error?`<p class="field-error pwm-interface-error">${esc(channel.error)}</p>`:''}${state.actionErrors[channel.id]?`<p class="field-error pwm-interface-error" role="alert">${esc(state.actionErrors[channel.id])}</p>`:''}${mappingMarkup(channel,assigned)}</article>`;
  }).join('');replacePanel($('#pwm-interfaces'),rows);
}
function renderPwmTest(){
  const test=state.status.pwm_test,result=state.status.pwm_test_result,host=$('#pwm-test-feedback'),rpms=state.status.rpm_inputs||[],groups=state.config.fan_groups||[];
  if(!test&&(!result||state.dismissedTest===result.ended_at)){host.innerHTML='<p class="test-introduction">“测试”不需要预先关联 FAN：只让选中接口全速 10 秒，后台自动恢复测试前状态，支持立即结束。</p>';return;}
  const id=test?.id||result.id,channel=state.status.channels.find(item=>item.id===id),baseline=test?.baseline_rpms||(result?.id===id?result.baseline_rpms:null)||{},final=result?.id===id?result.final_rpms||{}:{};
  const rpmRows=rpms.map(input=>{const fan=groups.find(group=>group.rpm_id===input.id),before=baseline[input.id],after=final[input.id];return `<tr><th scope="row">${esc(fan?.name||input.name)}<small>${esc(input.name)}</small></th><td>${num(before)} RPM</td><td><strong>${num(input.rpm)} RPM</strong></td><td>${test?'测试结束后显示':num(after)+' RPM'}</td></tr>`;}).join('');
  const title=test?`${shortPwm(channel)} 正在全速测试 · 剩余 ${Math.max(0,Math.ceil(test.remaining_seconds))} 秒`:result.ok?`${shortPwm(channel)} 测试已结束，已恢复测试前状态`:`${shortPwm(channel)} 测试恢复失败`;
  replacePanel(host,`<section class="pwm-test-panel ${result&&!test&&!result.ok?'test-failed':''}"><div class="section-heading"><div><h3>${esc(title)}</h3><p>${test?'请观察哪把风扇声音或转速变化。计时由后台执行，关闭页面仍会恢复。':result.ok?'对照变化后，在对应 PWM 点击“添加到 FAN”，由你确认实际归属。':esc(result.error||'恢复记录已保留，请在对应 PWM 重试恢复。')}</p></div>${test?`<button class="button danger" data-test-stop="${esc(id)}">立即结束</button>`:'<button class="quiet-button" data-dismiss-test aria-label="收起本次测试结果">收起</button>'}</div>${rpms.length?`<div class="test-rpm-table-wrap"><table class="test-rpm-table"><thead><tr><th>FAN / RPM 输入</th><th>测试前</th><th>实时转速</th><th>测试结束时</th></tr></thead><tbody>${rpmRows}</tbody></table></div>`:'<p class="field-hint">未读取到 RPM 输入，请观察实体风扇确认变化。</p>'}</section>`);
}
function renderLegacyMappings(){
  const history=state.config.legacy_pwm_candidates||[],open=$('#legacy-history')?.open;
  replacePanel($('#legacy-mappings'),history.length?`<details id="legacy-history" class="legacy-mapping-note" ${open?'open':''}><summary>旧版关联历史参考（${history.length} 路）</summary><p>以下记录不参与控制，不占用 PWM；请按本次手动测试重新确认。</p><div class="legacy-mapping-list">${history.map(candidate=>`<div><span>${esc(shortPwm(state.status.channels.find(channel=>channel.id===candidate.pwm_id))||candidate.pwm_id)}</span><span>${esc(candidate.former_group||'旧版关联')}</span></div>`).join('')}</div></details>`:'');
}
function setCurveDirty(){const changed=!state.curveDirty;state.curveDirty=true;$('#curve-dirty').textContent='有未保存修改';$('#curve-dirty').className='pill warning';$('#curve-error').textContent='';if(changed)updateMutationAvailability();}
function renderCurve(){if(!state.curve.length)return;$('#curve-dirty').textContent=state.curveDirty?'有未保存修改':'已保存';$('#curve-dirty').className=`pill ${state.curveDirty?'warning':'neutral'}`;$$('input[name="curve-source"]').forEach(el=>el.checked=el.value===state.source);replacePanel($('#global-sensor-exclusions'),sensorExclusionMarkup(state.source,state.ignoredTemperatureSensors,'global'));renderCurveGraph();renderCurvePoints();updateMutationAvailability();}
function sensorExclusionMarkup(source,ignored=[],scope='global'){
  const kinds=source==='max'?['cpu','disk']:[source],allowed=scope==='overview'?new Set(state.overviewSourceSensorIds):null;
  const sensors=(state.hardware?.temperature_sensors||[]).filter(sensor=>kinds.includes(sensor.kind)&&(!allowed||allowed.has(sensor.id)));
  if(!sensors.length)return '<p class="sensor-exclusion-empty">当前来源未发现可忽略的传感器节点。</p>';
  return '<div class="sensor-exclusion-list">'+sensors.map(sensor=>{const excluded=ignored.includes(sensor.id),included=scope==='overview'?'计入概览与走势':'参与温控';return `<label class="${excluded?'is-excluded':''}"><input type="checkbox" data-${scope}-ignore-sensor="${esc(sensor.id)}" data-focus="${esc(scope)}-${esc(sensor.id)}" aria-label="排除 ${esc(sensor.name)}；勾选后不参与对应类别的概览和温度走势" ${excluded?'checked':''}><span><strong>${esc(sensor.name)}</strong><small>${num(sensor.temperature,1)} °C · ${esc(sensor.source==='smartctl'?'SMART':'hwmon')}<span class="sensor-exclusion-state">${excluded?'已排除':included}</span></small></span></label>`;}).join('')+'</div>';
}
function renderCurveGraph(){const {width:w,height:h}=chartDimensions($('#curve-chart'));const pad={l:38,r:16,t:20,b:30};const base=chartBase(w,h,[25,50,75,100],[0,20,40,60,80,100].map(t=>({at:t/100,label:String(t)})),25,100,pad);const points=state.curve.map(p=>`${base.sx(p.temp/100)},${base.sy(p.percent)}`).join(' ');let body=base.body;body+=`<path d="M${base.sx(state.curve[0].temp/100)},${base.sy(25)} L${points.split(' ').join(' L')} L${base.sx(state.curve.at(-1).temp/100)},${base.sy(25)} Z" fill="#edf6ef"/><polyline points="${points}" fill="none" stroke="#338878" stroke-width="2.5" stroke-linejoin="round"/>`;state.curve.forEach((p,i)=>{body+=`<circle class="curve-handle" data-point="${i}" cx="${base.sx(p.temp/100)}" cy="${base.sy(p.percent)}" r="6" tabindex="${state.busy||state.authActive||!state.config?-1:0}" aria-disabled="${!!(state.busy||state.authActive||!state.config)}" role="slider" aria-label="节点 ${i+1}，温度 ${p.temp} 度，转速 ${p.percent}%" aria-valuemin="35" aria-valuemax="100" aria-valuenow="${p.percent}"><title>${p.temp}°C · ${p.percent}%</title></circle>`;});body+=`<text class="chart-text" x="${pad.l-8}" y="8" text-anchor="end">%</text>`;replacePanel($('#curve-chart'),`<svg viewBox="0 0 ${w} ${h}" aria-label="温控曲线，横轴 0 至 100°C，纵轴 25 至 100%">${body}</svg>`);}
function renderCurvePoints(){replacePanel($('#curve-points'),state.curve.map((p,i)=>`<div class="curve-point" data-point-index="${i}"><header><span>节点 ${i+1}</span><button class="icon-button" data-remove-point="${i}" aria-label="删除节点 ${i+1}" ${state.busy||state.authActive||state.curve.length<=2?'disabled':''}>${icon('close')}</button></header><label><input type="number" min="0" max="100" step="1" value="${p.temp}" data-curve-index="${i}" data-key="temp" aria-label="节点 ${i+1}温度" ${state.busy||state.authActive?'disabled':''}><span>°C</span></label><label><input type="number" min="35" max="100" step="1" value="${p.percent}" data-curve-index="${i}" data-key="percent" aria-label="节点 ${i+1}转速" ${state.busy||state.authActive?'disabled':''}><span>%</span></label></div>`).join(''));$('#add-point').disabled=state.busy||state.authActive||state.curve.length>=12;}
function validateCurve(curve=state.curve){if(curve.length<2||curve.length>12)return '曲线需要 2 至 12 个节点。';let lastTemp=-1,lastPct=0;for(const p of curve){if(!Number.isFinite(p.temp)||p.temp<0||p.temp>100||p.temp<=lastTemp)return '温度必须从低到高排列，且位于 0 至 100°C 之间。';if(!Number.isFinite(p.percent)||p.percent<35||p.percent>100||p.percent<lastPct)return '自动转速必须在 35% 至 100% 之间，且随温度保持或升高。';lastTemp=p.temp;lastPct=p.percent;}return '';}
function renderHardware(){
  const hardware=state.hardware;
  const groups=state.config?.fan_groups||[],history=state.config?.legacy_pwm_candidates||[];
  const deviceMarkup=(hardware?.devices||[]).map(device=>{
    const sensors=hardware.temperature_sensors.filter(sensor=>sensor.device_id===device.id),fans=hardware.fans.filter(sensor=>sensor.device_id===device.id),channels=state.status.channels.filter(channel=>channel.device_id===device.id);
    const rows=[
      ...sensors.map(sensor=>{const ignored=(state.config?.ignored_temperature_sensor_ids||[]).includes(sensor.id),kind={cpu:'CPU 温度',disk:'硬盘温度',other:'辅助温度'}[sensor.kind]||'温度',stateText=['cpu','disk'].includes(sensor.kind)?ignored?'已排除于概览与走势 · 原始读数保留':'参与概览与走势 · 全局曲线按来源选择':'';return '<tr><td>'+esc(sensor.name)+'</td><td class="'+(!ignored&&((sensor.kind==='disk'&&sensor.temperature>=60)||(sensor.kind==='cpu'&&sensor.temperature>=85))?'sensor-hot':'')+'">'+num(sensor.temperature,1)+' °C</td><td>'+kind+(stateText?' · '+stateText:'')+'</td></tr>'; }),
      ...fans.map(sensor=>{const group=groups.find(item=>item.rpm_id===sensor.id);const association=group?(group.rpm_verified?'已手动确认属于 '+group.name:'已选择 '+group.name+'，待手动确认'):'RPM 转速输入 · 未关联实体 FAN';return '<tr><td>'+esc(sensor.name)+'</td><td>'+num(sensor.rpm)+' RPM</td><td>测速输入 · '+esc(association)+'</td></tr>';}),
      ...channels.map(channel=>{
        const group=groups.find(item=>item.pwm_ids.includes(channel.id)),candidate=history.find(item=>item.pwm_id===channel.id),rpm=candidate?.rpm_id?(state.status.rpm_inputs||[]).find(input=>input.id===candidate.rpm_id):null;
        const association=group?(group.verified_pwm_ids.includes(channel.id)?'实体 FAN 组 '+group.name+' · 已手动验证':'实体 FAN 组 '+group.name+' · 待手动验证'):candidate?`未关联实体 FAN 组 · 历史记录指向 ${candidate.former_group||'旧版关联'} / ${rpm?.name||'未关联 RPM'}（仅供参考）`:'未关联实体 FAN 组';
        const recovery=channelPending(channel)?' · 待恢复':'';
        return '<tr><td>'+esc(channel.name)+'</td><td>'+(channel.ignored?'已忽略':num(channel.percent)+'%')+'</td><td>'+(channel.ignored?'已忽略 · 不读取、不控制、不做健康检查':'逻辑 PWM 输出 · '+esc(association)+recovery+' · '+esc(driverModes[channel.enable]||('模式 '+channel.enable))+' · '+(channel.writable?'可写':'只读'))+'</td></tr>';
      })
    ];
    const iconName=device.name==='drivetemp'?'disk':device.name==='coretemp'?'cpu':'chip';
    const body=rows.length?'<table class="hardware-table"><thead><tr><th scope="col">传感器 / 通道</th><th scope="col">当前读数</th><th scope="col">类型、实体 FAN 归属与驱动状态</th></tr></thead><tbody>'+rows.join('')+'</tbody></table>':'<p class="muted small-text">设备已发现，没有可读取的传感器。</p>';
    return '<section class="panel hardware-group"><div class="hardware-group-heading"><span data-icon="'+iconName+'"></span><div><h2>'+esc(device.name)+'</h2><p>'+esc(device.identity)+'</p></div></div>'+body+'</section>';
  }).join('');
  const emptyMarkup=!deviceMarkup?'<section class="panel"><div class="empty-state"><span data-icon="chip"></span><h3>未发现 hwmon 设备</h3><p>请确认传感器驱动已加载。随包驱动只支持已列明的主板与内核。</p></div></section>':'';
  $('#hardware-content').innerHTML='<section class="panel hardware-disk-panel"><div class="section-heading"><div><h2>硬盘温度</h2><p>优先显示硬盘 hwmon 传感器；缺少读数时，设备不在休眠的情况下尝试 SMART。</p></div></div><div id="hardware-disks" class="disk-list"></div></section>'+deviceMarkup+emptyMarkup;
  renderDiskList($('#hardware-disks'),hardware?.disks||[]);
  hydrate($('#hardware-content'));
}
function renderEvents(){const logs=[...state.logs].reverse().filter(l=>state.logLevel==='all'||l.level===state.logLevel);$('#events-list').innerHTML=logs.length?logs.map(l=>`<div class="event-row ${esc(l.level)}"><span data-icon="${l.level==='error'||l.level==='warning'?'alert':'check'}"></span><time datetime="${new Date(l.time*1000).toISOString()}">${dateTime(l.time)}</time><p>${esc(l.message)}</p></div>`).join(''):`<div class="empty-state"><span data-icon="list"></span><h3>${state.logLevel==='all'?'一切从这里开始':'没有此级别的记录'}</h3><p>${state.logLevel==='all'?'控制、配置保存与异常事件将记录在这里。':'可以切换至“全部”查看其他事件。'}</p></div>`;}
function renderSettings(){if(document.activeElement!==$('#poll-interval')){$('#poll-interval').value=String(state.config.poll_interval);if(!$('#poll-interval').value){const opt=document.createElement('option');opt.value=state.config.poll_interval;opt.textContent=`每 ${state.config.poll_interval} 秒`;$('#poll-interval').append(opt);$('#poll-interval').value=String(state.config.poll_interval);}}}
function operationSource(element){return element?{elementId:element.id,focus:element.dataset.focus,action:element.dataset.action,mode:element.dataset.mode,pwmAction:element.dataset.pwmAction,pwmIgnore:element.dataset.pwmIgnore,groupId:element.closest('[data-fan-control]')?.dataset.fanControl,pwmId:element.closest('[data-pwm]')?.dataset.pwm,formId:element.closest('form')?.id,tagName:element.tagName}:null;}
function operationMatches(element){
  const operation=state.operation;if(!state.busy||!operation)return false;
  if(operation.elementId)return element.id===operation.elementId;
  if(operation.focus)return element.dataset.focus===operation.focus;
  if(operation.groupId)return element.closest('[data-fan-control]')?.dataset.fanControl===operation.groupId&&element.dataset.action===operation.action&&element.dataset.mode===operation.mode;
  if(operation.pwmId)return element.closest('[data-pwm]')?.dataset.pwm===operation.pwmId&&(operation.pwmIgnore?element.dataset.pwmIgnore===operation.pwmIgnore:element.dataset.pwmAction===operation.pwmAction);
  if(operation.formId)return element.closest('form')?.id===operation.formId&&element.tagName===operation.tagName;
  return false;
}
async function mutation(path,body,success,element){if(!state.online||state.authActive||!state.status||!state.config){const error=new Error('当前未连接服务，恢复连接后才能保存或控制风扇。');toast(error.message,true);throw error;}if(state.busy)return;endDrag();state.busy=true;state.operation=operationSource(element);if(body?.id)delete state.actionErrors[body.id];if(body?.pwm_id)delete state.actionErrors[body.pwm_id];updateMutationAvailability();try{const result=await api(path,body);if(result.channels)state.status=result;if(success)toast(success);await refresh();return result;}catch(error){if(body?.id)state.actionErrors[body.id]=error.message;if(body?.pwm_id)state.actionErrors[body.pwm_id]=error.message;if(['hardware_error','operation_failed'].includes(error.code))await refresh();toast(error.message,true);throw error;}finally{state.busy=false;state.operation=null;if(state.page==='control')renderControl();updateMutationAvailability();hydrate($('#workspace'));}}

function updateMutationAvailability(){
  const blocked=!state.online||state.authActive||state.busy||!state.status||!state.config;
  for(const el of $$('#fan-group-controls button,#fan-group-controls input,#fan-group-controls select')){
    const card=el.closest('[data-fan-control]'),group=state.status?.fan_groups?.find(item=>item.id===card?.dataset.fanControl);if(!group||!state.config){el.disabled=blocked;continue;}
    const action=el.dataset.action,reason=fanControlReason(group),cfg=currentFanConfig(group.id),active=groupHasActiveOutput(cfg)||group.testing;
    if(action==='toggle-settings')el.disabled=state.authActive;
    else if(action==='mode'||action==='apply-duty'||action==='duty'||action==='duty-number')el.disabled=blocked||!!reason;
    else if(action==='release')el.disabled=blocked||(!group.owned&&!channelPending(group));
    else if(action==='delete-group')el.disabled=blocked||group.owned||channelPending(group)||group.testing;
    else if(el.dataset.edit==='rpm_id')el.disabled=blocked||active;
    else if(el.dataset.edit==='rpm_verified')el.disabled=blocked||active||!fanEditor(cfg).rpm_id;
    else if(action==='custom-remove')el.disabled=blocked||fanEditor(cfg).curve.length<=2;
    else if(action==='custom-add')el.disabled=blocked||fanEditor(cfg).curve.length>=12;
    else el.disabled=blocked;
  }
  for(const el of $$('#pwm-interfaces button,#pwm-interfaces input,#pwm-interfaces select')){
    const channel=state.status?.channels.find(item=>item.id===el.closest('[data-pwm]')?.dataset.pwm);if(!channel||!state.config){el.disabled=blocked;continue;}
    const action=el.dataset.pwmAction,assigned=state.config.fan_groups.find(group=>group.pwm_ids.includes(channel.id));
    if(el.dataset.pwmIgnore){const currentlyIgnored=(state.config.ignored_pwm_ids||[]).includes(channel.id),pending=channelPending(channel)||(state.status.pending_recovery_ids||[]).includes(channel.id),testing=state.status.pwm_test?.id===channel.id,activelyOwned=channel.owned&&!pending;el.disabled=blocked||(!currentlyIgnored&&(activelyOwned||testing));}
    else if(action==='test')el.disabled=blocked||!!pwmUnavailable(channel);
    else if(action==='map'||action==='remove-map')el.disabled=blocked||!!pwmUnavailable(channel)||!!(assigned&&groupHasActiveOutput(assigned));
    else if(action==='save-map')el.disabled=blocked||!state.mapping?.target||!state.mapping?.confirmed||!!pwmUnavailable(channel)||groupHasActiveOutput(currentFanConfig(state.mapping.target));
    else if(action==='cancel-map')el.disabled=state.authActive;
    else if(action==='retry')el.disabled=blocked;
    else el.disabled=blocked;
  }
  const curveEditingBlocked=state.busy||state.authActive||!state.config;
  for(const el of $$('input[name="curve-source"],#global-sensor-exclusions input,#curve-points input'))el.disabled=curveEditingBlocked;
  for(const el of $$('#curve-points [data-remove-point]'))el.disabled=curveEditingBlocked||state.curve.length<=2;
  $('#add-point').disabled=curveEditingBlocked||state.curve.length>=12;
  for(const el of $$('#curve-chart [data-point]')){el.setAttribute('aria-disabled',String(curveEditingBlocked));el.setAttribute('tabindex',curveEditingBlocked?'-1':'0');}
  for(const el of $$('[data-test-stop]'))el.disabled=blocked;
  for(const el of $$('[data-dismiss-test]'))el.disabled=state.authActive;
  $('#add-fan-group').disabled=blocked||(state.config?.fan_groups||[]).length>=32;
  $('#release-all').disabled=blocked||(!(state.status?.channels||[]).some(channel=>channel.owned&&!channel.ignored)&&!(state.status?.pending_recovery_ids||[]).length);
  $('#save-curve').disabled=blocked||!state.config||!state.curveDirty;
  $('#save-curve').dataset.dirty=String(state.curveDirty);
  $('#save-curve').setAttribute('aria-describedby','curve-dirty');
  $('#save-curve').title=state.curveDirty?'保存并应用当前全局曲线':'全局曲线已保存';
  $('#restore-default-curve').disabled=blocked||!state.config;
  $('#settings-form button[type="submit"]').disabled=blocked||!state.config;
  if($('#overview-source-dialog').open){
    const conflict=!!state.curveDirty,changed=overviewSourceChanged();
    $('#overview-source-conflict').hidden=!conflict;
    for(const el of $$('#overview-source-sensor-list input'))el.disabled=blocked||conflict;
    $('#overview-source-cancel').disabled=state.busy;
    $('#overview-source-save').disabled=blocked||conflict||!changed;
    $('#overview-source-save').classList.toggle('busy',state.busy&&state.operation?.elementId==='overview-source-save');
    if(state.busy&&state.operation?.elementId==='overview-source-save')$('#overview-source-save').setAttribute('aria-busy','true');else $('#overview-source-save').removeAttribute('aria-busy');
  }
  for(const el of $$('#alarm-region [data-alarm-action="apply"]'))el.disabled=state.authActive||state.busy;
  for(const el of $$('#workspace button,#workspace input,#workspace select,#suggestion-form button')){const pending=operationMatches(el);el.classList.toggle('busy',pending);if(pending)el.setAttribute('aria-busy','true');else el.removeAttribute('aria-busy');}
  for(const el of $$('[data-fan-control],[data-pwm]')){const pending=state.busy&&((state.operation?.groupId&&el.dataset.fanControl===state.operation.groupId)||(state.operation?.pwmId&&el.dataset.pwm===state.operation.pwmId));if(pending)el.setAttribute('aria-busy','true');else el.removeAttribute('aria-busy');}
  updateSuggestionAvailability();
}
function chartDimensions(element){
  const rect=element.getBoundingClientRect();
  return {width:Math.max(180,Math.round(rect.width||element.clientWidth||320)),height:Math.max(140,Math.round(rect.height||element.clientHeight||205))};
}

function download(name,value){const blob=new Blob([JSON.stringify(value,null,2)],{type:'application/json;charset=utf-8'});const href=URL.createObjectURL(blob);const a=document.createElement('a');a.href=href;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(href),1000);}

hydrate();
$('#toast-region').setAttribute('aria-atomic','false');
$('#toast-region').setAttribute('aria-relevant','additions');
$$('[data-window]').forEach(button=>button.setAttribute('aria-pressed',String(Number(button.dataset.window)===state.window)));
$$('[data-level]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.level===state.logLevel)));
setSidebar();
$('#auth-form').addEventListener('submit',async event=>{event.preventDefault();const password=$('#auth-password').value;$('#auth-error').textContent='';if(state.setup&&password.length<10){$('#auth-error').textContent='请使用至少 10 个字符。';return;}if(state.setup&&password!==$('#auth-confirm').value){$('#auth-error').textContent='两次输入的密码不一致，请重新确认。';return;}const button=$('#auth-submit');button.disabled=true;button.classList.add('busy');button.setAttribute('aria-busy','true');try{const result=await api(state.setup?'/api/setup':'/api/login',{password});state.csrf=result.csrf_token;$('#auth-password').value='';$('#auth-confirm').value='';await openApplication();}catch(error){$('#auth-error').textContent=error.message;}finally{button.disabled=false;button.classList.remove('busy');button.removeAttribute('aria-busy');}});
$('#toggle-password').addEventListener('click',()=>{const input=$('#auth-password');input.type=input.type==='password'?'text':'password';$('#toggle-password').setAttribute('aria-label',input.type==='password'?'显示密码':'隐藏密码');});
$('#logout').addEventListener('click',async()=>{try{await api('/api/logout',{});state.status=null;showAuth({setup_required:false});}catch(error){toast(error.message,true);}});
$('#alarm-region').addEventListener('click',event=>{
  const button=event.target.closest('[data-alarm-action]');if(!button||button.disabled)return;
  const code=button.closest('[data-alarm-code]').dataset.alarmCode;
  if(button.dataset.alarmAction==='ignore'){
    state.ignoredAlarms.add(code);saveIgnoredAlarms();renderShared();
    toast('本次提醒已忽略，风扇设置保持不变');$('#workspace').focus({preventScroll:true});
  }else openSuggestion(code,button);
});
$$('[data-overview-source-edit]').forEach(button=>button.addEventListener('click',event=>openOverviewSourceDialog(event.currentTarget,event.currentTarget.dataset.overviewSourceEdit)));
$('#history-series-open').addEventListener('click',()=>{renderHistorySeriesDialog();$('#history-series-dialog').showModal();});
$('#history-series-legend').addEventListener('click',event=>{
  const sensor=event.target.closest('[data-history-legend-sensor]'),mean=event.target.closest('[data-history-legend-mean]');
  if(sensor){const id=sensor.dataset.historyLegendSensor;if(state.hiddenHistorySensors.has(id))state.hiddenHistorySensors.delete(id);else state.hiddenHistorySensors.add(id);saveHiddenHistorySensors();renderHistory();return;}
  if(mean){const kind=mean.dataset.historyLegendMean;if(state.hiddenHistoryAverages.has(kind))state.hiddenHistoryAverages.delete(kind);else state.hiddenHistoryAverages.add(kind);saveHiddenHistoryAverages();renderHistory();}
});
$('#history-chart-frame').addEventListener('pointermove',event=>{if(event.pointerType==='touch')return;historyHoverPosition={x:event.clientX,y:event.clientY};updateHistoryHover(event.clientX,event.clientY);});
$('#history-chart-frame').addEventListener('pointerleave',()=>{historyHoverPosition=null;$('#history-hover-overlay').innerHTML='';$('#history-tooltip').hidden=true;});
$('#history-series-dialog').addEventListener('change',event=>{
  const sensor=event.target.closest('[data-history-sensor-toggle]');
  if(sensor){const id=sensor.dataset.historySensorToggle;if(sensor.checked)state.hiddenHistorySensors.delete(id);else state.hiddenHistorySensors.add(id);saveHiddenHistorySensors();renderHistory();return;}
  const mean=event.target.closest('[data-history-mean-toggle]');
  if(mean){const kind=mean.dataset.historyMeanToggle;if(mean.checked)state.hiddenHistoryAverages.delete(kind);else state.hiddenHistoryAverages.add(kind);saveHiddenHistoryAverages();renderHistory();}
});
$('#history-series-dialog').addEventListener('click',event=>{
  const bulk=event.target.closest('[data-history-sensors-all]');if(!bulk)return;
  for(const sensor of historySeriesList()){if(bulk.dataset.historySensorsAll==='on')state.hiddenHistorySensors.delete(sensor.id);else state.hiddenHistorySensors.add(sensor.id);}
  saveHiddenHistorySensors();renderHistory();renderHistorySeriesDialog();
});
$('#workspace').addEventListener('click',event=>{
  const diskButton=event.target.closest('[data-disk-ignore]');if(!diskButton||diskButton.disabled)return;
  const disk=(state.hardware?.disks||[]).find(item=>item.id===diskButton.dataset.diskIgnore);if(!disk)return;
  const sensors=diskTemperatureSensors(disk);openOverviewSourceDialog(diskButton,'disk',sensors.map(sensor=>sensor.id),disk.model||disk.name);
});
$('#overview-source-cancel').addEventListener('click',()=>{if(!state.busy)closeOverviewSourceDialog();});
$('#overview-source-dialog').addEventListener('cancel',event=>{event.preventDefault();if(!state.busy)closeOverviewSourceDialog();});
$('#overview-source-sensor-list').addEventListener('change',event=>{
  const input=event.target.closest('[data-overview-ignore-sensor]');if(!input||state.busy||state.authActive||state.curveDirty)return;
  const id=input.dataset.overviewIgnoreSensor,ids=new Set(state.overviewSourceDraft||[]);if(input.checked)ids.add(id);else ids.delete(id);state.overviewSourceDraft=[...ids];
  const label=input.closest('label');label?.classList.toggle('is-excluded',input.checked);const stateLabel=$('.sensor-exclusion-state',label);if(stateLabel)stateLabel.textContent=input.checked?'已排除':'计入概览与走势';$('#overview-source-error').textContent='';updateMutationAvailability();
});
$('#overview-source-form').addEventListener('submit',async event=>{
  event.preventDefault();const button=$('#overview-source-save');if(button.disabled||state.busy||!state.overviewSourceDraft)return;
  if(state.curveDirty){$('#overview-source-error').textContent='全局曲线有未保存修改，请先处理后再编辑来源忽略项。';return;}
  const ignored_temperature_sensor_ids=overviewSourcePayload();if(sameIdSet(ignored_temperature_sensor_ids,state.config.ignored_temperature_sensor_ids||[]))return;
  try{const result=await mutation('/api/config',{ignored_temperature_sensor_ids},'温度来源忽略设置已保存',button);if(result)closeOverviewSourceDialog();}
  catch(error){$('#overview-source-error').textContent=error.message;}
});
$('#suggestion-channel').addEventListener('change',renderSuggestion);
$('#suggestion-cancel').addEventListener('click',()=>{if(!state.busy)closeSuggestion();});
$('#suggestion-dialog').addEventListener('cancel',event=>{event.preventDefault();if(!state.busy)closeSuggestion();});
$('#suggestion-form').addEventListener('submit',async event=>{
  event.preventDefault();if(!state.suggestion||$('#suggestion-submit').disabled)return;
  if(state.suggestion.kind!=='control'){
    const page=state.suggestion.kind==='hardware'?'hardware':state.suggestion.kind==='events'?'events':'control';
    closeSuggestion(false);location.hash=page;navigate(page);$('#workspace').focus();return;
  }
  const reason=suggestionUnavailable();if(reason){$('#suggestion-error').textContent=reason;return;}
  const group=selectedSuggestionChannel(),id=group.id;
  try{
    const result=await mutation('/api/control',{id,mode:'auto'},null,$('#suggestion-submit'));
    if(!result)return;
    renderShared();renderPage();
    const actual=state.status?.fan_groups.find(item=>item.id===id);
    if(!actual?.owned||actual.mode!=='auto'||actual.error){throw new Error('未确认建议方案已生效，请检查所选 FAN 组及事件记录。');}
    closeSuggestion();toast(channelProtected(actual)?'建议已应用；异常状态按 50% 兜底':'建议已应用；所选 FAN 组已启用自动调速');
  }catch(error){$('#suggestion-error').textContent=error.message;}
});
$('#refresh').addEventListener('click',()=>refresh());$('#retry').addEventListener('click',()=>refresh());$('#rescan').addEventListener('click',async()=>{await refresh();if(state.online)toast('已重新扫描设备');});$('#initial-retry').addEventListener('click',initialize);
window.addEventListener('hashchange',()=>navigate(location.hash.slice(1)||'overview'));
$('#menu-toggle').addEventListener('click',()=>{const open=!$('#sidebar').classList.contains('is-open');setSidebar(open);if(open)$('#sidebar .nav-link.active')?.focus();});
document.addEventListener('click',event=>{if(mobileNavigation.matches&&$('#sidebar').classList.contains('is-open')&&!$('#sidebar').contains(event.target)&&!$('#menu-toggle').contains(event.target))setSidebar();});
document.addEventListener('keydown',event=>{if(event.key==='Escape'&&mobileNavigation.matches&&$('#sidebar').classList.contains('is-open')){event.preventDefault();setSidebar(false,true);}});
mobileNavigation.addEventListener('change',()=>setSidebar(false,mobileNavigation.matches&&$('#sidebar').contains(document.activeElement)));
$('#sidebar').addEventListener('click',event=>{if(!mobileNavigation.matches)return;const link=event.target.closest('a[href^="#"]');if(!link)return;event.preventDefault();const route=link.getAttribute('href').slice(1);if(location.hash!==`#${route}`)location.hash=route;navigate(route);});
let sectionScrollFrame;
window.addEventListener('scroll',()=>{if(state.page!=='control')return;cancelAnimationFrame(sectionScrollFrame);sectionScrollFrame=requestAnimationFrame(()=>{let active='global-curve';for(const id of ['global-curve','fans','pwm'])if(document.getElementById(id).getBoundingClientRect().top<=160)active=id;setControlJump(active);});},{passive:true});
$$('[data-window]').forEach(el=>el.addEventListener('click',async()=>{
  const requested=Number(el.dataset.window);if(requested===state.window)return;
  const previous=state.window;state.window=requested;$$('[data-window]').forEach(button=>{const selected=Number(button.dataset.window)===requested;button.classList.toggle('selected',selected);button.setAttribute('aria-pressed',String(selected));});
  if(!state.status)return;
  const request=++state.historyRequest;state.historyLoading=requested;renderHistory();
  try{const result=await api(`/api/history?minutes=${requested}`);if(request!==state.historyRequest||state.window!==requested)return;state.history=result.items||[];state.historySpanSeconds=Number(result.available_span_seconds)||0;state.historyLoading=null;renderHistory();}
  catch(error){if(request!==state.historyRequest)return;state.window=previous;state.historyLoading=null;$$('[data-window]').forEach(button=>{const selected=Number(button.dataset.window)===previous;button.classList.toggle('selected',selected);button.setAttribute('aria-pressed',String(selected));});renderHistory();toast(`切换历史范围失败：${error.message}`,true);}
}));
$$('[data-level]').forEach(el=>el.addEventListener('click',()=>{state.logLevel=el.dataset.level;$$('[data-level]').forEach(b=>{b.classList.toggle('selected',b===el);b.setAttribute('aria-pressed',String(b===el));});renderEvents();hydrate($('#events-list'));}));
function newFanGroup(){const suffix=Array.from(crypto.getRandomValues(new Uint8Array(12)),value=>value.toString(16).padStart(2,'0')).join('');return {id:`fan-${suffix}`,name:'新建 FAN',pwm_ids:[],verified_pwm_ids:[],rpm_id:null,rpm_verified:false,curve_mode:'global',temperature_source:state.config.temperature_source,ignored_temperature_sensor_ids:[],curve:state.config.curve.map(point=>({...point}))};}
async function addFanGroup(button){const groups=state.config?.fan_groups||[];if(groups.length>=32){toast('FAN 最多 32 个。',true);return;}const next=newFanGroup();try{await mutation('/api/config',{fan_groups:[...groups,next]},'已添加 FAN，可设置名称并关联 PWM',button);state.openSettings.add(next.id);renderControl();const card=$$('[data-fan-control]').find(item=>item.dataset.fanControl===next.id);if(card){card.scrollIntoView({block:'nearest',behavior:reducedMotion.matches?'instant':'smooth'});$('[data-edit="name"]',card)?.focus({preventScroll:true});animateSurface(card,'disclosure');}}catch{}}
$('#add-fan-group').addEventListener('click',event=>addFanGroup(event.currentTarget));
$('#fan-group-controls').addEventListener('input',event=>{
  const input=event.target,id=input.closest('[data-fan-control]')?.dataset.fanControl;if(!id)return;
  if(input.dataset.action==='duty'||input.dataset.action==='duty-number'){
    state.drafts[id]=input.value===''?NaN:Number(input.value);const card=input.closest('[data-fan-control]'),other=card.querySelector(`[data-action="${input.dataset.action==='duty'?'duty-number':'duty'}"]`);if(other)other.value=input.value;updateManualDraftState(card,id);return;
  }
  const cfg=currentFanConfig(id),draft=fanEditor(cfg);
  if(input.dataset.edit){draft[input.dataset.edit]=input.type==='checkbox'?input.checked:input.value;if(input.dataset.edit==='rpm_id')draft.rpm_verified=false;draft.dirty=true;draft.error='';}
  if(input.dataset.groupIgnoreSensor){const id=input.dataset.groupIgnoreSensor,current=new Set(draft.ignored_temperature_sensor_ids);if(input.checked)current.add(id);else current.delete(id);draft.ignored_temperature_sensor_ids=[...current];draft.dirty=true;draft.error='';}
  if(input.dataset.customKey){draft.curve[Number(input.dataset.customIndex)][input.dataset.customKey]=input.value===''?NaN:Number(input.value);draft.dirty=true;draft.error='';}
  const label=$('.settings-save-state',input.closest('[data-fan-control]'));if(label)label.textContent='有未保存修改';
});
$('#fan-group-controls').addEventListener('change',event=>{if(['curve_mode','rpm_id','temperature_source'].includes(event.target.dataset.edit)||event.target.dataset.groupIgnoreSensor){renderFanGroupControls();updateMutationAvailability();}});
$('#fan-group-controls').addEventListener('keydown',event=>{if(event.key==='Enter'&&event.target.dataset.action==='duty-number'){event.preventDefault();const button=event.target.closest('[data-fan-control]').querySelector('[data-action="apply-duty"]');if(button&&!button.disabled)button.click();}});
function insertCurvePoint(curve){let index=0,gap=0;for(let i=0;i<curve.length-1;i++){const difference=curve[i+1].temp-curve[i].temp;if(difference>gap){index=i;gap=difference;}}if(gap<2)return false;const a=curve[index],b=curve[index+1];curve.splice(index+1,0,{temp:Math.round((a.temp+b.temp)/2),percent:Math.round((a.percent+b.percent)/2)});return true;}
$('#fan-group-controls').addEventListener('click',async event=>{
  const button=event.target.closest('button[data-action]');if(!button||button.disabled)return;
  if(button.dataset.action==='add-group'){await addFanGroup(button);return;}
  if(button.dataset.action==='toggle-settings'){const id=button.closest('[data-fan-control]')?.dataset.fanControl,body=button.closest('[data-fan-control]')?.querySelector('.fan-settings-body');if(!id||!body)return;const open=!state.openSettings.has(id);if(open)state.openSettings.add(id);else state.openSettings.delete(id);setDisclosure(body,button,open);return;}
  const id=button.closest('[data-fan-control]')?.dataset.fanControl,group=state.status.fan_groups.find(item=>item.id===id),cfg=currentFanConfig(id);if(!group||!cfg)return;
  const action=button.dataset.action,draft=fanEditor(cfg);
  if(action==='mode'&&button.dataset.mode==='manual'){state.modeDrafts[id]='manual';state.drafts[id]=state.drafts[id]??group.saved_percent??50;renderControl();updateMutationAvailability();const card=$$('[data-fan-control]').find(item=>item.dataset.fanControl===id);animateSurface(card&&$('.manual-control',card),'disclosure');return;}
  if(action==='custom-add'){if(!insertCurvePoint(draft.curve)){draft.error='节点间距不足，请先调整温度。';}else draft.dirty=true;renderControl();return;}
  if(action==='custom-remove'){draft.curve.splice(Number(button.dataset.index),1);draft.dirty=true;renderControl();return;}
  if(action==='save-group'){
    if(!draft.name.trim()){draft.error='请填写 FAN 名称。';renderControl();return;}
    const error=draft.curve_mode==='custom'?validateCurve(draft.curve):'';if(error){draft.error=error;renderControl();return;}
    const patch={name:draft.name.trim(),rpm_id:draft.rpm_id||null,rpm_verified:!!draft.rpm_id&&draft.rpm_verified,curve_mode:draft.curve_mode,temperature_source:draft.temperature_source,ignored_temperature_sensor_ids:[...draft.ignored_temperature_sensor_ids],curve:draft.curve.map(point=>({...point}))};
    try{await mutation('/api/config',{fan_groups:state.config.fan_groups.map(item=>item.id===id?{...item,...patch}:item)},'FAN 设置已保存',button);delete state.fanEditors[id];renderControl();}catch(error){draft.error=error.message;renderControl();}return;
  }
  if(action==='delete-group'){const ignored=state.config.ignored_rpm_ids||[];const ignoredRpm=group.rpm_id&&/^fan-[a-f0-9]{20}$/.test(group.id)?[...new Set([...ignored,group.rpm_id])]:ignored;try{await mutation('/api/config',{fan_groups:state.config.fan_groups.filter(item=>item.id!==id),ignored_rpm_ids:ignoredRpm},'风扇已删除；PWM 输出保持当前状态',button);delete state.fanEditors[id];state.openSettings.delete(id);renderControl();}catch{}return;}
  let path='/api/control',body,success;
  if(action==='mode'){const mode=button.dataset.mode;state.modeDrafts[id]=mode;body={id,mode};success=`${group.name} 已启用${modeNames[mode]}`;}
  else if(action==='apply-duty'){const percent=state.drafts[id]??group.saved_percent??50;if(!Number.isInteger(percent)||percent<25||percent>100){toast('手动占空比请输入 25 至 100 之间的整数。',true);return;}body={id,mode:'manual',percent};success=`${group.name} 已应用 ${percent}% 手动占空比`;state.modeDrafts[id]='manual';}
  else if(action==='release'){path='/api/release';body={id};success=`${group.name} 已释放接管并恢复原始状态`;delete state.modeDrafts[id];}
  else return;
  try{await mutation(path,body,success,button);}catch{}
});
$('#pwm-interfaces').addEventListener('change',async event=>{
  const toggle=event.target.closest('[data-pwm-ignore]');
  if(toggle){const id=toggle.dataset.pwmIgnore,current=new Set(state.config.ignored_pwm_ids||[]);if(toggle.checked)current.add(id);else current.delete(id);state.mapping=null;try{await mutation('/api/config',{ignored_pwm_ids:[...current]},toggle.checked?'PWM 已忽略：停止读取、检查、测试和控制；恢复记录仍保留':'PWM 已解除忽略；可恢复监控并手动重试恢复',toggle);}catch{toggle.checked=(state.config.ignored_pwm_ids||[]).includes(id);}return;}
  if(!state.mapping||!event.target.dataset.mapping)return;const key=event.target.dataset.mapping;state.mapping[key]=event.target.type==='checkbox'?event.target.checked:event.target.value;if(key==='target')state.mapping.confirmed=false;state.mapping.error='';renderPwmInterfaces();updateMutationAvailability();
});
$('#pwm-interfaces').addEventListener('click',async event=>{
  const button=event.target.closest('button[data-pwm-action]');if(!button||button.disabled)return;
  const id=button.closest('[data-pwm]').dataset.pwm,channel=state.status.channels.find(item=>item.id===id),groups=state.config.fan_groups,assigned=groups.find(group=>group.pwm_ids.includes(id)),action=button.dataset.pwmAction;
  if(action==='map'){state.mapping={id,target:assigned?.id||'',confirmed:false,error:''};renderPwmInterfaces();updateMutationAvailability();const row=$$('[data-pwm]').find(item=>item.dataset.pwm===id),editor=row&&$('.pwm-mapping-editor',row);if(editor){animateSurface(editor,'disclosure');$('[data-mapping="target"]',editor)?.focus();}return;}
  if(action==='cancel-map'){state.mapping=null;renderPwmInterfaces();const row=$$('[data-pwm]').find(item=>item.dataset.pwm===id);if(row)$('[data-pwm-action="map"]',row)?.focus({preventScroll:true});return;}
  if(action==='test'||action==='stop'){try{await mutation('/api/pwm-test',{id,action:action==='test'?'start':'stop'},action==='test'?`${shortPwm(channel)} 已开始 10 秒测试`:'已结束测试并请求恢复原始状态',button);if(action==='test')$('#pwm-test-feedback').scrollIntoView({block:'nearest',behavior:reducedMotion.matches?'instant':'smooth'});}catch{}return;}
  if(action==='retry'){try{await mutation('/api/release',{pwm_id:id},`${shortPwm(channel)} 已恢复原始状态`,button);}catch{}return;}
  if(action==='save-map'||action==='remove-map'){
    const mapping=state.mapping;if(action==='save-map'&&(!mapping?.target||!mapping.confirmed))return;
    const target=action==='save-map'?mapping.target:null;
    const next=groups.map(group=>{const pwm=group.pwm_ids.filter(value=>value!==id),verified=group.verified_pwm_ids.filter(value=>value!==id);if(group.id===target){pwm.push(id);verified.push(id);}return {...group,pwm_ids:pwm,verified_pwm_ids:verified};});
    try{await mutation('/api/config',{fan_groups:next},action==='save-map'?`${shortPwm(channel)} 已添加到 ${groups.find(group=>group.id===target).name}`:'PWM 与 FAN 的关联已解除',button);state.mapping=null;renderControl();}catch(error){if(state.mapping)state.mapping.error=error.message;renderPwmInterfaces();}return;
  }
});
$('#pwm-test-feedback').addEventListener('click',async event=>{const stop=event.target.closest('[data-test-stop]');if(stop){try{await mutation('/api/pwm-test',{id:stop.dataset.testStop,action:'stop'},'已结束测试并请求恢复原始状态',stop);}catch{}}const dismiss=event.target.closest('[data-dismiss-test]');if(dismiss){state.dismissedTest=state.status.pwm_test_result?.ended_at;$('#pwm-test-feedback').innerHTML='';}});
$('#release-all').addEventListener('click',async event=>{try{await mutation('/api/release',{},'全部已接管 FAN 组均已恢复原始 PWM 状态',event.currentTarget);}catch{}});
$$('input[name="curve-source"]').forEach(el=>el.addEventListener('change',()=>{if(state.busy||state.authActive)return;state.source=el.value;setCurveDirty();replacePanel($('#global-sensor-exclusions'),sensorExclusionMarkup(state.source,state.ignoredTemperatureSensors,'global'));updateMutationAvailability();}));
$('#global-sensor-exclusions').addEventListener('change',event=>{const input=event.target.closest('[data-global-ignore-sensor]');if(!input||state.busy||state.authActive)return;const id=input.dataset.globalIgnoreSensor,current=new Set(state.ignoredTemperatureSensors);if(input.checked)current.add(id);else current.delete(id);state.ignoredTemperatureSensors=[...current];setCurveDirty();replacePanel($('#global-sensor-exclusions'),sensorExclusionMarkup(state.source,state.ignoredTemperatureSensors,'global'));updateMutationAvailability();});
$('#curve-points').addEventListener('input',event=>{const input=event.target;if(!input.dataset.key||state.busy||state.authActive)return;state.curve[Number(input.dataset.curveIndex)][input.dataset.key]=input.value===''?NaN:Number(input.value);setCurveDirty();if(state.curve.every(p=>Number.isFinite(p.temp)&&Number.isFinite(p.percent)))renderCurveGraph();});
$('#restore-default-curve').addEventListener('click',()=>{if(state.busy||state.authActive)return;state.curve=recommendedCurve.map(point=>({...point}));setCurveDirty();renderCurve();toast('已恢复推荐曲线到编辑区；点击“保存全局曲线”后才会生效。');});
$('#curve-points').addEventListener('click',event=>{const button=event.target.closest('[data-remove-point]');if(!button||button.disabled||state.busy||state.authActive||state.curve.length<=2)return;state.curve.splice(Number(button.dataset.removePoint),1);setCurveDirty();renderCurve();});
$('#add-point').addEventListener('click',()=>{if(state.busy||state.authActive||state.curve.length>=12)return;let bestIndex=0,bestGap=0;for(let i=0;i<state.curve.length-1;i++){const gap=state.curve[i+1].temp-state.curve[i].temp;if(gap>bestGap){bestGap=gap;bestIndex=i;}}if(bestGap<2){toast('现有节点之间没有足够空间，请先调整温度。',true);return;}const a=state.curve[bestIndex],b=state.curve[bestIndex+1];state.curve.splice(bestIndex+1,0,{temp:Math.round((a.temp+b.temp)/2),percent:Math.round((a.percent+b.percent)/2)});setCurveDirty();renderCurve();});
$('#save-curve').addEventListener('click',async event=>{if(state.busy||event.currentTarget.disabled)return;const error=validateCurve();if(error){$('#curve-error').textContent=error;return;}try{const result=await mutation('/api/config',{curve:state.curve,temperature_source:state.source,ignored_temperature_sensor_ids:state.ignoredTemperatureSensors},'温控曲线已保存并生效',event.currentTarget);if(!result)return;state.curveDirty=false;renderCurve();}catch(error){$('#curve-error').textContent=error.message;}});
let drag=null;
$('#curve-chart').addEventListener('pointerdown',event=>{const point=event.target.closest('[data-point]');if(!point||drag||state.busy||state.authActive)return;drag={index:Number(point.dataset.point),pointerId:event.pointerId};$('#curve-chart').setPointerCapture(event.pointerId);event.preventDefault();});
$('#curve-chart').addEventListener('pointermove',event=>{if(state.busy||state.authActive){endDrag();return;}if(!drag||event.pointerId!==drag.pointerId)return;const svg=$('#curve-chart svg'),rect=svg.getBoundingClientRect(),view=svg.viewBox.baseVal;const w=view.width,h=view.height;const x=(event.clientX-rect.left)/rect.width*w,y=(event.clientY-rect.top)/rect.height*h;const i=drag.index,prev=state.curve[i-1],next=state.curve[i+1];const temp=Math.round(Math.max(prev?prev.temp+1:0,Math.min(next?next.temp-1:100,(x-38)/(w-54)*100)));const percent=Math.round(Math.max(prev?prev.percent:35,Math.min(next?next.percent:100,25+(h-30-y)/(h-50)*75)));state.curve[i]={temp,percent};setCurveDirty();renderCurveGraph();renderCurvePoints();});
function endDrag(){const active=drag;drag=null;const chart=$('#curve-chart');if(active&&chart.hasPointerCapture(active.pointerId))chart.releasePointerCapture(active.pointerId);}$('#curve-chart').addEventListener('pointerup',endDrag);$('#curve-chart').addEventListener('pointercancel',endDrag);$('#curve-chart').addEventListener('lostpointercapture',endDrag);window.addEventListener('blur',endDrag);
$('#curve-chart').addEventListener('keydown',event=>{const point=event.target.closest('[data-point]');if(!point||!['ArrowUp','ArrowDown','ArrowLeft','ArrowRight'].includes(event.key))return;event.preventDefault();if(state.busy||state.authActive)return;const i=Number(point.dataset.point);const p=state.curve[i],prev=state.curve[i-1],next=state.curve[i+1];if(event.key==='ArrowUp')p.percent=Math.min(next?next.percent:100,p.percent+1);if(event.key==='ArrowDown')p.percent=Math.max(prev?prev.percent:35,p.percent-1);if(event.key==='ArrowRight')p.temp=Math.min(next?next.temp-1:100,p.temp+1);if(event.key==='ArrowLeft')p.temp=Math.max(prev?prev.temp+1:0,p.temp-1);setCurveDirty();renderCurveGraph();renderCurvePoints();$(`[data-point="${i}"]`,$('#curve-chart')).focus();});
$('#settings-form').addEventListener('submit',async event=>{event.preventDefault();try{await mutation('/api/config',{poll_interval:Number($('#poll-interval').value)},'采样间隔已保存',$('button',event.currentTarget));}catch{}});
$('#export-logs').addEventListener('click',()=>download(`fan-studio-events-${new Date().toISOString().slice(0,10)}.json`,{exported_at:new Date().toISOString(),demo:!!state.status?.demo,events:state.logs}));
$('#export-diagnostics').addEventListener('click',()=>download(`fan-studio-diagnostics-${new Date().toISOString().slice(0,10)}.json`,{exported_at:new Date().toISOString(),status:state.status,hardware:state.hardware,config:state.config,events:state.logs}));
document.addEventListener('visibilitychange',()=>{if(!document.hidden&&!state.authActive)refresh();});

let chartResizeFrame;
function redrawVisibleCharts(){
  cancelAnimationFrame(chartResizeFrame);
  chartResizeFrame=requestAnimationFrame(()=>{
    if(!state.status||state.authActive)return;
    if(state.page==='overview')renderHistory();
    if(state.page==='control'&&state.curve.length)renderCurveGraph();
  });
}
if(typeof ResizeObserver!=='undefined'){
  const chartObserver=new ResizeObserver(redrawVisibleCharts);
  chartObserver.observe($('#history-chart'));
  chartObserver.observe($('#curve-chart'));
}else window.addEventListener('resize',redrawVisibleCharts);

initialize();
