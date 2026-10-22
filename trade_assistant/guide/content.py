"""The investor's guide: chapters, quizzes and glossary, written for a beginner investing monthly
through a PEA at Trade Republic. Facts checked in October 2026 (taxes: LFSS 2026).

Each chapter: a few short sections, the key takeaways, links to the place in the tool where the
notion is used, and a quiz whose explanations matter as much as the answers.
"""
from __future__ import annotations

CHAPTERS: list[dict] = [
    {
        "id": "bases",
        "title": "Les bases : action, ETF, indice",
        "level": "Débutant",
        "minutes": 6,
        "sections": [
            ("Une action, c'est un morceau d'entreprise",
             "Acheter une action d'Air Liquide, c'est devenir copropriétaire d'Air Liquide, pour une part minuscule. "
             "Tu as droit à ta part des bénéfices : une partie t'est versée en **dividende**, le reste est réinvesti "
             "par l'entreprise pour grandir. Sur le long terme, le cours d'une action suit surtout une chose : "
             "**la croissance des bénéfices par action**. Au jour le jour, il suit l'humeur du marché."),
            ("Un indice, c'est un panier de référence",
             "Le **CAC 40** regroupe 40 grandes entreprises françaises, le **MSCI World** environ 1 500 grandes "
             "entreprises de 23 pays développés. Un indice sert de thermomètre : quand on dit que « le marché a "
             "fait +10 % », on parle d'un indice."),
            ("Un ETF, c'est un indice que l'on peut acheter",
             "Un **ETF** (ou tracker) est un fonds coté qui reproduit un indice. En achetant une part de l'ETF "
             "Amundi PEA Monde, tu achètes en une fois un petit morceau des 1 500 entreprises du MSCI World, pour "
             "des frais de gestion très bas (environ 0,2 % par an). C'est la façon la plus simple et la moins chère "
             "de diversifier."),
            ("Rendement et risque vont ensemble",
             "Les actions rapportent plus que le livret A sur longue période (environ 7 % par an en moyenne pour les "
             "actions mondiales, sur un siècle), mais au prix de chutes régulières : -20 %, -30 %, parfois -50 %. "
             "Ce n'est pas un défaut du système : c'est précisément parce qu'elles font peur que les actions "
             "rapportent davantage. Il n'existe pas de placement à fort rendement et sans risque : si on t'en promet "
             "un, c'est une arnaque."),
        ],
        "takeaways": [
            "Une action = une part d'entreprise ; à long terme son cours suit les bénéfices.",
            "Un ETF = tout un indice en une seule ligne, pour des frais très faibles.",
            "Plus de rendement espéré = plus de secousses à supporter. Toujours.",
        ],
        "links": [("/analyses", "Univers et analyses : les actions et les ETF suivis")],
        "glossary": ["action", "dividende", "indice", "etf", "msci_world"],
        "quiz": [
            ("À long terme, qu'est-ce qui fait surtout monter le cours d'une action ?",
             ["Les avis des analystes", "La croissance des bénéfices par action", "Le nombre d'articles de presse"],
             1, "L'humeur du marché domine sur quelques mois, mais sur 10 ans le cours suit les bénéfices par action."),
            ("Qu'achètes-tu avec une part d'ETF MSCI World ?",
             ["Une seule grande entreprise américaine", "Un morceau d'environ 1 500 entreprises", "Une obligation d'État"],
             1, "L'ETF reproduit l'indice : une part contient un peu de chacune de ses entreprises."),
            ("Un placement promet 15 % par an sans aucun risque. C'est :",
             ["Une bonne affaire", "Probablement une arnaque", "Normal pour un ETF"],
             1, "Rendement élevé et absence de risque ne vont jamais ensemble. Méfiance absolue."),
        ],
    },
    {
        "id": "pea",
        "title": "Le PEA et Trade Republic",
        "level": "Débutant",
        "minutes": 7,
        "sections": [
            ("L'enveloppe fiscale la plus avantageuse pour les actions",
             "Le **PEA** (plan d'épargne en actions) est un compte-titres avec un avantage fiscal. Après **5 ans** "
             "(comptés depuis le premier versement), les gains sont exonérés d'impôt sur le revenu : seuls restent "
             "les prélèvements sociaux, **18,6 % depuis 2026**. Sur un compte-titres ordinaire, les gains subissent "
             "la flat tax de **31,4 %** (12,8 % d'impôt + 18,6 % de prélèvements sociaux). Sur 20 ans, la "
             "différence se compte en milliers d'euros."),
            ("Les règles à connaître",
             "Versements plafonnés à **150 000 €** (les gains, eux, ne sont pas plafonnés). Avant 5 ans, un retrait "
             "clôture le plan et les gains sont taxés à 31,4 % (sauf exceptions : licenciement, invalidité, création "
             "d'entreprise...). Après 5 ans, tu peux retirer une partie sans clôturer et continuer à verser. "
             "Conseil classique : **ouvre-le tôt**, même avec peu, pour faire courir le délai de 5 ans."),
            ("Ce que l'on peut y mettre",
             "Des actions d'entreprises dont le siège est dans l'Union européenne ou l'Espace économique européen "
             "(ASML, LVMH, SAP, Novo Nordisk : oui ; Apple, Nestlé : non), et des ETF construits pour être éligibles. "
             "Les ETF « PEA Monde » ou « PEA S&P 500 » détiennent en réalité des actions européennes et échangent "
             "leur performance contre celle de l'indice voulu (réplication **synthétique**, par swap) : c'est légal, "
             "encadré, et c'est ce qui permet d'avoir le monde entier dans un PEA."),
            ("Trade Republic : les plans programmés sont gratuits",
             "Chez Trade Republic, un ordre ponctuel coûte **1 €** ; un **plan d'investissement programmé** ne coûte "
             "rien et peut acheter des fractions d'action (10 € d'Hermès, même si une action vaut plus de 1 000 €). "
             "D'où la règle de l'outil : des plans mensuels à montant fixe, que tu ne modifies que lorsque le plan "
             "du mois change. Un ordre de 10 € à 1 € de frais, c'est 10 % perdus d'entrée."),
        ],
        "takeaways": [
            "Après 5 ans : 18,6 % sur les gains au lieu de 31,4 %. Ouvre le PEA tôt.",
            "Actions européennes et ETF éligibles uniquement ; les ETF monde passent par un swap.",
            "Plans programmés gratuits, ordres ponctuels à 1 € : privilégie les plans.",
        ],
        "links": [("/portefeuille", "Portefeuille : tes plans programmés du mois"),
                  ("/reglages", "Réglages : enveloppe et horizon")],
        "glossary": ["pea", "flat_tax", "prelevements_sociaux", "plan_programme", "replication_synthetique"],
        "quiz": [
            ("Ton PEA a 6 ans et a gagné 2 000 €. Combien d'impôts et prélèvements sur ces gains (règles 2026) ?",
             ["0 €", "372 € (18,6 %)", "628 € (31,4 %)"],
             1, "Après 5 ans, seuls les prélèvements sociaux s'appliquent : 18,6 % de 2 000 € = 372 €."),
            ("Peux-tu acheter des actions Apple dans un PEA ?",
             ["Oui", "Non, son siège n'est pas dans l'UE/EEE", "Oui, mais seulement via un plan programmé"],
             1, "Seules les sociétés de l'UE/EEE sont éligibles. Pour Apple, il faut un ETF éligible (S&P 500 PEA, MSCI World PEA)."),
            ("Pourquoi l'outil propose-t-il des plans programmés plutôt que des ordres chaque mois ?",
             ["Ils sont plus rapides", "Ils sont gratuits alors qu'un ordre coûte 1 €", "Ils rapportent plus"],
             1, "Sur 10 € investis, 1 € de frais représente 10 % : un handicap énorme. Les plans programmés sont gratuits."),
        ],
    },
    {
        "id": "dca",
        "title": "Investir chaque mois et laisser le temps travailler",
        "level": "Débutant",
        "minutes": 6,
        "sections": [
            ("Les intérêts composés",
             "Un gain de 7 % la première année produit lui-même des gains les années suivantes. 10 000 € placés à "
             "7 % par an deviennent environ 19 700 € en 10 ans, et **76 000 €** en 30 ans : les dernières années "
             "rapportent bien plus que les premières. Le facteur le plus puissant n'est ni le choix des actions ni "
             "le montant : c'est **la durée**."),
            ("Le versement programmé (DCA)",
             "Investir la même somme chaque mois (en anglais *dollar cost averaging*) achète automatiquement plus de "
             "parts quand les prix sont bas et moins quand ils sont hauts. Surtout, il supprime la question "
             "impossible « est-ce le bon moment ? ». Avec 500 € au départ puis 100 € par mois à 7 % par an, tu "
             "aurais environ **18 100 €** au bout de 10 ans pour 12 500 € versés, et environ **52 700 €** au bout "
             "de 20 ans pour 24 500 € versés. À taux constant ; la réalité sera plus heurtée."),
            ("Ne pas jouer au plus malin avec le marché",
             "Les meilleures journées de bourse arrivent souvent en pleine crise, juste après les pires. Celui qui "
             "vend pour « attendre que ça se calme » rate presque toujours le rebond. La règle du programme est "
             "simple : **on continue les versements, surtout quand ça baisse**."),
            ("Une baisse se rattrape plus difficilement qu'on ne croit",
             "Après -50 %, il faut +100 % pour revenir au point de départ. C'est pourquoi l'outil limite chaque "
             "action à 10 % du portefeuille et garde un cœur ETF diversifié : éviter les très grosses pertes compte "
             "plus que viser les très gros gains."),
        ],
        "takeaways": [
            "Le temps est le premier moteur du rendement : commencer tôt vaut plus que choisir parfaitement.",
            "Verser chaque mois supprime la question du « bon moment ».",
            "Une perte de 50 % demande un gain de 100 % : éviter les grosses pertes avant tout.",
        ],
        "links": [("/", "Tableau de bord : projection de ton épargne"),
                  ("/portefeuille", "Portefeuille : simulation sur 10 ans")],
        "glossary": ["interets_composes", "dca", "drawdown"],
        "quiz": [
            ("Ton portefeuille perd 50 %. Quel gain faut-il ensuite pour revenir au point de départ ?",
             ["+50 %", "+100 %", "+25 %"],
             1, "100 € deviennent 50 € ; pour revenir à 100 €, il faut doubler : +100 %."),
            ("Le marché chute de 25 % en un mois. Que prévoit la stratégie ?",
             ["Tout vendre et attendre", "Continuer les versements mensuels", "Mettre tout son livret A d'un coup"],
             1, "On continue les versements : ils achètent à prix réduit. Vendre en panique fige la perte et fait rater le rebond."),
            ("Quel facteur pèse le plus sur le résultat final d'une épargne en actions ?",
             ["Le choix de la meilleure action", "La durée de placement", "La date exacte du premier achat"],
             1, "Les intérêts composés font l'essentiel du travail sur la durée."),
        ],
    },
    {
        "id": "diversification",
        "title": "Le cœur ETF et la diversification",
        "level": "Intermédiaire",
        "minutes": 6,
        "sections": [
            ("Pourquoi un cœur d'ETF monde",
             "Sur 10 ou 15 ans, la grande majorité des fonds gérés par des professionnels font **moins bien** que "
             "leur indice, une fois leurs frais déduits. Choisir des actions est difficile, même à temps plein. Le "
             "cœur ETF monde (70 % de tes versements par défaut) te garantit au moins la performance du marché, "
             "pour presque rien."),
            ("La diversification protège de ce qu'on ne voit pas venir",
             "Une entreprise excellente peut s'effondrer : scandale, technologie dépassée, fraude, procès. Dans un "
             "ETF de 1 500 sociétés, la faillite de l'une d'elles est invisible. Dans un portefeuille de 3 actions, "
             "elle est dramatique. D'où les deux règles de l'outil : **10 % maximum par action** et **2 actions "
             "par secteur au plus**."),
            ("Les limites du MSCI World",
             "Il est très exposé aux États-Unis (autour de 70 % aujourd'hui, la proportion varie avec le temps) et "
             "à quelques géants technologiques. Ce n'est pas un problème en soi, c'est la taille réelle de ces "
             "entreprises, mais il faut le savoir : tes actions européennes satellites apportent un peu "
             "d'équilibre."),
            ("Ce que montre la simulation de l'outil",
             "Rejouée sur 10 ans, la stratégie 70/30 avec les meilleures actions d'aujourd'hui a fait **moins bien** "
             "que l'ETF seul, alors même qu'elle profitait du recul. Elle a été un peu plus calme. Les satellites "
             "sont là pour apprendre et pour un petit potentiel en plus, pas pour garantir mieux que le marché."),
        ],
        "takeaways": [
            "La plupart des professionnels ne battent pas leur indice : le cœur ETF est un choix rationnel.",
            "Diversifier, c'est se protéger de l'imprévisible, pas réduire ses gains.",
            "Les satellites restent minoritaires et plafonnés.",
        ],
        "links": [("/portefeuille", "Portefeuille : simulation 70/30 contre 100 % ETF"),
                  ("/reglages", "Réglages : part ETF, plafond par action")],
        "glossary": ["diversification", "ter", "coeur_satellites"],
        "quiz": [
            ("Pourquoi l'outil met-il la majorité des versements sur un ETF monde ?",
             ["Parce qu'il rapporte toujours plus que les actions", "Parce que la plupart des gérants ne battent pas l'indice",
              "Parce que c'est obligatoire dans un PEA"],
             1, "Battre l'indice durablement est rare ; l'ETF garantit la performance du marché pour des frais minimes."),
            ("Une action de ton portefeuille fait faillite. Elle pesait 10 %. Que perds-tu ?",
             ["1 % du portefeuille", "10 % du portefeuille", "Tout le portefeuille"],
             1, "La perte totale d'une ligne de 10 % coûte 10 % du portefeuille. D'où le plafond : jamais plus de 10 % sur une action."),
            ("Pourquoi limiter à 2 actions par secteur ?",
             ["Pour payer moins de frais", "Parce qu'un même choc frappe tout un secteur", "C'est une règle du PEA"],
             1, "Une crise du luxe en Chine touche LVMH, Hermès et Kering en même temps."),
        ],
    },
    {
        "id": "comptes",
        "title": "Lire les comptes d'une entreprise",
        "level": "Intermédiaire",
        "minutes": 8,
        "sections": [
            ("Le compte de résultat : ce que l'entreprise gagne",
             "Il part du **chiffre d'affaires** (les ventes), retire les coûts pour donner le **résultat "
             "opérationnel** (ce que rapporte le métier), puis les intérêts et l'impôt pour arriver au **résultat "
             "net** (le bénéfice des actionnaires). Divisé par le nombre d'actions, il donne le **bénéfice par "
             "action** (BPA)."),
            ("Le tableau des flux de trésorerie : l'argent réellement encaissé",
             "Le bénéfice est une construction comptable ; la trésorerie, elle, est difficile à maquiller. Le **flux "
             "de trésorerie opérationnel** moins les **investissements** (capex : usines, machines, logiciels) donne "
             "le **flux de trésorerie disponible** (free cash flow) : l'argent qui reste pour payer les dividendes, "
             "racheter des actions ou rembourser la dette. Une entreprise dont le bénéfice ne se transforme jamais "
             "en cash mérite des questions."),
            ("Le bilan : ce que l'entreprise possède et doit",
             "D'un côté les actifs (usines, stocks, trésorerie), de l'autre ce qui les finance : les **capitaux "
             "propres** (l'argent des actionnaires) et la **dette**. Une dette élevée amplifie tout : les bonnes "
             "années comme les mauvaises."),
            ("D'où viennent les chiffres de l'outil",
             "Des **rapports annuels officiels** que les sociétés cotées dans l'UE publient au format ESEF (chiffres "
             "audités, point vert dans les tableaux), complétés par Yahoo pour les années récentes. Attention aux "
             "normes : ASML publie ses comptes européens en IFRS et ses comptes américains en US GAAP, avec des "
             "écarts de 10 à 20 %. L'outil ne mélange jamais les deux dans un même ratio."),
        ],
        "takeaways": [
            "Chiffre d'affaires → résultat opérationnel → résultat net → bénéfice par action.",
            "Le cash disponible (FCF) est plus fiable que le bénéfice comptable.",
            "La dette amplifie les bonnes comme les mauvaises années.",
        ],
        "links": [("/analyses", "Ouvre une fiche : le tableau « Comptes annuels » et ses définitions")],
        "glossary": ["chiffre_affaires", "resultat_operationnel", "resultat_net", "bpa", "fcf", "capex",
                     "capitaux_propres", "esef", "ifrs"],
        "quiz": [
            ("Quel chiffre est le plus difficile à « embellir » par la comptabilité ?",
             ["Le résultat net", "Le flux de trésorerie", "Le chiffre d'affaires ajusté"],
             1, "Les flux de trésorerie mesurent l'argent réellement entré et sorti : beaucoup moins de marge d'interprétation."),
            ("Free cash flow = ?",
             ["Chiffre d'affaires - impôts", "Flux de trésorerie opérationnel - investissements", "Résultat net + dette"],
             1, "C'est le cash qui reste une fois l'outil de production entretenu et développé."),
            ("Pourquoi un point vert à côté d'un chiffre dans l'outil ?",
             ["Il est en hausse", "Il vient du rapport annuel officiel audité", "Il est estimé par l'IA"],
             1, "Point vert = rapport ESEF officiel. Sans point : Yahoo Finance. Jamais l'IA."),
        ],
    },
    {
        "id": "qualite",
        "title": "Reconnaître une entreprise de qualité",
        "level": "Intermédiaire",
        "minutes": 7,
        "sections": [
            ("La rentabilité du capital : le critère roi",
             "Le **ROIC** (rentabilité du capital investi) mesure combien rapporte chaque euro mis au travail dans "
             "l'entreprise, qu'il vienne des actionnaires ou des prêteurs. Au-dessus de 15 % durablement, "
             "l'entreprise a un **avantage concurrentiel** (marque, technologie, réseau, coûts) que les concurrents "
             "n'arrivent pas à copier. Sous 7 %, elle rapporte à peine plus que ce que coûte son financement."),
            ("Les marges et leur stabilité",
             "Une **marge opérationnelle** élevée et stable signale un pouvoir de fixer ses prix : Hermès ou ASML "
             "peuvent augmenter leurs tarifs sans perdre de clients. Une marge qui s'effrite année après année est "
             "un signal d'alarme, même si les ventes progressent."),
            ("La solidité financière",
             "La **dette nette / EBITDA** dit en combien d'années le résultat brut rembourserait la dette : sous 2, "
             "c'est confortable ; au-dessus de 3,5, une mauvaise année peut devenir dangereuse. La **couverture des "
             "intérêts** (résultat / charges d'intérêts) dit si l'entreprise paie facilement ses intérêts."),
            ("Les banques et assurances sont à part",
             "Pour elles, la dette est la matière première du métier : marges, cash et endettement ne se lisent pas "
             "comme pour un industriel. L'outil les juge sur la rentabilité des fonds propres (ROE) et le prix payé "
             "pour leurs fonds propres, et signale que leur solidité réelle (ratios de solvabilité) n'est pas "
             "disponible gratuitement."),
        ],
        "takeaways": [
            "ROIC durablement > 15 % = avantage concurrentiel probable.",
            "Des marges hautes et stables valent mieux que des ventes en forte hausse.",
            "Dette nette / EBITDA > 3,5 : prudence.",
        ],
        "links": [("/classement", "Classement : piliers Qualité et Solidité"),
                  ("/analyses", "Fiche d'une entreprise : déplie le pilier Qualité")],
        "glossary": ["roic", "roe", "marge_operationnelle", "ebitda", "dette_nette_ebitda", "avantage_concurrentiel"],
        "quiz": [
            ("Une entreprise affiche un ROIC de 25 % depuis 10 ans. Cela suggère :",
             ["Une entreprise très endettée", "Un avantage concurrentiel durable", "Une action bon marché"],
             1, "Une rentabilité élevée qui dure signifie que les concurrents n'arrivent pas à la rattraper. Mais cela ne dit rien du prix de l'action."),
            ("Dette nette / EBITDA de 5. Que retenir ?",
             ["Endettement confortable", "Endettement à surveiller de près", "Ce ratio ne veut rien dire"],
             1, "5 années de résultat brut pour rembourser : une mauvaise année ou une hausse des taux peut faire mal."),
            ("Pourquoi l'outil ne calcule-t-il pas de marge opérationnelle pour BNP Paribas ?",
             ["Faute de données", "Ce ratio n'a pas de sens pour une banque", "Parce qu'elle n'est pas éligible au PEA"],
             1, "Pour une banque, la dette est l'activité même : les ratios industriels induisent en erreur."),
        ],
    },
    {
        "id": "valorisation",
        "title": "Le prix : une bonne entreprise peut être un mauvais placement",
        "level": "Intermédiaire",
        "minutes": 7,
        "sections": [
            ("Le PER",
             "Le **PER** (cours / bénéfice par action) dit combien d'années de bénéfice actuel tu paies. Autour de "
             "15 : prix moyen. Au-dessus de 25 : le marché attend une forte croissance, et la moindre déception "
             "coûte cher. Un PER bas n'est pas forcément une affaire : parfois le marché anticipe, à raison, une "
             "baisse des bénéfices (c'est le « piège à valeur »)."),
            ("Comparer à soi-même et à ses voisins",
             "Le PER d'une entreprise **par rapport à son propre historique** est souvent plus parlant que le chiffre "
             "brut : Hermès à 30 fois ses bénéfices est historiquement bon marché, une banque à 15 est chère. L'outil "
             "affiche aussi la médiane du secteur dans l'univers."),
            ("Le rendement du cash",
             "Le **rendement du free cash flow** (cash disponible / capitalisation) est le « loyer » que rapporte "
             "l'entreprise au prix actuel. Au-dessus de 5 % : bon marché ; sous 2 % : cher. Il inclut ce qui sert "
             "au dividende et aux rachats d'actions."),
            ("La leçon la plus importante",
             "Une entreprise exceptionnelle achetée beaucoup trop cher peut rapporter peu pendant 10 ans. "
             "Inversement, une entreprise moyenne achetée très bon marché peut bien rapporter. La note de l'outil "
             "sépare donc la **qualité** de la **valorisation**, et c'est leur combinaison qui compte."),
        ],
        "takeaways": [
            "PER ≈ 15 : moyen ; > 25 : beaucoup de croissance attendue.",
            "Compare le PER à l'historique de l'entreprise et à son secteur.",
            "Qualité et prix sont deux questions distinctes : il faut les deux.",
        ],
        "links": [("/classement", "Classement : trie par PER ou par Valorisation")],
        "glossary": ["per", "capitalisation", "rendement_fcf", "ve_ebit", "piege_valeur", "rendement_dividende"],
        "quiz": [
            ("Une action a un PER de 8, très bas pour son secteur. Que faut-il se demander d'abord ?",
             ["Combien en acheter", "Pourquoi le marché la paie si peu cher", "Rien, c'est une affaire"],
             1, "Un prix bas a souvent une raison : bénéfices attendus en baisse, risque juridique, dette... Vérifie avant de conclure."),
            ("Le PER d'Hermès est passé de 50 à 30. Son PER par rapport à l'historique vaut 0,62. Cela signifie :",
             ["Hermès est en faillite", "Hermès est moins chère que d'habitude", "Hermès ne verse plus de dividende"],
             1, "Sous 1 : moins cher que sa moyenne passée. Reste à savoir si la baisse est justifiée (Chine)."),
            ("Rendement du free cash flow de 7 % : c'est plutôt...",
             ["Cher", "Bon marché", "Sans importance"],
             1, "Chaque année, l'entreprise produit 7 % de sa valeur boursière en cash disponible : c'est généreux."),
        ],
    },
    {
        "id": "risque",
        "title": "Le risque et les pièges de notre cerveau",
        "level": "Intermédiaire",
        "minutes": 7,
        "sections": [
            ("Mesurer le risque",
             "La **volatilité** mesure l'amplitude habituelle des variations (20 % : une année normale peut finir "
             "entre -20 % et +20 %). La **pire baisse** (drawdown) dit ce qu'il aurait fallu endurer sans vendre. "
             "Le **bêta** dit si l'action amplifie le marché (1,3 : +-13 % quand le marché fait +-10 %). Avant "
             "d'acheter, demande-toi : « supporterais-je de voir cette ligne à -50 % ? »"),
            ("Nos biais nous coûtent de l'argent",
             "**Aversion aux pertes** : une perte fait deux fois plus mal qu'un gain ne fait plaisir, ce qui pousse à "
             "vendre au pire moment. **Peur de rater** : on achète ce qui a déjà beaucoup monté. **Excès de "
             "confiance** : on surestime sa capacité à choisir. **Biais de confirmation** : on ne lit que ce qui "
             "conforte son avis. **Biais rétrospectif** : après coup, tout semblait évident."),
            ("Les règles plutôt que l'humeur",
             "D'où les règles écrites à l'avance : versements automatiques, plafond par ligne, un avocat du diable "
             "qui attaque chaque idée, et un **journal** qui compare honnêtement les décisions au simple ETF. Une "
             "règle décidée au calme protège des décisions prises sous le coup de l'émotion."),
            ("L'IA aussi se trompe",
             "L'agent de l'outil est un assistant, pas un oracle. Il peut mal comprendre une actualité ou faire une "
             "erreur de calcul : c'est arrivé dans une de ses premières leçons, qui affirmait qu'une perte totale "
             "sur une ligne de 10 % ne coûtait que 1 % du capital (c'est 10 %). D'où les faits cités, les chiffres "
             "vérifiés, et **ta validation** à chaque plan."),
        ],
        "takeaways": [
            "Volatilité, pire baisse et bêta disent ce qu'il faudra supporter.",
            "Nos biais poussent à acheter haut et vendre bas : des règles écrites nous en protègent.",
            "Vérifie ce que dit l'IA : elle aussi peut se tromper.",
        ],
        "links": [("/plan", "Plan du mois : l'avocat du diable et les faits cités"),
                  ("/analyses", "Fiche : pilier Risque de marché")],
        "glossary": ["volatilite", "drawdown", "beta", "aversion_pertes", "biais_retrospectif"],
        "quiz": [
            ("Une action a perdu 77 % au pire sur 5 ans. Ce chiffre est :",
             ["Le drawdown maximal", "La volatilité", "Le bêta"],
             0, "C'est la pire baisse depuis un sommet : ce qu'un actionnaire aurait dû endurer."),
            ("Tu veux acheter une action qui a fait +60 % en un an parce que « tout le monde en parle ». Quel biais te guette ?",
             ["Aversion aux pertes", "Peur de rater (FOMO)", "Biais rétrospectif"],
             1, "Acheter après une forte hausse sous l'effet de l'enthousiasme collectif, c'est souvent acheter cher."),
            ("L'IA écrit qu'une perte totale sur une ligne de 10 % coûte 1 % du capital. Que fais-tu ?",
             ["Je la crois, c'est une IA", "Je vérifie : c'est 10 % du capital", "J'arrête d'investir"],
             1, "10 % du portefeuille perdu entièrement = 10 % du capital. Toujours refaire le calcul."),
        ],
    },
    {
        "id": "actualite",
        "title": "Lire l'actualité sans se faire piéger",
        "level": "Avancé",
        "minutes": 5,
        "sections": [
            ("Bruit et signal",
             "La plupart des articles boursiers sont du **bruit** : « l'action recule de 0,8 % », listes de "
             "recommandations, commentaires de séance. Un **signal** change la valeur de l'entreprise à long terme : "
             "avertissement sur les résultats, acquisition importante, procès lourd, départ du dirigeant, "
             "changement de stratégie, baisse du dividende."),
            ("Les avis d'analystes",
             "Un analyste qui relève son objectif de 192 à 193 € n'apporte presque rien. Les avis sont utiles quand "
             "ils argumentent et quand ils changent de sens (passage d'achat à vente). Un **consensus** très "
             "optimiste est déjà dans le prix."),
            ("Une forte baisse : opportunité ou signal ?",
             "Une chute de 10 % en un jour a toujours une cause. Si c'est une mauvaise nouvelle de fond (prévisions "
             "abaissées, perte d'un marché clé), le prix s'ajuste à une réalité nouvelle. Si c'est la panique "
             "générale sans changement pour l'entreprise, ce peut être une occasion. L'outil t'alerte au-delà de "
             "5 % pour que tu cherches la cause avant d'agir."),
            ("Comment l'outil trie",
             "Chaque article reçoit une catégorie, un ton et une importance de 0 (bruit) à 3 (majeur), puis la "
             "synthèse relie chaque phrase à ses sources numérotées. Va toujours lire la source d'une nouvelle qui "
             "pourrait changer ta décision."),
        ],
        "takeaways": [
            "La plupart des articles sont du bruit ; cherche ce qui change la valeur à long terme.",
            "Un consensus optimiste est déjà dans le prix.",
            "Une forte baisse : cherche la cause avant d'agir.",
        ],
        "links": [("/actualites", "Actualités : filtre « Notable » et « Majeur »")],
        "glossary": ["avertissement_resultats", "consensus", "rachat_actions"],
        "quiz": [
            ("Lequel de ces titres est un vrai signal pour un actionnaire de long terme ?",
             ["« L'action progresse de 0,8 % »", "« L'entreprise abaisse ses prévisions annuelles »",
              "« Le CAC 40 termine en hausse »"],
             1, "Un avertissement sur les prévisions change les bénéfices attendus, donc la valeur."),
            ("Une action chute de 12 % en un jour. Première chose à faire ?",
             ["Vendre", "Acheter beaucoup", "Chercher la cause dans l'actualité"],
             2, "Selon la cause, c'est un signal à prendre au sérieux ou une occasion. Ne jamais agir à l'aveugle."),
        ],
    },
    {
        "id": "agent",
        "title": "Utiliser l'agent et ton journal",
        "level": "Avancé",
        "minutes": 4,
        "sections": [
            ("Ce que fait l'agent",
             "Chaque mois, un **analyste** lit les dossiers, un **avocat du diable** cherche les failles, un "
             "**gérant** décide en partant du plan calculé par les règles. Tous les chiffres viennent des données "
             "de l'outil (faits F1, F2...) ; un chiffre absent de ces faits est signalé « non vérifié »."),
            ("Comment décider",
             "Lis d'abord les objections de gravité 3. Si l'une te paraît sérieuse, tu peux refuser le plan, ou "
             "exclure l'action concernée dans Portefeuille et en préparer un nouveau. Écris un commentaire : dans "
             "un an, relire pourquoi tu as validé ou refusé t'apprendra beaucoup sur ta façon de décider."),
            ("Le vrai test : le journal",
             "Une stratégie ne se juge ni sur un mois ni sur une belle histoire, mais en la comparant pendant des "
             "années à l'alternative la plus simple : tout mettre sur l'ETF monde. C'est le rôle du journal. Si, "
             "après plusieurs années, les satellites ne font pas mieux, la décision rationnelle sera d'augmenter la "
             "part de l'ETF."),
        ],
        "takeaways": [
            "Lis les objections graves avant de valider.",
            "Commente tes décisions : c'est ainsi qu'on progresse.",
            "Juge la stratégie sur des années, contre l'ETF seul.",
        ],
        "links": [("/plan", "Plan du mois"), ("/journal", "Journal")],
        "glossary": ["benchmark"],
        "quiz": [
            ("L'avocat du diable signale une objection de gravité 3 sur une action. Tu peux :",
             ["Uniquement valider le plan", "Refuser le plan ou exclure l'action puis refaire un plan",
              "Supprimer l'avocat du diable"],
             1, "Tu restes décideur : refuser, exclure l'action, ou valider en connaissance de cause."),
            ("À quoi compare-t-on la stratégie pour savoir si elle marche ?",
             ["Au livret A", "À 100 % ETF monde sur plusieurs années", "Au meilleur mois de l'année"],
             1, "L'alternative simple et bon marché est l'ETF monde : c'est elle qu'il faut battre."),
        ],
    },
]

