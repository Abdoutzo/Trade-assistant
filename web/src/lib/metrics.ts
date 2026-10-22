// The annual figures shown on a company page, in reading order, with a one-line explanation:
// the first step of the guide (brick 6) is to know what each line means.

export const METRICS: { key: string; label: string; help: string }[] = [
  { key: "revenue", label: "Chiffre d'affaires", help: "Total des ventes de l'année. Il doit croître dans la durée." },
  { key: "gross_profit", label: "Marge brute", help: "Ventes moins le coût direct des produits vendus." },
  { key: "operating_income", label: "Résultat opérationnel", help: "Ce que rapporte le métier, avant intérêts et impôts." },
  { key: "ebitda", label: "EBITDA", help: "Résultat opérationnel avant amortissements : proche du cash généré par l'activité." },
  { key: "net_income", label: "Résultat net", help: "Le bénéfice final revenant aux actionnaires, après tout." },
  { key: "eps_diluted", label: "Bénéfice par action", help: "Résultat net divisé par le nombre d'actions. Sa croissance tire le cours à long terme." },
  { key: "operating_cash_flow", label: "Flux de trésorerie opérationnel", help: "L'argent réellement encaissé par l'activité. Plus difficile à maquiller que le résultat." },
  { key: "capex", label: "Investissements (capex)", help: "Argent dépensé en usines, machines, logiciels pour maintenir et développer l'activité." },
  { key: "free_cash_flow", label: "Flux de trésorerie disponible", help: "Cash opérationnel moins investissements : ce qui reste pour dividendes, rachats, dette." },
  { key: "dividends_paid", label: "Dividendes versés", help: "Argent rendu aux actionnaires dans l'année." },
  { key: "equity", label: "Capitaux propres", help: "Ce qui appartient aux actionnaires : actifs moins dettes." },
  { key: "total_debt", label: "Dette financière", help: "Emprunts et obligations. À comparer au cash généré chaque année." },
  { key: "cash", label: "Trésorerie", help: "L'argent disponible immédiatement." },
  { key: "total_assets", label: "Total du bilan", help: "Tout ce que possède l'entreprise." },
  { key: "invested_capital", label: "Capitaux investis", help: "Capital mis au travail (fonds propres + dette). Sert à calculer le ROIC." },
  { key: "shares", label: "Nombre d'actions", help: "S'il baisse, l'entreprise rachète ses actions ; s'il monte, elle dilue ses actionnaires." },
];
