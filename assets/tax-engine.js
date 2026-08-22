(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.ImaikuraTax = api;
})(typeof window !== 'undefined' ? window : globalThis, function () {
  'use strict';

  const HEALTH_RATES_2026 = {
    '北海道':10.28,'青森県':9.85,'岩手県':9.51,'宮城県':10.10,'秋田県':10.01,'山形県':9.75,'福島県':9.50,
    '茨城県':9.52,'栃木県':9.82,'群馬県':9.68,'埼玉県':9.67,'千葉県':9.73,'東京都':9.85,'神奈川県':9.92,
    '新潟県':9.21,'富山県':9.59,'石川県':9.70,'福井県':9.71,'山梨県':9.55,'長野県':9.63,
    '岐阜県':9.80,'静岡県':9.61,'愛知県':9.93,'三重県':9.77,
    '滋賀県':9.88,'京都府':9.89,'大阪府':10.13,'兵庫県':10.12,'奈良県':9.91,'和歌山県':10.06,
    '鳥取県':9.86,'島根県':9.94,'岡山県':10.05,'広島県':9.78,'山口県':10.15,
    '徳島県':10.24,'香川県':10.02,'愛媛県':9.98,'高知県':10.05,
    '福岡県':10.11,'佐賀県':10.55,'長崎県':10.06,'熊本県':10.08,'大分県':10.08,'宮崎県':9.77,'鹿児島県':10.13,'沖縄県':9.44
  };

  const HEALTH_STANDARDS = [
    [63000,58000],[73000,68000],[83000,78000],[93000,88000],[101000,98000],[107000,104000],[114000,110000],
    [122000,118000],[130000,126000],[138000,134000],[146000,142000],[155000,150000],[165000,160000],
    [175000,170000],[185000,180000],[195000,190000],[210000,200000],[230000,220000],[250000,240000],
    [270000,260000],[290000,280000],[310000,300000],[330000,320000],[350000,340000],[370000,360000],
    [395000,380000],[425000,410000],[455000,440000],[485000,470000],[515000,500000],[545000,530000],
    [575000,560000],[605000,590000],[635000,620000],[665000,650000],[695000,680000],[730000,710000],
    [770000,750000],[810000,790000],[855000,830000],[905000,880000],[955000,930000],[1005000,980000],
    [1055000,1030000],[1115000,1090000],[1175000,1150000],[1235000,1210000],[1295000,1270000],
    [1355000,1330000],[Infinity,1390000]
  ];

  const PENSION_STANDARDS = [
    [93000,88000],[101000,98000],[107000,104000],[114000,110000],[122000,118000],[130000,126000],
    [138000,134000],[146000,142000],[155000,150000],[165000,160000],[175000,170000],[185000,180000],
    [195000,190000],[210000,200000],[230000,220000],[250000,240000],[270000,260000],[290000,280000],
    [310000,300000],[330000,320000],[350000,340000],[370000,360000],[395000,380000],[425000,410000],
    [455000,440000],[485000,470000],[515000,500000],[545000,530000],[575000,560000],[605000,590000],
    [635000,620000],[Infinity,650000]
  ];

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, Number(value) || 0));
  }

  function standardAmount(monthly, table) {
    const row = table.find(([upper]) => monthly < upper);
    return row ? row[1] : table[table.length - 1][1];
  }

  // 令和8・9年分。220万円未満は国税庁の特例表を反映。
  function salaryIncome2026(gross) {
    const n = Math.max(0, Math.floor(gross));
    if (n < 691000) return 0;
    if (n < 741000) return Math.max(0, n - 740000);
    if (n < 2191000) return n - 740000;
    if (n < 2193000) return 1451000;
    if (n < 2196000) return 1453000;
    if (n < 2200000) return 1456000;
    if (n <= 3600000) return Math.floor(n - (n * 0.30 + 80000));
    if (n <= 6600000) return Math.floor(n - (n * 0.20 + 440000));
    if (n <= 8500000) return Math.floor(n - (n * 0.10 + 1100000));
    return n - 1950000;
  }

  function incomeBasicDeduction2026(totalIncome) {
    const g = Math.max(0, totalIncome);
    if (g <= 1320000) return 1040000;
    if (g <= 3360000) return 620000;
    if (g <= 4890000) return 680000;
    if (g <= 6550000) return 670000;
    if (g <= 23500000) return 620000;
    if (g <= 24000000) return 480000;
    if (g <= 24500000) return 320000;
    if (g <= 25000000) return 160000;
    return 0;
  }

  function nationalIncomeTax(taxable) {
    const base = Math.floor(Math.max(0, taxable) / 1000) * 1000;
    let rate = 0;
    let deduction = 0;
    if (base <= 1949000) { rate = 0.05; }
    else if (base <= 3299000) { rate = 0.10; deduction = 97500; }
    else if (base <= 6949000) { rate = 0.20; deduction = 427500; }
    else if (base <= 8999000) { rate = 0.23; deduction = 636000; }
    else if (base <= 17999000) { rate = 0.33; deduction = 1536000; }
    else if (base <= 39999000) { rate = 0.40; deduction = 2796000; }
    else { rate = 0.45; deduction = 4796000; }
    const baseTax = Math.max(0, Math.floor(base * rate - deduction));
    return { taxable: base, rate, baseTax, total: Math.floor(baseTax * 1.021) };
  }

  function socialInsurance2026(options) {
    const monthlySalary = clamp(options.monthlySalary, 0, 5000000);
    const annualBonus = clamp(options.annualBonus, 0, 20000000);
    const bonusPayments = clamp(options.bonusPayments || 2, 1, 12);
    const age = clamp(options.age || 30, 18, 69);
    const prefecture = HEALTH_RATES_2026[options.prefecture] ? options.prefecture : '東京都';
    const healthRate = HEALTH_RATES_2026[prefecture] / 100;
    const careRate = age >= 40 && age <= 64 ? 0.0162 : 0;
    const supportRate = 0.0023;
    const pensionRate = 0.183;
    const employmentRate = 0.005;
    const healthStandard = standardAmount(monthlySalary, HEALTH_STANDARDS);
    const pensionStandard = standardAmount(monthlySalary, PENSION_STANDARDS);
    const healthBonusBase = Math.min(Math.floor(annualBonus / 1000) * 1000, 5730000);
    const eachBonus = annualBonus / bonusPayments;
    const pensionBonusBase = Math.min(Math.floor(eachBonus / 1000) * 1000, 1500000) * bonusPayments;
    const health = Math.round((healthStandard * 12 + healthBonusBase) * healthRate / 2);
    const care = Math.round((healthStandard * 12 + healthBonusBase) * careRate / 2);
    const childSupport = Math.round((healthStandard * 12 + healthBonusBase) * supportRate / 2);
    const pension = Math.round((pensionStandard * 12 + pensionBonusBase) * pensionRate / 2);
    const gross = monthlySalary * 12 + annualBonus;
    const employment = Math.floor(gross * employmentRate);
    return {
      prefecture, healthRate, healthStandard, pensionStandard,
      health, care, childSupport, pension, employment,
      total: health + care + childSupport + pension + employment
    };
  }

  function takeHome2026(options) {
    const monthlySalary = clamp(options.monthlySalary, 0, 5000000);
    const annualBonus = clamp(options.annualBonus, 0, 20000000);
    const dependents = clamp(options.dependents, 0, 10);
    const specificDependents = clamp(options.specificDependents, 0, 10);
    const elderDependents = clamp(options.elderDependents, 0, 10);
    const spouse = options.spouse ? 1 : 0;
    const gross = monthlySalary * 12 + annualBonus;
    const salaryIncome = salaryIncome2026(gross);
    const social = socialInsurance2026(options);
    const incomeDeduction = incomeBasicDeduction2026(salaryIncome);
    const dependentIncomeDeduction = (dependents + spouse) * 380000 + specificDependents * 630000 + elderDependents * 480000;
    const taxableIncome = Math.max(0, salaryIncome - incomeDeduction - dependentIncomeDeduction - social.total);
    const incomeTaxInfo = nationalIncomeTax(taxableIncome);
    const residentDependentDeduction = (dependents + spouse) * 330000 + specificDependents * 450000 + elderDependents * 380000;
    const residentDeductions = 430000 + residentDependentDeduction + social.total;
    const residentTaxable = Math.floor(Math.max(0, salaryIncome - residentDeductions) / 1000) * 1000;
    const residentTax = residentTaxable > 0 ? Math.floor(residentTaxable * 0.10 / 100) * 100 + 5000 : 0;
    const annualNet = Math.max(0, gross - social.total - incomeTaxInfo.total - residentTax);
    return {
      gross, salaryIncome, social, incomeDeduction, dependentIncomeDeduction,
      taxableIncome: incomeTaxInfo.taxable, incomeTax: incomeTaxInfo.total,
      marginalRate: incomeTaxInfo.rate, residentTaxable, residentTax,
      annualNet, monthlyNet: Math.floor(annualNet / 12), netRate: gross ? annualNet / gross : 0
    };
  }

  function furusatoLimit2026(options) {
    const annualSalary = clamp(options.annualSalary, 0, 100000000);
    const dependents = clamp(options.dependents, 0, 10);
    const specificDependents = clamp(options.specificDependents, 0, 10);
    const elderDependents = clamp(options.elderDependents, 0, 10);
    const spouse = options.spouse ? 1 : 0;
    const monthlySalary = annualSalary / 12;
    const social = options.socialInsuranceAnnual > 0
      ? { total: Number(options.socialInsuranceAnnual) }
      : socialInsurance2026({ monthlySalary, annualBonus: 0, age: options.age || 30, prefecture: options.prefecture || '東京都' });
    const salaryIncome = salaryIncome2026(annualSalary);
    const incomeDependentDeduction = (dependents + spouse) * 380000 + specificDependents * 630000 + elderDependents * 480000;
    const residentDependentDeduction = (dependents + spouse) * 330000 + specificDependents * 450000 + elderDependents * 380000;
    const incomeTaxable = Math.max(0, salaryIncome - incomeBasicDeduction2026(salaryIncome) - social.total - incomeDependentDeduction);
    const incomeInfo = nationalIncomeTax(incomeTaxable);
    const residentTaxable = Math.floor(Math.max(0, salaryIncome - 430000 - social.total - residentDependentDeduction) / 1000) * 1000;
    const residentIncomeLevy = Math.floor(residentTaxable * 0.10 / 100) * 100;
    const denominator = 0.90 - incomeInfo.rate * 1.021;
    const limit = denominator > 0 ? Math.max(0, Math.floor((residentIncomeLevy * 0.20 / denominator + 2000) / 1000) * 1000) : 0;
    return { annualSalary, salaryIncome, socialInsurance: social.total, incomeTaxable: incomeInfo.taxable, marginalRate: incomeInfo.rate, residentTaxable, residentIncomeLevy, limit };
  }

  return {
    HEALTH_RATES_2026, salaryIncome2026, incomeBasicDeduction2026,
    nationalIncomeTax, socialInsurance2026, takeHome2026, furusatoLimit2026
  };
});
