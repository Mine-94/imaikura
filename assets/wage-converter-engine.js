(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.ImaikuraWage = api;
})(typeof window !== 'undefined' ? window : globalThis, function () {
  'use strict';

  const MODES = ['hourly', 'daily', 'monthly', 'annual'];

  function numeric(value, label, min, max) {
    const number = Number(value);
    if (!Number.isFinite(number) || number < min || number > max) {
      throw new Error(label + 'は' + min.toLocaleString('ja-JP') + '〜' + max.toLocaleString('ja-JP') + 'の範囲で入力してください。');
    }
    return number;
  }

  function calculateWageConversion(options) {
    const mode = MODES.includes(options.mode) ? options.mode : 'monthly';
    const amount = numeric(options.amount, '賃金額', 1, 1000000000);
    const dailyHours = numeric(options.dailyHours, '1日の所定労働時間', 0.01, 24);
    const annualWorkDays = numeric(options.annualWorkDays, '年間所定労働日数', 1, 366);
    const annualBonus = numeric(options.annualBonus || 0, '年間賞与', 0, 1000000000);
    const annualHoursOverride = numeric(options.annualHoursOverride || 0, '年間所定労働時間の直接入力', 0, 8784);
    const minimumWage = numeric(options.minimumWage || 0, '比較する最低賃金', 0, 1000000);

    if (mode === 'annual' && annualBonus > amount) {
      throw new Error('年間賞与は、入力した年収以下にしてください。');
    }

    const calculatedAnnualHours = dailyHours * annualWorkDays;
    const annualScheduledHours = annualHoursOverride > 0 ? annualHoursOverride : calculatedAnnualHours;
    const monthlyAverageScheduledHours = annualScheduledHours / 12;

    let hourlyEquivalent;
    let dailyEquivalent;
    let monthlyEquivalent;
    let annualBase;
    let totalAnnual;

    if (mode === 'hourly') {
      hourlyEquivalent = amount;
      dailyEquivalent = hourlyEquivalent * dailyHours;
      annualBase = hourlyEquivalent * annualScheduledHours;
      monthlyEquivalent = annualBase / 12;
      totalAnnual = annualBase + annualBonus;
    } else if (mode === 'daily') {
      dailyEquivalent = amount;
      hourlyEquivalent = dailyEquivalent / dailyHours;
      annualBase = dailyEquivalent * annualWorkDays;
      monthlyEquivalent = annualBase / 12;
      totalAnnual = annualBase + annualBonus;
    } else if (mode === 'annual') {
      totalAnnual = amount;
      annualBase = totalAnnual - annualBonus;
      monthlyEquivalent = annualBase / 12;
      hourlyEquivalent = annualBase / annualScheduledHours;
      dailyEquivalent = hourlyEquivalent * dailyHours;
    } else {
      monthlyEquivalent = amount;
      annualBase = monthlyEquivalent * 12;
      hourlyEquivalent = annualBase / annualScheduledHours;
      dailyEquivalent = hourlyEquivalent * dailyHours;
      totalAnnual = annualBase + annualBonus;
    }

    const minimumWageComparison = minimumWage > 0
      ? {
          entered: true,
          minimumWage,
          differencePerHour: hourlyEquivalent - minimumWage,
          meetsOrExceeds: hourlyEquivalent + 1e-9 >= minimumWage,
          requiredDaily: minimumWage * dailyHours,
          requiredMonthly: minimumWage * monthlyAverageScheduledHours,
          requiredAnnualBase: minimumWage * annualScheduledHours
        }
      : {
          entered: false,
          minimumWage: 0,
          differencePerHour: 0,
          meetsOrExceeds: null,
          requiredDaily: 0,
          requiredMonthly: 0,
          requiredAnnualBase: 0
        };

    return {
      mode,
      amount,
      dailyHours,
      annualWorkDays,
      annualBonus,
      annualHoursOverride,
      annualHoursSource: annualHoursOverride > 0 ? 'override' : 'days',
      calculatedAnnualHours,
      annualScheduledHours,
      monthlyAverageScheduledHours,
      hourlyEquivalent,
      dailyEquivalent,
      monthlyEquivalent,
      annualBase,
      totalAnnual,
      minimumWageComparison
    };
  }

  return { MODES, calculateWageConversion };
});
