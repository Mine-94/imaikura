(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.ImaikuraPaidLeave = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  const GRANT_TABLE = Object.freeze({
    full: Object.freeze([10, 11, 12, 14, 16, 18, 20]),
    4: Object.freeze([7, 8, 9, 10, 12, 13, 15]),
    3: Object.freeze([5, 6, 6, 8, 9, 10, 11]),
    2: Object.freeze([3, 4, 4, 5, 6, 6, 7]),
    1: Object.freeze([1, 2, 2, 2, 3, 3, 3])
  });

  function parseDate(value) {
    if (value instanceof Date && !Number.isNaN(value.getTime())) {
      return new Date(value.getFullYear(), value.getMonth(), value.getDate());
    }
    if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return null;
    const [year, month, day] = value.split('-').map(Number);
    const date = new Date(year, month - 1, day);
    if (date.getFullYear() !== year || date.getMonth() !== month - 1 || date.getDate() !== day) return null;
    return date;
  }

  function formatDate(date) {
    if (!(date instanceof Date) || Number.isNaN(date.getTime())) return '';
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
  }

  function addMonths(date, months) {
    const originalDay = date.getDate();
    const result = new Date(date.getFullYear(), date.getMonth(), 1);
    result.setMonth(result.getMonth() + months);
    const lastDay = new Date(result.getFullYear(), result.getMonth() + 1, 0).getDate();
    result.setDate(Math.min(originalDay, lastDay));
    return result;
  }

  function addDays(date, days) {
    const result = new Date(date.getFullYear(), date.getMonth(), date.getDate());
    result.setDate(result.getDate() + days);
    return result;
  }

  function diffDays(later, earlier) {
    const ms = Date.UTC(later.getFullYear(), later.getMonth(), later.getDate()) - Date.UTC(earlier.getFullYear(), earlier.getMonth(), earlier.getDate());
    return Math.floor(ms / 86400000);
  }

  function resolveScheduleGroup(scheduleMode, weeklyDays, annualDays, weeklyHours) {
    if (weeklyHours >= 30) return 'full';
    if (scheduleMode === 'annual') {
      if (annualDays >= 217) return 'full';
      if (annualDays >= 169) return '4';
      if (annualDays >= 121) return '3';
      if (annualDays >= 73) return '2';
      if (annualDays >= 48) return '1';
      return null;
    }
    if (weeklyDays >= 5) return 'full';
    if (weeklyDays >= 1 && weeklyDays <= 4) return String(weeklyDays);
    return null;
  }

  function calculatePaidLeave(input) {
    const hireDate = parseDate(input.hireDate);
    const referenceDate = parseDate(input.referenceDate);
    const scheduleMode = input.scheduleMode === 'annual' ? 'annual' : 'weekly';
    const weeklyDays = Number(input.weeklyDays);
    const annualDays = Number(input.annualDays);
    const weeklyHours = Number(input.weeklyHours);
    const attendanceRate = Number(input.attendanceRate);
    const daysTaken = Math.max(0, Number(input.daysTaken) || 0);

    const errors = [];
    if (!hireDate) errors.push('入社日を正しく入力してください。');
    if (!referenceDate) errors.push('基準日を正しく入力してください。');
    if (hireDate && referenceDate && referenceDate < hireDate) errors.push('基準日は入社日以後にしてください。');
    if (!Number.isFinite(weeklyHours) || weeklyHours < 0 || weeklyHours > 80) errors.push('週の所定労働時間は0〜80時間で入力してください。');
    if (!Number.isFinite(attendanceRate) || attendanceRate < 0 || attendanceRate > 100) errors.push('出勤率は0〜100％で入力してください。');
    if (scheduleMode === 'weekly' && (!Number.isInteger(weeklyDays) || weeklyDays < 1 || weeklyDays > 7)) errors.push('週の所定労働日数を選んでください。');
    if (scheduleMode === 'annual' && (!Number.isFinite(annualDays) || annualDays < 1 || annualDays > 366)) errors.push('年間の所定労働日数は1〜366日で入力してください。');
    if (errors.length) return { ok: false, errors };

    const scheduleGroup = resolveScheduleGroup(scheduleMode, weeklyDays, annualDays, weeklyHours);
    if (!scheduleGroup) {
      return {
        ok: false,
        errors: ['年間所定労働日数が48日未満の場合、この比例付与表では判定できません。勤務先または労働基準監督署へ確認してください。']
      };
    }

    const firstGrantDate = addMonths(hireDate, 6);
    const eligibleByAttendance = attendanceRate >= 80;

    if (referenceDate < firstGrantDate) {
      const statutoryDaysAtFirstGrant = eligibleByAttendance ? GRANT_TABLE[scheduleGroup][0] : 0;
      return {
        ok: true,
        beforeFirstGrant: true,
        scheduleGroup,
        fullTimeEquivalent: scheduleGroup === 'full',
        eligibleByAttendance,
        statutoryGrantDays: 0,
        firstGrantDays: statutoryDaysAtFirstGrant,
        firstGrantDate: formatDate(firstGrantDate),
        nextGrantDate: formatDate(firstGrantDate),
        daysUntilNextGrant: diffDays(firstGrantDate, referenceDate),
        currentGrantDate: '',
        expiryDate: '',
        remainingDays: 0,
        mandatoryFiveApplies: false,
        mandatoryFiveRemaining: 0,
        stage: -1,
        errors: []
      };
    }

    let stage = 0;
    let currentGrantDate = firstGrantDate;
    for (let i = 1; i <= 6; i += 1) {
      const candidate = addMonths(firstGrantDate, i * 12);
      if (candidate <= referenceDate) {
        stage = i;
        currentGrantDate = candidate;
      } else {
        break;
      }
    }
    if (referenceDate >= addMonths(firstGrantDate, 72)) {
      stage = 6;
      const elapsedYears = Math.floor(diffDays(referenceDate, firstGrantDate) / 365.2425);
      currentGrantDate = addMonths(firstGrantDate, Math.max(6, elapsedYears) * 12);
      while (addMonths(currentGrantDate, 12) <= referenceDate) currentGrantDate = addMonths(currentGrantDate, 12);
      while (currentGrantDate > referenceDate) currentGrantDate = addMonths(currentGrantDate, -12);
    }

    const statutoryGrantDays = eligibleByAttendance ? GRANT_TABLE[scheduleGroup][stage] : 0;
    const remainingDays = Math.max(0, statutoryGrantDays - daysTaken);
    const mandatoryFiveApplies = statutoryGrantDays >= 10;
    const mandatoryFiveRemaining = mandatoryFiveApplies ? Math.max(0, 5 - Math.min(daysTaken, 5)) : 0;
    const nextGrantDate = addMonths(currentGrantDate, 12);
    const expiryDate = addDays(addMonths(currentGrantDate, 24), -1);

    return {
      ok: true,
      beforeFirstGrant: false,
      scheduleGroup,
      fullTimeEquivalent: scheduleGroup === 'full',
      eligibleByAttendance,
      statutoryGrantDays,
      firstGrantDays: GRANT_TABLE[scheduleGroup][0],
      firstGrantDate: formatDate(firstGrantDate),
      currentGrantDate: formatDate(currentGrantDate),
      nextGrantDate: formatDate(nextGrantDate),
      daysUntilNextGrant: diffDays(nextGrantDate, referenceDate),
      expiryDate: formatDate(expiryDate),
      remainingDays,
      mandatoryFiveApplies,
      mandatoryFiveRemaining,
      stage,
      errors: []
    };
  }

  return {
    GRANT_TABLE,
    parseDate,
    formatDate,
    addMonths,
    resolveScheduleGroup,
    calculatePaidLeave
  };
});
