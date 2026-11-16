(() => {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const mock = {active: false, chrome: true, mode: 'browser'};
  const write = (id, text) => { $(id).textContent = text; };
  function status() {
    write('mock-status', mock.active ? '제어 중 · 예시' : '제어 대기');
    $('mock-status').classList.toggle('on', mock.active);
    write('mock-target', mock.mode === 'image' ? 'HAND 이미지 화면 · 예시' : mock.chrome ? 'Chrome 선택됨 · 예시' : '다른 앱 선택됨 · 예시');
    write('mock-target-detail', mock.mode === 'image' ? '앱 내부 명령만 적용합니다. 외부 키 입력은 보내지 않습니다.' : mock.chrome ? '제어 시작 후 손동작 하나가 단축키 한 번으로 연결됩니다.' : 'Chrome 창을 다시 선택하고 새 동작을 해주세요.');
    write('mock-camera-caption', mock.mode === 'image' ? '왼쪽 쓸기 → 이전 이미지' : '검지를 펴고 왼쪽으로 쓸어보세요.');
  }
  function reset() {
    mock.active = false; mock.chrome = true; mock.mode = 'browser';
    document.querySelectorAll('[data-mode]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.mode === mock.mode)));
    write('mock-gesture', '손동작 대기');
    write('mock-gesture-detail', 'V로 시작한 뒤 손을 잠깐 풀어주세요.');
    write('mock-command', '아직 전송 없음');
    write('mock-command-detail', '인식과 입력 전송 결과를 구분합니다.');
    write('mock-footer', '카메라 영상이 아닌 설계 일러스트입니다.'); status();
  }
  document.querySelectorAll('[data-view]').forEach(button => button.addEventListener('click', () => {
    const selected = button.dataset.view;
    if (selected === 'practice') { mock.active = false; status(); }
    document.querySelectorAll('[data-view]').forEach(b => b.setAttribute('aria-pressed', String(b === button)));
    document.querySelectorAll('.view').forEach(v => { v.hidden = v.id !== `view-${selected}`; });
  }));
  document.querySelectorAll('[data-mode]').forEach(button => button.addEventListener('click', () => {
    mock.mode = button.dataset.mode;
    document.querySelectorAll('[data-mode]').forEach(b => b.setAttribute('aria-pressed', String(b === button)));
    write('mock-gesture', '새 동작 대기'); write('mock-gesture-detail', '모드 전환 후 자세 해제 예시. 이전 동작은 재생하지 않습니다.');
    write('mock-command', '아직 실행 없음'); write('mock-command-detail', '이 모드의 새 동작을 기다립니다.'); status();
  }));
  $('mock-start').addEventListener('click', () => {
    const inPractice = !$('view-practice').hidden;
    if (inPractice) { write('mock-status', '연습 중 · 실제 입력 없음'); return; }
    mock.active = true; status(); write('mock-gesture', 'V 인식 → 자세 해제');
    write('mock-gesture-detail', '예시에서 600ms 유지와 180ms 자세 해제를 완료했습니다.');
    write('mock-footer', '예시 상태입니다. 실제 카메라·키 입력은 발생하지 않습니다.');
  });
  $('mock-stop').addEventListener('click', () => {
    mock.active = false; status(); write('mock-gesture', '중단 요청');
    write('mock-gesture-detail', '중단 버튼으로 제어 대기 상태가 됐습니다.');
    write('mock-footer', '최근 중단 이유: 중단 버튼 · 설계 예시');
  });
  $('mock-back').addEventListener('click', () => {
    write('mock-gesture', '검지 왼쪽 쓸기'); write('mock-gesture-detail', '임계값을 충족한 확정 동작 예시입니다.');
    if (!mock.active) { write('mock-command', '전송 보류'); write('mock-command-detail', '제어 대기 중입니다. V로 먼저 시작하세요.'); }
    else if (mock.mode === 'image') { write('mock-command', '이전 이미지 적용 · 예시'); write('mock-command-detail', '앱 내부 PREV_IMAGE. OS 키 전송 없음.'); }
    else if (!mock.chrome) { write('mock-command', '전송 보류'); write('mock-command-detail', '대상 불일치: Chrome 창을 선택하세요.'); }
    else { write('mock-command', 'Alt + ← 전송 · 예시'); write('mock-command-detail', '실제 웹페이지 이동은 별도 실기 검증으로 확인합니다.'); }
  });
  $('mock-block').addEventListener('click', () => { mock.chrome = !mock.chrome; status(); });
  $('mock-reset').addEventListener('click', reset);
  $('test-filter').addEventListener('input', event => {
    const query = event.target.value.trim().toLocaleLowerCase('ko'); let count = 0;
    document.querySelectorAll('#test-matrix tbody tr').forEach(row => {
      row.hidden = !row.textContent.toLocaleLowerCase('ko').includes(query);
      if (!row.hidden) count++;
    }); write('test-count', `${count} / 40개 항목`);
  });
  const detailsBeforePrint = new Map();
  const hiddenRowsBeforePrint = new Map();
  window.addEventListener('beforeprint', () => {
    document.querySelectorAll('details').forEach(d => { detailsBeforePrint.set(d, d.open); d.open = true; });
    document.querySelectorAll('#test-matrix tbody tr').forEach(r => { hiddenRowsBeforePrint.set(r, r.hidden); r.hidden = false; });
  });
  window.addEventListener('afterprint', () => {
    detailsBeforePrint.forEach((open, d) => { d.open = open; }); detailsBeforePrint.clear();
    hiddenRowsBeforePrint.forEach((hidden, r) => { r.hidden = hidden; }); hiddenRowsBeforePrint.clear();
  });
  $('print-document').addEventListener('click', () => window.print());
  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver(entries => entries.forEach(entry => {
      if (entry.isIntersecting) {
        document.querySelectorAll('.toc a').forEach(a => a.classList.toggle('current', a.hash === `#${entry.target.id}`));
      }
    }), {rootMargin: '-10% 0px -70% 0px'});
    document.querySelectorAll('.doc-section').forEach(section => observer.observe(section));
  }
})();
