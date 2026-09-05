document.addEventListener('DOMContentLoaded', function () {
  'use strict';
  const form = document.getElementById('paid-leave-form');
  if (!form || !window.ImaikuraPaidLeave) return;

  const scheduleMode = document.getElementById('schedule-mode');
  const weeklyWrap = document.getElementById('weekly-days-wrap');
  const annualWrap = document.getElementById('annual-days-wrap');
  const referenceDate = document.getElementById('reference-date');
  const result = document.getElementById('paid-leave-result');
  const errorBox = document.getElementById('paid-leave-errors');
  const nf = new Intl.NumberFormat('ja-JP', { maximumFractionDigits: 1 });

  if (!referenceDate.value) {
    const today = new Date();
    referenceDate.value = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
  }

  function updateScheduleMode() {
    const annual = scheduleMode.value === 'annual';
    weeklyWrap.hidden = annual;
    annualWrap.hidden = !annual;
    document.getElementById('weekly-days').disabled = annual;
    document.getElementById('annual-days').disabled = !annual;
  }

  function jpDate(value) {
    if (!value) return '—';
    const parts = value.split('-');
    return `${Number(parts[0])}年${Number(parts[1])}月${Number(parts[2])}日`;
  }

  function showErrors(errors) {
    errorBox.innerHTML = `<strong>入力内容を確認してください</strong><ul>${errors.map((item) => `<li>${item}</li>`).join('')}</ul>`;
    errorBox.hidden = false;
    result.hidden = true;
    errorBox.focus();
  }

  scheduleMode.addEventListener('change', updateScheduleMode);
  updateScheduleMode();

  form.addEventListener('submit', function (event) {
    event.preventDefault();
    errorBox.hidden = true;
    const data = new FormData(form);
    const calculated = window.ImaikuraPaidLeave.calculatePaidLeave({
      hireDate: data.get('hireDate'),
      referenceDate: data.get('referenceDate'),
      scheduleMode: data.get('scheduleMode'),
      weeklyDays: data.get('weeklyDays'),
      annualDays: data.get('annualDays'),
      weeklyHours: data.get('weeklyHours'),
      attendanceRate: data.get('attendanceRate'),
      daysTaken: data.get('daysTaken')
    });

    if (!calculated.ok) {
      showErrors(calculated.errors);
      return;
    }

    const groupLabel = calculated.fullTimeEquivalent
      ? '通常の付与日数（週5日以上または週30時間以上）'
      : `比例付与（週${calculated.scheduleGroup}日相当）`;
    const attendanceText = calculated.eligibleByAttendance
      ? '出勤率80％以上として判定'
      : '出勤率80％未満のため、法定の付与要件を満たさない判定';

    if (calculated.beforeFirstGrant) {
      result.innerHTML = `
        <div class="result-eyebrow">初回付与前</div>
        <h2>次の法定付与日は ${jpDate(calculated.nextGrantDate)}</h2>
        <div class="result-grid paid-leave-result-grid">
          <div><span>初回の法定付与</span><strong>${nf.format(calculated.firstGrantDays)}日</strong></div>
          <div><span>付与日まで</span><strong>${nf.format(calculated.daysUntilNextGrant)}日</strong></div>
          <div><span>判定区分</span><strong class="result-small">${groupLabel}</strong></div>
        </div>
        <p class="result-note">${attendanceText}。会社が基準日を統一している場合や前倒し付与をしている場合は、就業規則・勤怠システムの付与日を優先してください。</p>`;
    } else {
      const mandatory = calculated.mandatoryFiveApplies
        ? `<strong>${nf.format(calculated.mandatoryFiveRemaining)}日</strong><small>年5日取得義務の残り目安</small>`
        : '<strong>対象外</strong><small>今回の法定付与が10日未満</small>';
      result.innerHTML = `
        <div class="result-eyebrow">法定付与日数の目安</div>
        <h2>${nf.format(calculated.statutoryGrantDays)}日</h2>
        <div class="result-grid paid-leave-result-grid">
          <div><span>今回の付与日</span><strong class="result-small">${jpDate(calculated.currentGrantDate)}</strong></div>
          <div><span>取得後の残り</span><strong>${nf.format(calculated.remainingDays)}日</strong></div>
          <div><span>次回付与日</span><strong class="result-small">${jpDate(calculated.nextGrantDate)}</strong></div>
          <div><span>今回分の時効目安</span><strong class="result-small">${jpDate(calculated.expiryDate)}</strong></div>
          <div class="result-wide"><span>年5日取得義務</span>${mandatory}</div>
        </div>
        <p class="result-note">${groupLabel}・${attendanceText}。残日数は「今回の付与分だけ」から入力した取得日数を差し引いた値です。前年繰越分、会社独自の上乗せ、時間単位年休は含みません。</p>`;
    }
    result.hidden = false;
    result.focus();
    if (typeof window.gtag === 'function') window.gtag('event', 'calculate_paid_leave', { schedule_group: calculated.scheduleGroup });
  });
});
