// 轉珠打怪 - 簡易 Match-3 + 回合制
// Author: Codex CLI

(function(){
  const ROWS = 5;
  const COLS = 6;
  const COLORS = 6; // 0..5
  const MIN_MATCH = 3;

  // 戰鬥設定
  const PLAYER_MAX_HP = 100;
  const ENEMY_BASE_HP = 120;
  const ENEMY_BASE_ATK = 14;
  const ORB_BASE_DMG = 6;

  // 技能設定
  const SKILLS = {
    heal: { cost: 25, heal: 30 },
    fire: { cost: 40, dmg: 50 },
    buff: { cost: 50, turns: 1, mult: 2 },
  };

  // 狀態
  const state = {
    board: [],
    selected: null, // {r,c}
    canInput: true,
    combo: 0,
    pendingDamage: 0,
    player: { hp: PLAYER_MAX_HP, maxHp: PLAYER_MAX_HP, sp: 0, buffTurns: 0, dmgMult: 1 },
    enemy: { hp: ENEMY_BASE_HP, maxHp: ENEMY_BASE_HP, atk: ENEMY_BASE_ATK, level: 1 },
    phase: 'player', // 'player' | 'resolving' | 'enemy'
  };

  // DOM 快取
  const el = {
    board: document.getElementById('board'),
    log: document.getElementById('log-list'),
    combo: document.getElementById('combo-count'),
    phase: document.getElementById('turn-phase'),
    pHpFill: document.getElementById('player-hp-fill'),
    pHpText: document.getElementById('player-hp-text'),
    pSpFill: document.getElementById('player-sp-fill'),
    pSpText: document.getElementById('player-sp-text'),
    eHpFill: document.getElementById('enemy-hp-fill'),
    eHpText: document.getElementById('enemy-hp-text'),
    eAtkText: document.getElementById('enemy-atk-text'),
    btnRestart: document.getElementById('btn-restart'),
    sHeal: document.getElementById('skill-heal'),
    sFire: document.getElementById('skill-fire'),
    sBuff: document.getElementById('skill-buff'),
  };

  // 工具
  const rand = (n)=> Math.floor(Math.random()*n);
  const clamp = (x,min,max)=> Math.max(min, Math.min(max,x));

  function log(msg, cls='info'){
    const div = document.createElement('div');
    div.className = `log-item ${cls}`;
    div.textContent = msg;
    el.log.prepend(div);
  }

  function setPhase(ph){
    state.phase = ph;
    el.phase.textContent = ph === 'player' ? '玩家行動' : (ph === 'resolving' ? '結算消除' : '敵人行動');
    updateSkillsAvailability();
  }

  // 棋盤
  function makeCell(r,c,val){
    return { r, c, val };
  }

  function initBoard(){
    state.board = [];
    for(let r=0;r<ROWS;r++){
      const row=[];
      for(let c=0;c<COLS;c++){
        let v;
        do{
          v = rand(COLORS);
        }while(c>=2 && row[c-1].val===v && row[c-2].val===v || r>=2 && state.board[r-1][c].val===v && state.board[r-2][c].val===v);
        row.push(makeCell(r,c,v));
      }
      state.board.push(row);
    }
  }

  function renderBoard(){
    el.board.innerHTML = '';
    el.board.style.setProperty('--rows', ROWS);
    el.board.style.setProperty('--cols', COLS);
    for(let r=0;r<ROWS;r++){
      for(let c=0;c<COLS;c++){
        const cell = state.board[r][c];
        const div = document.createElement('div');
        div.className = 'cell';
        div.setAttribute('role','gridcell');
        div.dataset.r = r;
        div.dataset.c = c;
        const orb = document.createElement('div');
        orb.className = `orb c-${cell.val}`;
        div.appendChild(orb);
        div.addEventListener('click', onCellClick);
        el.board.appendChild(div);
      }
    }
    updateSelection();
  }

  function updateSelection(){
    const nodes = el.board.querySelectorAll('.cell');
    nodes.forEach(n=>n.classList.remove('selected'));
    if(state.selected){
      const q = `.cell[data-r="${state.selected.r}"][data-c="${state.selected.c}"]`;
      const s = el.board.querySelector(q);
      if(s) s.classList.add('selected');
    }
  }

  function inBounds(r,c){
    return r>=0 && r<ROWS && c>=0 && c<COLS;
  }

  function isAdjacent(a,b){
    return Math.abs(a.r-b.r)+Math.abs(a.c-b.c)===1;
  }

  function swapCells(a,b){
    const tmp = state.board[a.r][a.c].val;
    state.board[a.r][a.c].val = state.board[b.r][b.c].val;
    state.board[b.r][b.c].val = tmp;
  }

  function onCellClick(e){
    if(!state.canInput || state.phase!=='player') return;
    const r = Number(e.currentTarget.dataset.r);
    const c = Number(e.currentTarget.dataset.c);
    const cur = { r, c };
    if(!state.selected){
      state.selected = cur;
      updateSelection();
      return;
    }
    if(r===state.selected.r && c===state.selected.c){
      state.selected = null;
      updateSelection();
      return;
    }
    if(!isAdjacent(state.selected, cur)){
      state.selected = cur;
      updateSelection();
      return;
    }
    // 嘗試交換
    state.canInput = false;
    swapCells(state.selected, cur);
    renderBoard();
    // 若無法形成消除，換回
    const matches = findMatches();
    if(matches.length===0){
      swapCells(state.selected, cur);
      renderBoard();
      log('沒有消除，交換無效', 'info');
      state.canInput = true;
      state.selected = null;
      updateSelection();
      return;
    }
    state.selected = null;
    updateSelection();
    setPhase('resolving');
    resolveMatches().then(()=>{
      // 玩家傷害結算
      const mult = state.player.buffTurns>0 ? SKILLS.buff.mult : 1;
      const total = Math.floor(state.pendingDamage * state.player.dmgMult * mult);
      state.pendingDamage = 0;
      if(total>0){
        damageEnemy(total);
        log(`造成傷害 ${total}`, 'dmg');
      }
      if(state.player.buffTurns>0){
        state.player.buffTurns -= 1;
        if(state.player.buffTurns===0) log('狂怒效果結束', 'info');
      }
      // 若敵已死，換新敵
      if(state.enemy.hp<=0){
        nextEnemy();
        setPhase('player');
        state.canInput = true;
        return;
      }
      // 敵人行動
      enemyTurn();
    });
  }

  // 找出所有消除組
  function findMatches(){
    const matches = [];
    // 水平
    for(let r=0;r<ROWS;r++){
      let streak=1;
      for(let c=1;c<=COLS;c++){
        if(c<COLS && state.board[r][c].val===state.board[r][c-1].val){
          streak++;
        }else{
          if(streak>=MIN_MATCH){
            const group=[];
            for(let k=c-streak;k<c;k++) group.push({r,c:k});
            matches.push(group);
          }
          streak=1;
        }
      }
    }
    // 垂直
    for(let c=0;c<COLS;c++){
      let streak=1;
      for(let r=1;r<=ROWS;r++){
        if(r<ROWS && state.board[r][c].val===state.board[r-1][c].val){
          streak++;
        }else{
          if(streak>=MIN_MATCH){
            const group=[];
            for(let k=r-streak;k<r;k++) group.push({r:k,c});
            matches.push(group);
          }
          streak=1;
        }
      }
    }
    // 合併座標
    const set = new Set();
    const uniq = [];
    for(const g of matches){
      const group=[];
      for(const {r,c} of g){
        const key = r+','+c;
        if(!set.has(key)){
          set.add(key);
          group.push({r,c});
        }
      }
      if(group.length>0) uniq.push(group);
    }
    return uniq;
  }

  function removeMatches(groups){
    // 計算傷害 & SP
    let removed = 0;
    for(const g of groups){
      removed += g.length;
    }
    const comboBonus = 1 + (state.combo * 0.25); // 每多 1 連擊 +25% 傷害
    const dmg = Math.floor(removed * ORB_BASE_DMG * comboBonus);
    state.pendingDamage += dmg;
    const spGain = Math.min(100 - state.player.sp, removed * 2);
    state.player.sp += spGain;
    // 移除
    for(const g of groups){
      for(const {r,c} of g){
        state.board[r][c].val = -1; // 空
      }
    }
    log(`消除 ${removed} 顆，暫存傷害 +${dmg}，SP+${spGain}`,'good');
  }

  function collapseAndRefill(){
    // 下落
    for(let c=0;c<COLS;c++){
      let write = ROWS-1;
      for(let r=ROWS-1;r>=0;r--){
        if(state.board[r][c].val!==-1){
          state.board[write][c].val = state.board[r][c].val;
          write--;
        }
      }
      while(write>=0){
        state.board[write][c].val = rand(COLORS);
        write--;
      }
    }
  }

  async function resolveMatches(){
    state.combo = 0;
    renderBoard();
    await sleep(120);
    while(true){
      const groups = findMatches();
      if(groups.length===0) break;
      state.combo++;
      el.combo.textContent = String(state.combo);
      removeMatches(groups);
      renderBoard();
      await sleep(120);
      collapseAndRefill();
      renderBoard();
      await sleep(120);
    }
  }

  function damageEnemy(amount){
    state.enemy.hp = clamp(state.enemy.hp - amount, 0, state.enemy.maxHp);
    updateHud();
  }

  function damagePlayer(amount){
    state.player.hp = clamp(state.player.hp - amount, 0, state.player.maxHp);
    updateHud();
  }

  function healPlayer(amount){
    state.player.hp = clamp(state.player.hp + amount, 0, state.player.maxHp);
    updateHud();
  }

  function nextEnemy(){
    state.enemy.level += 1;
    const scale = 1 + (state.enemy.level-1)*0.2;
    state.enemy.maxHp = Math.floor(ENEMY_BASE_HP * scale);
    state.enemy.hp = state.enemy.maxHp;
    state.enemy.atk = Math.floor(ENEMY_BASE_ATK * scale);
    log(`新魔物出現！等級 ${state.enemy.level}，HP ${state.enemy.maxHp}，ATK ${state.enemy.atk}`,'info');
    updateHud();
  }

  function enemyTurn(){
    setPhase('enemy');
    const atk = state.enemy.atk;
    damagePlayer(atk);
    log(`魔物對你造成 ${atk} 傷害！`,'dmg');
    if(state.player.hp<=0){
      gameOver(false);
      return;
    }
    setPhase('player');
    state.canInput = true;
  }

  function updateHud(){
    // Player HP
    const p = state.player;
    const pHpPct = Math.floor((p.hp/p.maxHp)*100);
    el.pHpFill.style.width = pHpPct+'%';
    el.pHpText.textContent = `${p.hp}/${p.maxHp}`;
    const spPct = Math.floor((p.sp/100)*100);
    el.pSpFill.style.width = spPct+'%';
    el.pSpText.textContent = `${p.sp}/100`;
    // Enemy
    const e = state.enemy;
    const eHpPct = Math.floor((e.hp/e.maxHp)*100);
    el.eHpFill.style.width = eHpPct+'%';
    el.eHpText.textContent = `${e.hp}/${e.maxHp}`;
    el.eAtkText.textContent = e.atk;
    updateSkillsAvailability();
  }

  function updateSkillsAvailability(){
    const sp = state.player.sp;
    const canUse = state.phase==='player' && state.canInput;
    el.sHeal.disabled = !(canUse && sp>=SKILLS.heal.cost);
    el.sFire.disabled = !(canUse && sp>=SKILLS.fire.cost);
    el.sBuff.disabled = !(canUse && sp>=SKILLS.buff.cost);
  }

  function spendSP(cost){
    state.player.sp = clamp(state.player.sp - cost, 0, 100);
    updateHud();
  }

  function useHeal(){
    if(state.phase!=='player'||!state.canInput) return;
    if(state.player.sp<SKILLS.heal.cost) return;
    spendSP(SKILLS.heal.cost);
    healPlayer(SKILLS.heal.heal);
    log(`施放治癒，回復 ${SKILLS.heal.heal} HP`,'good');
  }

  function useFire(){
    if(state.phase!=='player'||!state.canInput) return;
    if(state.player.sp<SKILLS.fire.cost) return;
    spendSP(SKILLS.fire.cost);
    damageEnemy(SKILLS.fire.dmg);
    log(`施放火球，造成 ${SKILLS.fire.dmg} 傷害！`,'dmg');
    if(state.enemy.hp<=0){
      nextEnemy();
    }
  }

  function useBuff(){
    if(state.phase!=='player'||!state.canInput) return;
    if(state.player.sp<SKILLS.buff.cost) return;
    spendSP(SKILLS.buff.cost);
    state.player.buffTurns = SKILLS.buff.turns;
    log('進入狂怒狀態：本回合傷害x2','good');
  }

  function gameOver(win){
    state.canInput = false;
    setPhase('enemy');
    if(win){
      log('你贏了！','good');
    }else{
      log('你被打倒了，遊戲結束','dmg');
    }
  }

  function restart(){
    state.player.hp = PLAYER_MAX_HP;
    state.player.sp = 0;
    state.player.buffTurns = 0;
    state.player.dmgMult = 1;
    state.enemy.level = 1;
    state.enemy.maxHp = ENEMY_BASE_HP;
    state.enemy.hp = ENEMY_BASE_HP;
    state.enemy.atk = ENEMY_BASE_ATK;
    state.pendingDamage = 0;
    state.selected = null;
    setPhase('player');
    state.canInput = true;
    initBoard();
    renderBoard();
    updateHud();
    el.combo.textContent = '0';
    el.log.innerHTML = '';
    log('遊戲開始！','info');
  }

  function sleep(ms){ return new Promise(r=>setTimeout(r,ms)); }

  // 綁定事件
  el.btnRestart.addEventListener('click', restart);
  el.sHeal.addEventListener('click', useHeal);
  el.sFire.addEventListener('click', useFire);
  el.sBuff.addEventListener('click', useBuff);

  // 初始化
  restart();
})();

