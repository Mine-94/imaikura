(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.ImaikuraIncomeWall = api;
})(typeof window !== 'undefined' ? window : globalThis, function () {
  'use strict';

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, Number(value) || 0));
  }

  function calculateIncomeWall(options) {
    const annualSalary = clamp(options.annualSalary, 0, 10000000);
    const healthAnnualIncome = clamp(
      options.healthAnnualIncome == null ? annualSalary : options.healthAnnualIncome,
      0,
      10000000
    );
    const monthlyScheduledWage = clamp(
      options.monthlyScheduledWage == null ? annualSalary / 12 : options.monthlyScheduledWage,
      0,
      2000000
    );
    const weeklyHours = clamp(options.weeklyHours, 0, 80);
    const age = clamp(options.age || 30, 15, 99);
    const companyEmployees = Math.floor(clamp(options.companyEmployees || 50, 1, 1000000));
    const student = Boolean(options.student);
    const employmentOverTwoMonths = options.employmentOverTwoMonths !== false;
    const regularThreeQuarter = Boolean(options.regularThreeQuarter);
    const plannedWageRequirementRemoval = Boolean(options.plannedWageRequirementRemoval);
    const dependentRelation = options.dependentRelation === 'spouse' ? 'spouse' : 'other';
    const disabled = Boolean(options.disabled);

    // 2026年分：給与所得控除の最低保障額74万円＋扶養親族等の所得要件62万円。
    const taxDependentLimit = 1360000;
    const taxDependentEligible = annualSalary <= taxDependentLimit;

    // 給与所得控除74万円＋基礎控除104万円（給与のみ・他の所得なしの低所得帯）。
    const personalIncomeTaxLimit = 1780000;
    const personalIncomeTaxFree = annualSalary <= personalIncomeTaxLimit;

    // 通常労働者の4分の3基準を先に確認し、該当しない場合に短時間要件を確認。
    const regularEligible = employmentOverTwoMonths && regularThreeQuarter;
    const shortTimeConditionsExceptWage = employmentOverTwoMonths && companyEmployees >= 51 &&
      weeklyHours >= 20 && !student;
    const currentWageRequirementMet = monthlyScheduledWage >= 88000;
    const shortTimeEligible = shortTimeConditionsExceptWage &&
      (plannedWageRequirementRemoval || currentWageRequirementMet);
    const employeeSocialEligible = regularEligible || shortTimeEligible;
    const employeeSocialBasis = regularEligible
      ? 'three-quarter'
      : shortTimeEligible
        ? (plannedWageRequirementRemoval ? 'short-time-planned' : 'short-time-current')
        : 'not-eligible';

    // 被扶養者の年間収入要件。配偶者を除く19〜22歳は150万円未満。
    // 60歳以上または障害者は180万円未満。年齢は認定年の12月31日時点を想定。
    const specialYoungRelative = dependentRelation === 'other' && age >= 19 && age <= 22;
    const dependentLimit = disabled || age >= 60
      ? 1800000
      : specialYoungRelative
        ? 1500000
        : 1300000;
    const healthDependent = !employeeSocialEligible && healthAnnualIncome < dependentLimit;
    const dependentLost = !employeeSocialEligible && healthAnnualIncome >= dependentLimit;
    const healthRemaining = Math.max(0, dependentLimit - healthAnnualIncome);

    // 住民税は自治体・課税年度で限度額が異なるため、全国一律の壁には含めない。
    const taxWalls = [
      { amount: taxDependentLimit, label: '税法上の扶養所得要件' },
      { amount: personalIncomeTaxLimit, label: '本人の所得税非課税目安' }
    ];
    const nextTaxWall = taxWalls.find(wall => annualSalary < wall.amount) || null;

    return {
      annualSalary,
      healthAnnualIncome,
      monthlyScheduledWage,
      weeklyHours,
      age,
      companyEmployees,
      student,
      employmentOverTwoMonths,
      regularThreeQuarter,
      plannedWageRequirementRemoval,
      dependentRelation,
      disabled,
      taxDependentLimit,
      taxDependentEligible,
      personalIncomeTaxLimit,
      personalIncomeTaxFree,
      regularEligible,
      shortTimeConditionsExceptWage,
      currentWageRequirementMet,
      shortTimeEligible,
      employeeSocialEligible,
      employeeSocialBasis,
      specialYoungRelative,
      dependentLimit,
      healthDependent,
      dependentLost,
      healthRemaining,
      nextTaxWall,
      remainingToNextWall: nextTaxWall ? nextTaxWall.amount - annualSalary : 0,
      resultNature: plannedWageRequirementRemoval ? 'planned-rule-estimate' : 'current-rule-estimate'
    };
  }

  return { calculateIncomeWall };
});