GLOSSARY: dict[str, tuple[str, str]] = {
    "action": ("Action", "Titre de propriété d'une part d'entreprise, qui donne droit à une part des bénéfices et souvent à un vote."),
    "dividende": ("Dividende", "Part du bénéfice versée chaque année aux actionnaires, en euros par action."),
    "indice": ("Indice", "Panier d'actions qui sert de référence pour mesurer un marché (CAC 40, MSCI World...)."),
    "etf": ("ETF (tracker)", "Fonds coté en bourse qui reproduit un indice, avec des frais très bas."),
    "msci_world": ("MSCI World", "Indice d'environ 1 500 grandes entreprises de 23 pays développés, très exposé aux États-Unis."),
    "pea": ("PEA", "Plan d'épargne en actions : après 5 ans, gains exonérés d'impôt sur le revenu (18,6 % de prélèvements sociaux en 2026). Versements plafonnés à 150 000 €."),
    "flat_tax": ("Flat tax (PFU)", "Prélèvement forfaitaire unique sur les gains de placement : 31,4 % en 2026 (12,8 % d'impôt + 18,6 % de prélèvements sociaux)."),
    "prelevements_sociaux": ("Prélèvements sociaux", "CSG, CRDS et prélèvement de solidarité sur les revenus du capital : 18,6 % en 2026 pour le PEA et le compte-titres."),
    "plan_programme": ("Plan d'investissement programmé", "Achat automatique d'un montant fixe à intervalle régulier ; gratuit chez Trade Republic, avec achat de fractions."),
    "replication_synthetique": ("Réplication synthétique", "Un ETF détient d'autres actions (européennes pour un PEA) et échange leur performance contre celle de l'indice visé grâce à un swap."),
    "interets_composes": ("Intérêts composés", "Les gains produisent eux-mêmes des gains : l'effet grandit avec le temps."),
    "dca": ("DCA (versements programmés)", "Investir la même somme à intervalle régulier, quel que soit le niveau du marché."),
    "drawdown": ("Pire baisse (drawdown)", "Plus forte chute depuis un sommet, par exemple -35 %."),
    "diversification": ("Diversification", "Répartir son argent entre de nombreux titres, secteurs et pays pour qu'aucun accident isolé ne soit grave."),
    "ter": ("Frais courants (TER)", "Frais de gestion annuels d'un fonds, déduits automatiquement de sa performance (environ 0,2 % pour un ETF monde)."),
    "coeur_satellites": ("Cœur et satellites", "Stratégie : un cœur large et peu cher (ETF monde) et quelques lignes choisies autour, minoritaires."),
    "chiffre_affaires": ("Chiffre d'affaires", "Total des ventes de l'année."),
    "resultat_operationnel": ("Résultat opérationnel", "Ce que rapporte l'activité, avant intérêts et impôts."),
    "resultat_net": ("Résultat net", "Bénéfice final revenant aux actionnaires, après tout."),
    "bpa": ("Bénéfice par action (BPA)", "Résultat net divisé par le nombre d'actions ; sa croissance tire le cours à long terme."),
    "fcf": ("Flux de trésorerie disponible (FCF)", "Cash opérationnel moins investissements : l'argent disponible pour les actionnaires et la dette."),
    "capex": ("Capex", "Investissements dans l'outil de production : usines, machines, logiciels."),
    "capitaux_propres": ("Capitaux propres", "Ce qui appartient aux actionnaires : actifs moins dettes."),
    "esef": ("ESEF", "Format électronique obligatoire des rapports annuels des sociétés cotées dans l'UE ; source officielle et auditée des chiffres de l'outil."),
    "ifrs": ("IFRS et US GAAP", "Normes comptables européennes (IFRS) et américaines (US GAAP) ; les mêmes comptes peuvent différer de 10 à 20 % selon la norme."),
    "roic": ("ROIC", "Rentabilité du capital investi : bénéfice d'exploitation après impôt / capital investi. Durablement > 15 % : avantage concurrentiel probable."),
    "roe": ("ROE", "Rentabilité des fonds propres : bénéfice net / capitaux propres. Peut être gonflée par la dette."),
    "marge_operationnelle": ("Marge opérationnelle", "Résultat opérationnel / chiffre d'affaires : la part des ventes qui reste en bénéfice d'exploitation."),
    "ebitda": ("EBITDA", "Résultat opérationnel avant amortissements ; proche du cash généré par l'activité."),
    "dette_nette_ebitda": ("Dette nette / EBITDA", "Années de résultat brut nécessaires pour rembourser la dette nette ; < 2 confortable, > 3,5 risqué."),
    "avantage_concurrentiel": ("Avantage concurrentiel", "Ce qui protège une entreprise de ses concurrents : marque, brevets, réseau, coûts, habitudes des clients."),
    "per": ("PER", "Cours / bénéfice par action : nombre d'années de bénéfice actuel payées. ≈ 15 : moyen."),
    "capitalisation": ("Capitalisation boursière", "Valeur de toutes les actions d'une entreprise au cours actuel."),
    "rendement_fcf": ("Rendement du free cash flow", "Cash disponible / capitalisation : le « loyer » rapporté au prix actuel."),
    "ve_ebit": ("VE / EBIT", "Valeur d'entreprise (capitalisation + dette nette) / résultat d'exploitation ; compare des sociétés plus ou moins endettées."),
    "piege_valeur": ("Piège à valeur", "Action qui paraît bon marché mais dont les bénéfices vont baisser : le prix bas était justifié."),
    "rendement_dividende": ("Rendement du dividende", "Dividende annuel / cours. Très élevé (> 7 %), il annonce souvent une baisse du dividende."),
    "volatilite": ("Volatilité", "Amplitude habituelle des variations d'un cours sur un an."),
    "beta": ("Bêta", "Sensibilité au marché : 1,3 = l'action varie de 13 % quand le marché varie de 10 %."),
    "aversion_pertes": ("Aversion aux pertes", "Biais : une perte fait environ deux fois plus mal qu'un gain équivalent ne fait plaisir."),
    "biais_retrospectif": ("Biais rétrospectif", "Après coup, tout semble évident ; on surestime ce qu'on aurait pu prévoir."),
    "avertissement_resultats": ("Avertissement sur résultats", "Annonce que les résultats seront inférieurs aux prévisions ; souvent suivie d'une forte baisse."),
    "consensus": ("Consensus", "Moyenne des prévisions des analystes ; ce qu'il annonce est en général déjà dans le cours."),
    "rachat_actions": ("Rachat d'actions", "L'entreprise rachète et annule ses propres actions : chaque action restante détient une plus grande part des bénéfices."),
    "benchmark": ("Indice de référence (benchmark)", "Ce à quoi on compare une stratégie ; ici, 100 % ETF monde."),
}

# Analysis metrics (brick 2) -> the chapter that explains them, for "en savoir plus" links.
METRIC_CHAPTER = {
    "roic": "qualite", "roe": "qualite", "operating_margin": "qualite", "fcf_margin": "comptes",
    "cash_conversion": "comptes", "net_debt_to_ebitda": "qualite", "interest_coverage": "qualite",
    "current_ratio": "qualite", "equity_ratio": "qualite", "revenue_cagr": "comptes", "revenue_recent": "comptes",
    "eps_cagr": "comptes", "revenue_consistency": "comptes", "pe": "valorisation", "pe_vs_history": "valorisation",
    "fcf_yield": "valorisation", "ev_ebit": "valorisation", "pb": "valorisation", "dividend_yield": "valorisation",
    "volatility": "risque", "max_drawdown": "risque", "beta": "risque",
}
