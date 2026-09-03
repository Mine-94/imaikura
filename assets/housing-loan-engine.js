(function (root, factory) {
  const tax = typeof module === 'object' && module.exports
    ? require('./tax-engine.js')
    : root.ImaikuraTax;
  const api = factory(tax);
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.ImaikuraHousing = api;
})(typeof window !== 'undefined' ? window : globalThis, function (tax) {
  'use strict';

  if (!tax) throw new Error('ImaikuraTax is required.');

  const LIMITS_2026_NEW = {
    chotan: {
      base: 45000000,
      upgrade: 50000000,
      period: 13,
      label: '認定長期優良住宅・認定低炭素住宅'
    },
    zeh: {
      base: 35000000,
      upgrade: 45000000,
      period: 13,
      label: 'ZEH水準省エネ住宅'
    },
    shoene: {
      base: 20000000,
      upgrade: 30000000,
      period: 13,
      label: '省エネ基準適合住宅'
    },
    otherGrandfathered: {
      base: 20000000,
      upgrade: 20000000,
      period: 10,
      label: 'その他住宅（経過措置対象）'
    },
    ineligibleOther: {
      base: 0,
      upgrade: 0,
      period: 0,
      label: '省エネ基準を満たさず経過措置にも該当しない新築住宅'
    }
  };

  function clamp(value, min, max) {
    const number = Number(value);
    if (!Number.isFinite(number)) return min;
    return Math.min(max, Math.max(min, number));
  }

  function calculateHousingLoanDeduction2026(options) {
    const annualSalary = clamp(options.annualSalary, 0, 100000000);
    const otherIncome = clamp(options.otherIncome, 0, 100000000);
    const loanYearEndBalance = clamp(options.loanYearEndBalance, 0, 200000000);
    const acquisitionCost = clamp(options.acquisitionCost, 0, 200000000);
    const floorArea = clamp(options.floorArea, 0, 10000);
    const loanTermYears = clamp(options.loanTermYears, 0, 100);
    const childOrYoungCouple = Boolean(options.childOrYoungCouple);
    const category = Object.prototype.hasOwnProperty.call(LIMITS_2026_NEW, options.housingCategory)
      ? options.housingCategory
      : 'ineligibleOther';
    const limits = LIMITS_2026_NEW[category];

    const salaryIncome = tax.salaryIncome2026(annualSalary);
    const totalIncome = salaryIncome + otherIncome;
    const floorAreaRequired = totalIncome > 10000000 || childOrYoungCouple ? 50 : 40;

    const principalResidence = options.principalResidence !== false;
    const movedWithinSixMonths = options.movedWithinSixMonths !== false;
    const residentAtYearEnd = options.residentAtYearEnd !== false;
    const residentialHalfOrMore = options.residentialHalfOrMore !== false;

    const eligibilityReasons = [];
    if (limits.period === 0) eligibilityReasons.push('選択した住宅区分は令和8年入居分の対象外です。');
    if (totalIncome > 20000000) eligibilityReasons.push('合計所得金額が2,000万円を超えています。');
    if (floorArea < floorAreaRequired) {
      eligibilityReasons.push(`床面積が必要な${floorAreaRequired}㎡以上を満たしていません。`);
    }
    if (loanTermYears < 10) eligibilityReasons.push('住宅ローンの償還期間が10年未満です。');
    if (!principalResidence) eligibilityReasons.push('本人が主として居住する住宅ではありません。');
    if (!movedWithinSixMonths) eligibilityReasons.push('引渡し・工事完了から6か月以内に入居していません。');
    if (!residentAtYearEnd) eligibilityReasons.push('入居年の12月31日まで引き続き居住していません。');
    if (!residentialHalfOrMore) eligibilityReasons.push('床面積の2分の1以上が居住用ではありません。');
    if (loanYearEndBalance <= 0) eligibilityReasons.push('年末ローン残高が0円です。');
    if (acquisitionCost <= 0) eligibilityReasons.push('取得対価等が0円です。');

    const eligible = eligibilityReasons.length === 0;
    const borrowLimit = childOrYoungCouple ? limits.upgrade : limits.base;
    const qualifyingBalance = eligible
      ? Math.min(loanYearEndBalance, acquisitionCost, borrowLimit)
      : 0;
    const statutoryCredit = Math.floor(qualifyingBalance * 0.007 / 100) * 100;

    const dependents = Math.floor(clamp(options.dependents, 0, 10));
    const specificDependents = Math.floor(clamp(options.specificDependents, 0, 10));
    const elderDependents = Math.floor(clamp(options.elderDependents, 0, 10));
    const spouse = Boolean(options.spouse);
    const monthlySalary = annualSalary / 12;
    const social = options.socialInsuranceAnnual > 0
      ? { total: clamp(options.socialInsuranceAnnual, 0, 30000000) }
      : tax.socialInsurance2026({
          monthlySalary,
          annualBonus: 0,
          age: options.age || 30,
          prefecture: options.prefecture || '東京都'
        });

    const spouseDeduction = tax.spouseDeduction2026(salaryIncome, spouse);
    const dependentDeduction = dependents * 380000 + spouseDeduction +
      specificDependents * 630000 + elderDependents * 480000;
    const basicDeduction = tax.incomeBasicDeduction2026(totalIncome);
    const taxableIncome = Math.max(0, totalIncome - basicDeduction - social.total - dependentDeduction);
    const taxBefore = tax.nationalIncomeTax(taxableIncome);

    const baseIncomeTaxCredit = eligible ? Math.min(statutoryCredit, taxBefore.baseTax) : 0;
    const baseTaxAfter = Math.max(0, taxBefore.baseTax - baseIncomeTaxCredit);
    const reconstructionTaxAfter = Math.floor(baseTaxAfter * 21 / 1000);
    const incomeTaxAndReconstructionReduction = eligible
      ? taxBefore.total - (baseTaxAfter + reconstructionTaxAfter)
      : 0;
    const creditShortfall = eligible ? Math.max(0, statutoryCredit - baseIncomeTaxCredit) : 0;
    const residentTaxLimit = eligible
      ? Math.min(97500, Math.floor(taxBefore.taxable * 0.05))
      : 0;
    const residentTaxReduction = Math.min(creditShortfall, residentTaxLimit);
    const totalSaving = incomeTaxAndReconstructionReduction + residentTaxReduction;

    return {
      annualSalary,
      salaryIncome,
      otherIncome,
      totalIncome,
      loanYearEndBalance,
      acquisitionCost,
      floorArea,
      floorAreaRequired,
      loanTermYears,
      childOrYoungCouple,
      category,
      categoryLabel: limits.label,
      controlPeriod: limits.period,
      borrowLimit,
      qualifyingBalance,
      statutoryCredit,
      socialInsurance: social.total,
      taxableIncome: taxBefore.taxable,
      baseTaxBeforeCredit: taxBefore.baseTax,
      baseIncomeTaxCredit,
      incomeTaxAndReconstructionReduction,
      creditShortfall,
      residentTaxLimit,
      residentTaxReduction,
      totalSaving,
      eligible,
      eligibilityReasons
    };
  }

  return { LIMITS_2026_NEW, calculateHousingLoanDeduction2026 };
});
