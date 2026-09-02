(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.ImaikuraWork = api;
})(typeof window !== 'undefined' ? window : globalThis, function () {
  'use strict';

  function parseClockTime(value) {
    if (typeof value !== 'string' || !/^\d{2}:\d{2}$/.test(value)) {
      throw new Error('始業時刻と終業時刻を入力してください。');
    }
    const [hours, minutes] = value.split(':').map(Number);
    if (hours < 0 || hours > 23 || minutes < 0 || minutes > 59) {
      throw new Error('時刻を正しく入力してください。');
    }
    return hours * 60 + minutes;
  }

  function requiredBreakMinutes(actualWorkMinutes) {
    const minutes = Number(actualWorkMinutes);
    if (!Number.isFinite(minutes) || minutes < 0) {
      throw new Error('実労働時間を正しく指定してください。');
    }
    if (minutes > 480) return 60;
    if (minutes > 360) return 45;
    return 0;
  }

  function calculateWorkTime(options) {
    const startMinutes = parseClockTime(options.startTime);
    const endMinutes = parseClockTime(options.endTime);
    const nextDay = Boolean(options.nextDay);
    const breakMinutes = Number(options.breakMinutes);

    if (!Number.isInteger(breakMinutes) || breakMinutes < 0 || breakMinutes > 1440) {
      throw new Error('休憩時間は0〜1,440分の整数で入力してください。');
    }

    let elapsedMinutes = endMinutes - startMinutes + (nextDay ? 1440 : 0);

    if (!nextDay && elapsedMinutes < 0) {
      throw new Error('終業時刻が始業時刻より前です。夜勤などで翌日に終わる場合は「翌日」を選択してください。');
    }
    if (nextDay && elapsedMinutes <= 0) {
      throw new Error('翌日終了の時刻を確認してください。');
    }
    if (elapsedMinutes > 1440) {
      throw new Error('このツールは24時間以内の1勤務を対象にしています。終了日の選択を確認してください。');
    }
    if (breakMinutes > elapsedMinutes) {
      throw new Error('休憩時間は、始業から終業までの時間以下にしてください。');
    }

    const actualWorkMinutes = elapsedMinutes - breakMinutes;
    const minimumBreakMinutes = requiredBreakMinutes(actualWorkMinutes);
    const breakShortfallMinutes = Math.max(0, minimumBreakMinutes - breakMinutes);
    const dailyOverEightHoursMinutes = Math.max(0, actualWorkMinutes - 480);

    return {
      startMinutes,
      endMinutes,
      nextDay,
      elapsedMinutes,
      breakMinutes,
      actualWorkMinutes,
      minimumBreakMinutes,
      breakShortfallMinutes,
      dailyOverEightHoursMinutes,
      meetsMinimumBreak: breakShortfallMinutes === 0
    };
  }

  return { parseClockTime, requiredBreakMinutes, calculateWorkTime };
});
