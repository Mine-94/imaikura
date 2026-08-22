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
    if (n < 741000) return 0;
    if (n < 2191000) return n - 740000;
    if (n < 2193000) return 1451000;
    if (n < 2196000) return 1453000;
    if (n < 2200000) return 1456000;
    if (n < 3600000) return Math.floor(n / 4 / 1000) * 1000 * 2.8 - 80000;
    if (n < 6600000) return Math.floor(n / 4 / 1000) * 1000 * 3.2 - 440000;
    if (n < 8500000) return Math.floor(n * 0.90 - 1100000);
    return n - 1950000;
  }

  // 令和8年度住民税（令和7年分給与）。給与所得控除の最低保障額は65万円。
  function residentSalaryIncome2026(gross) {
    const n = Math.max(0, Math.floor(gross));
    if (n <= 1900000) return Math.max(0, n - 650000);
    if (n < 3600000) return Math.floor(n / 4 / 1000) * 1000 * 2.8 - 80000;
    if (n < 6600000) return Math.floor(n / 4 / 1000) * 1000 * 3.2 - 440000;
    if (n < 8500000) return Math.floor(n * 0.90 - 1100000);
    return n - 1950000;
  }

  function residentBasicDeduction2026(totalIncome) {
    const g = Math.max(0, totalIncome);
    if (g <= 24000000) return 430000;
    if (g <= 24500000) return 290000;
    if (g <= 25000000) return 150000;
    return 0;
  }

  function residentSpouseDeduction2026(totalIncome, eligible) {
    if (!eligible) return 0;
    const g = Math.max(0, totalIncome);
    if (g <= 9000000) return 330000;
    if (g <= 9500000) return 220000;
    if (g <= 10000000) return 110000;
    return 0;
  }

  // 東京23区の標準税率で令和8年度の住民税を概算する。
  function residentTax2026(options) {
    const annualSalary = clamp(options.annualSalary, 0, 100000000);
    const socialInsurance = clamp(options.socialInsurance, 0, 30000000);
    const lifeInsuranceDeduction = clamp(options.lifeInsuranceDeduction, 0, 70000);
    const earthquakeInsuranceDeduction = clamp(options.earthquakeInsuranceDeduction, 0, 25000);
    const idecoDeduction = clamp(options.idecoDeduction, 0, 10000000);
    const medicalExpenseDeduction = clamp(options.medicalExpenseDeduction, 0, 30000000);
    const otherDeductions = clamp(options.otherDeductions, 0, 30000000);
    const dependents = Math.floor(clamp(options.dependents, 0, 20));
    const specificDependents = Math.floor(clamp(options.specificDependents, 0, 20));
    const elderDependents = Math.floor(clamp(options.elderDependents, 0, 20));
    const spouse = Boolean(options.spouse);
    const salaryIncome = residentSalaryIncome2026(annualSalary);
    const basicDeduction = residentBasicDeduction2026(salaryIncome);
    const spouseDeduction = residentSpouseDeduction2026(salaryIncome, spouse);
    const dependentDeduction = dependents * 330000 + specificDependents * 450000 + elderDependents * 380000;
    const totalDeductions = basicDeduction + socialInsurance + lifeInsuranceDeduction +
      earthquakeInsuranceDeduction + idecoDeduction + medicalExpenseDeduction + otherDeductions +
      spouseDeduction + dependentDeduction;
    const taxableIncome = Math.floor(Math.max(0, salaryIncome - totalDeductions) / 1000) * 1000;

    const familyCount = 1 + (spouse ? 1 : 0) + dependents + specificDependents + elderDependents;
    const fullyExemptLimit = familyCount === 1 ? 450000 : 350000 * familyCount + 310000;
    const incomeLevyExemptLimit = familyCount === 1 ? 450000 : 350000 * familyCount + 420000;
    const fullyExempt = salaryIncome <= fullyExemptLimit;
    const incomeLevyExempt = salaryIncome <= incomeLevyExemptLimit;

    let spouseDifference = 0;
    if (spouse) {
      if (salaryIncome <= 9000000) spouseDifference = 50000;
      else if (salaryIncome <= 9500000) spouseDifference = 40000;
      else if (salaryIncome <= 10000000) spouseDifference = 20000;
    }
    const humanDifference = 50000 + spouseDifference + dependents * 50000 +
      specificDependents * 180000 + elderDependents * 100000;
    let adjustmentBase = 0;
    if (salaryIncome <= 25000000 && taxableIncome > 0) {
      adjustmentBase = taxableIncome <= 2000000
        ? Math.min(humanDifference, taxableIncome)
        : Math.max(humanDifference - (taxableIncome - 2000000), 50000);
    }
    const cityAdjustment = Math.floor(adjustmentBase * 0.03);
    const metroAdjustment = Math.floor(adjustmentBase * 0.02);
    const cityIncomeLevy = incomeLevyExempt ? 0 : Math.floor(Math.max(0, taxableIncome * 0.06 - cityAdjustment) / 100) * 100;
    const metroIncomeLevy = incomeLevyExempt ? 0 : Math.floor(Math.max(0, taxableIncome * 0.04 - metroAdjustment) / 100) * 100;
    const incomeLevy = cityIncomeLevy + metroIncomeLevy;
    const perCapitaLevy = fullyExempt ? 0 : 4000;
    const forestTax = fullyExempt ? 0 : 1000;
    const annualTax = incomeLevy + perCapitaLevy + forestTax;
    const julyToMay = Math.floor(annualTax / 12 / 100) * 100;
    const june = annualTax - julyToMay * 11;
    return {
      annualSalary, salaryIncome, basicDeduction, spouseDeduction, dependentDeduction,
      socialInsurance, lifeInsuranceDeduction, earthquakeInsuranceDeduction, idecoDeduction,
      medicalExpenseDeduction, otherDeductions, totalDeductions, taxableIncome,
      humanDifference, adjustmentDeduction: cityAdjustment + metroAdjustment,
      cityIncomeLevy, metroIncomeLevy, incomeLevy, perCapitaLevy, forestTax,
      annualTax, june, julyToMay, fullyExempt, incomeLevyExempt,
      fullyExemptLimit, incomeLevyExemptLimit
    };
  }

  // 2026年のパート・アルバイト向け「年収の壁」判定。
  function incomeWall2026(options) {
    const annualSalary = clamp(options.annualSalary, 0, 10000000);
    const weeklyHours = clamp(options.weeklyHours, 0, 80);
    const age = clamp(options.age || 30, 15, 99);
    const companyEmployees = Math.floor(clamp(options.companyEmployees || 50, 1, 1000000));
    const student = Boolean(options.student);
    const afterOctober = options.afterOctober !== false;
    const healthDependentRequested = options.healthDependent !== false;
    const monthlySalary = annualSalary / 12;
    const shortTimeBase = companyEmployees >= 51 && weeklyHours >= 20 && !student;
    const employeeSocialEligible = shortTimeBase && (afterOctober || monthlySalary >= 88000);
    const dependentLimit = age >= 60 ? 1800000 : 1300000;
    const healthDependent = healthDependentRequested && !employeeSocialEligible && annualSalary < dependentLimit;
    const dependentLost = healthDependentRequested && !employeeSocialEligible && annualSalary >= dependentLimit;
    let socialInsurance = 0;
    let employmentInsurance = 0;
    let socialBreakdown = null;
    if (employeeSocialEligible) {
      socialBreakdown = socialInsurance2026({monthlySalary, annualBonus:0, age, prefecture:options.prefecture || '東京都'});
      socialInsurance = socialBreakdown.total;
      employmentInsurance = socialBreakdown.employment;
    } else if (weeklyHours >= 20 && !student) {
      employmentInsurance = Math.floor(annualSalary * 0.005);
      socialInsurance = employmentInsurance;
    }
    const salaryIncome = salaryIncome2026(annualSalary);
    const basicDeduction = incomeBasicDeduction2026(salaryIncome);
    const incomeTaxInfo = nationalIncomeTax(Math.max(0, salaryIncome - basicDeduction - socialInsurance));
    const incomeTax = incomeTaxInfo.total;
    const knownNet = Math.max(0, annualSalary - socialInsurance - incomeTax);
    const walls = [
      {amount:1100000,label:'住民税の非課税目安'},
      {amount:1230000,label:'税法上の扶養目安'},
      {amount:1300000,label:'社会保険の扶養'},
      {amount:1780000,label:'本人の所得税'}
    ];
    const nextWall = walls.find(wall => annualSalary < wall.amount) || null;
    return {
      annualSalary, monthlySalary, weeklyHours, age, companyEmployees, student, afterOctober,
      employeeSocialEligible, healthDependent, dependentLost, dependentLimit,
      socialInsurance, employmentInsurance, socialBreakdown, salaryIncome, basicDeduction,
      incomeTax, knownNet, netIsComplete:!dependentLost, nextWall,
      remainingToNextWall:nextWall ? nextWall.amount - annualSalary : 0
    };
  }

  function incomeBasicDeduction2026(totalIncome) {
    const g = Math.max(0, totalIncome);
    if (g <= 4890000) return 1040000;
    if (g <= 6550000) return 670000;
    if (g <= 23500000) return 620000;
    if (g <= 24000000) return 480000;
    if (g <= 24500000) return 320000;
    if (g <= 25000000) return 160000;
    return 0;
  }

  function spouseDeduction2026(totalIncome, eligible) {
    if (!eligible) return 0;
    const g = Math.max(0, totalIncome);
    if (g <= 9000000) return 380000;
    if (g <= 9500000) return 260000;
    if (g <= 10000000) return 130000;
    return 0;
  }

  function incomeAdjustmentDeduction2026(gross, eligible) {
    if (!eligible || gross <= 8500000) return 0;
    return Math.min(150000, Math.floor((Math.min(gross, 10000000) - 8500000) * 0.10));
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

  const BONUS_RATES_2026 = [0,2.042,4.084,6.126,8.168,10.210,12.252,14.294,16.336,18.378,20.420,22.462,24.504,26.546,28.588,30.630,32.672,35.735,38.798,41.861,45.945];
  const BONUS_THRESHOLDS_2026 = [
    [82,94,260,309,342,372,402,433,520,605,684,715,752,795,854,922,1318,1521,2621,3495,Infinity],
    [107,250,289,346,373,401,430,463,520,621,705,739,778,821,882,952,1342,1526,2645,3527,Infinity],
    [143,276,321,377,400,426,457,492,525,636,728,764,804,848,910,983,1367,1526,2669,3559,Infinity],
    [181,300,354,405,424,452,484,517,550,651,751,788,830,876,938,1013,1391,1538,2693,3590,Infinity],
    [218,300,387,431,452,477,509,540,577,666,774,813,856,903,966,1044,1416,1555,2716,3622,Infinity],
    [251,304,412,457,479,503,531,564,604,681,798,838,881,930,994,1074,1440,1555,2740,3654,Infinity],
    [284,343,438,483,505,527,553,589,630,697,821,862,907,957,1022,1104,1464,1555,2764,3685,Infinity],
    [317,383,463,508,529,552,578,614,657,708,845,887,933,985,1051,1135,1489,1583,2788,3717,Infinity]
  ];

  function bonusWithholdingRate2026(previousAfterSocial, dependents, declarationFiled) {
    const baseThousands = Math.max(0, Number(previousAfterSocial) || 0) / 1000;
    if (!declarationFiled) {
      if (baseThousands < 224) return 0.10210;
      if (baseThousands < 295) return 0.20420;
      if (baseThousands < 527) return 0.30630;
      if (baseThousands < 1118) return 0.38798;
      return 0.45945;
    }
    const count = Math.min(7, Math.max(0, Math.floor(Number(dependents) || 0)));
    const thresholds = BONUS_THRESHOLDS_2026[count];
    const index = thresholds.findIndex(upper => baseThousands < upper);
    return BONUS_RATES_2026[index < 0 ? BONUS_RATES_2026.length - 1 : index] / 100;
  }

  function bonusTakeHome2026(options) {
    const bonus = clamp(options.bonus, 0, 100000000);
    const previousSalary = clamp(options.previousSalary, 0, 5000000);
    const age = clamp(options.age || 30, 18, 69);
    const prefecture = HEALTH_RATES_2026[options.prefecture] ? options.prefecture : '東京都';
    const dependents = clamp(options.dependents, 0, 20);
    const declarationFiled = options.declarationFiled !== false;
    const healthCumulativeBefore = clamp(options.healthCumulativeBefore, 0, 5730000);
    const pensionSameMonthBefore = clamp(options.pensionSameMonthBefore, 0, 1500000);
    const standardBonus = Math.floor(bonus / 1000) * 1000;
    const healthBonusBase = Math.max(0, Math.min(standardBonus, 5730000 - healthCumulativeBefore));
    const pensionBonusBase = Math.max(0, Math.min(standardBonus, 1500000 - pensionSameMonthBefore));
    const healthRate = HEALTH_RATES_2026[prefecture] / 100;
    const careRate = age >= 40 && age <= 64 ? 0.0162 : 0;
    const supportRate = 0.0023;
    const pensionRate = 0.183;
    const employmentRate = 0.005;
    const health = Math.round(healthBonusBase * healthRate / 2);
    const care = Math.round(healthBonusBase * careRate / 2);
    const childSupport = Math.round(healthBonusBase * supportRate / 2);
    const pension = Math.round(pensionBonusBase * pensionRate / 2);
    const employment = Math.floor(bonus * employmentRate);
    const socialTotal = health + care + childSupport + pension + employment;
    const healthStandard = standardAmount(previousSalary, HEALTH_STANDARDS);
    const pensionStandard = standardAmount(previousSalary, PENSION_STANDARDS);
    const previousSocialAuto = Math.round(healthStandard * healthRate / 2) +
      Math.round(healthStandard * careRate / 2) + Math.round(healthStandard * supportRate / 2) +
      Math.round(pensionStandard * pensionRate / 2) + Math.floor(previousSalary * employmentRate);
    const previousSocial = Number(options.previousSocial) > 0 ? clamp(options.previousSocial, 0, previousSalary) : previousSocialAuto;
    const previousAfterSocial = Math.max(0, previousSalary - previousSocial);
    const withholdingRate = bonusWithholdingRate2026(previousAfterSocial, dependents, declarationFiled);
    const taxableBonus = Math.max(0, bonus - socialTotal);
    const incomeTax = Math.floor(taxableBonus * withholdingRate);
    const net = Math.max(0, bonus - socialTotal - incomeTax);
    const exceptional = previousAfterSocial <= 0 || taxableBonus > previousAfterSocial * 10;
    return {
      bonus, net, standardBonus, healthBonusBase, pensionBonusBase, health, care, childSupport,
      pension, employment, socialTotal, previousSocial, previousAfterSocial, withholdingRate,
      taxableBonus, incomeTax, exceptional, netRate: bonus ? net / bonus : 0
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
    const spouseDeduction = spouseDeduction2026(salaryIncome, spouse);
    const dependentIncomeDeduction = dependents * 380000 + spouseDeduction + specificDependents * 630000 + elderDependents * 480000;
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
    const spouseDeduction = spouseDeduction2026(salaryIncome, spouse);
    const incomeDependentDeduction = dependents * 380000 + spouseDeduction + specificDependents * 630000 + elderDependents * 480000;
    const residentDependentDeduction = (dependents + spouse) * 330000 + specificDependents * 450000 + elderDependents * 380000;
    const incomeTaxable = Math.max(0, salaryIncome - incomeBasicDeduction2026(salaryIncome) - social.total - incomeDependentDeduction);
    const incomeInfo = nationalIncomeTax(incomeTaxable);
    const residentTaxable = Math.floor(Math.max(0, salaryIncome - 430000 - social.total - residentDependentDeduction) / 1000) * 1000;
    const residentIncomeLevy = Math.floor(residentTaxable * 0.10 / 100) * 100;
    const denominator = 0.90 - incomeInfo.rate * 1.021;
    const limit = denominator > 0 ? Math.max(0, Math.floor((residentIncomeLevy * 0.20 / denominator + 2000) / 1000) * 1000) : 0;
    return { annualSalary, salaryIncome, socialInsurance: social.total, incomeTaxable: incomeInfo.taxable, marginalRate: incomeInfo.rate, residentTaxable, residentIncomeLevy, limit };
  }

  function yearEndAdjustment2026(options) {
    const annualSalary = clamp(options.annualSalary, 0, 100000000);
    const withheldTax = clamp(options.withheldTax, 0, 50000000);
    const socialInsurance = clamp(options.socialInsurance, 0, 30000000);
    const lifeInsuranceDeduction = clamp(options.lifeInsuranceDeduction, 0, 120000);
    const earthquakeInsuranceDeduction = clamp(options.earthquakeInsuranceDeduction, 0, 50000);
    const idecoDeduction = clamp(options.idecoDeduction, 0, 10000000);
    const otherDeductions = clamp(options.otherDeductions, 0, 30000000);
    const housingLoanCredit = clamp(options.housingLoanCredit, 0, 10000000);
    const dependents = clamp(options.dependents, 0, 10);
    const specificDependents = clamp(options.specificDependents, 0, 10);
    const elderDependents = clamp(options.elderDependents, 0, 10);
    const specialRelativeDeduction = clamp(options.specialRelativeDeduction, 0, 630000);
    const incomeBeforeAdjustment = salaryIncome2026(annualSalary);
    const incomeAdjustment = incomeAdjustmentDeduction2026(annualSalary, Boolean(options.incomeAdjustmentEligible));
    const salaryIncome = Math.max(0, incomeBeforeAdjustment - incomeAdjustment);
    const basicDeduction = incomeBasicDeduction2026(salaryIncome);
    const spouseDeduction = spouseDeduction2026(salaryIncome, Boolean(options.spouse));
    const dependentDeduction = dependents * 380000 + specificDependents * 630000 + elderDependents * 480000;
    const totalDeductions = basicDeduction + socialInsurance + lifeInsuranceDeduction + earthquakeInsuranceDeduction +
      idecoDeduction + otherDeductions + spouseDeduction + dependentDeduction + specialRelativeDeduction;
    const taxableIncome = Math.floor(Math.max(0, salaryIncome - totalDeductions) / 1000) * 1000;
    const incomeTaxInfo = nationalIncomeTax(taxableIncome);
    const taxAfterCredit = Math.max(0, incomeTaxInfo.baseTax - housingLoanCredit);
    const annualTax = Math.floor(taxAfterCredit * 1.021 / 100) * 100;
    const balance = Math.floor(withheldTax - annualTax);
    return {
      annualSalary, withheldTax, incomeBeforeAdjustment, incomeAdjustment, salaryIncome,
      basicDeduction, spouseDeduction, dependentDeduction, specialRelativeDeduction,
      socialInsurance, lifeInsuranceDeduction, earthquakeInsuranceDeduction, idecoDeduction,
      otherDeductions, totalDeductions, taxableIncome, baseTax: incomeTaxInfo.baseTax,
      housingLoanCredit, annualTax, balance, refund: Math.max(0, balance), additional: Math.max(0, -balance)
    };
  }

  return {
    HEALTH_RATES_2026, salaryIncome2026, residentSalaryIncome2026,
    residentBasicDeduction2026, residentSpouseDeduction2026, residentTax2026, incomeWall2026,
    incomeBasicDeduction2026,
    spouseDeduction2026, incomeAdjustmentDeduction2026, nationalIncomeTax,
    socialInsurance2026, bonusWithholdingRate2026, bonusTakeHome2026,
    takeHome2026, furusatoLimit2026, yearEndAdjustment2026
  };
});
