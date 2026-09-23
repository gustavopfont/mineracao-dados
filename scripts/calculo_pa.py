"""
Classificação da Pressão Arterial na Infância e Adolescência (0 a 18 anos)
Baseado no Manual de Orientação da Sociedade Brasileira de Pediatria (SBP, 2019)
"""

# Tabela simplificada de percentis de estatura e corte de PA para Meninos (Tabela 1 - SBP)
TABELA_MENINOS = {
    1: {
        'alturas': [77.2, 78.3, 80.2, 82.4, 84.6, 86.7, 87.9],
        'pas': {'p50': [85]*7, 'p90': [98, 99, 99, 100, 100, 101, 101], 'p95': [102, 102, 103, 103, 104, 105, 105], 'p95_12': [114, 114, 115, 117, 116, 115, 117]},
        'pad': {'p50': [40, 40, 41, 40, 41, 42, 42], 'p90': [52, 52, 53, 53, 54, 54, 54], 'p95': [54, 54, 55, 55, 56, 57, 57], 'p95_12': [66, 66, 67, 67, 68, 69, 69]}
    },
    5: {
        'alturas': [104.4, 106.2, 109.1, 112.4, 115.7, 118.6, 120.3],
        'pas': {'p50': [91, 92, 93, 96, 96, 95, 94], 'p90': [104, 103, 105, 106, 108, 108, 107], 'p95': [107, 108, 109, 111, 110, 109, 112], 'p95_12': [119, 120, 121, 124, 123, 122, 121]},
        'pad': {'p50': [51, 52, 51, 53, 54, 55, 55], 'p90': [64, 63, 65, 65, 66, 67, 67], 'p95': [69, 68, 67, 66, 70, 70, 71], 'p95_12': [78, 79, 80, 81, 83, 82, 82]}
    },
    10: {
        'alturas': [130.2, 132.7, 136.7, 141.3, 145.9, 150.1, 152.7],
        'pas': {'p50': [98, 97, 100, 101, 99, 102, 103], 'p90': [109, 108, 115, 113, 111, 112, 116], 'p95': [113, 112, 120, 118, 116, 114, 121], 'p95_12': [125, 124, 128, 126, 132, 130, 133]},
        'pad': {'p50': [60, 59, 61, 63, 63, 62, 64], 'p90': [72, 73, 74, 75, 74, 75, 76], 'p95': [76, 76, 77, 78, 78, 77, 78], 'p95_12': [88, 88, 89, 89, 90, 90, 90]}
    },
    12: {
        'alturas': [140.3, 143.0, 147.5, 152.7, 157.9, 162.6, 165.5],
        'pas': {'p50': [101, 101, 106, 108, 102, 104, 109], 'p90': [114, 113, 121, 119, 117, 115, 122], 'p95': [116, 117, 118, 126, 124, 121, 128], 'p95_12': [129, 128, 130, 133, 136, 138, 140]},
        'pad': {'p50': [62, 61, 62, 63, 62, 62, 63], 'p90': [75, 75, 75, 76, 75, 75, 76], 'p95': [78, 78, 78, 79, 78, 78, 79], 'p95_12': [90, 90, 90, 91, 90, 90, 91]}
    }
}

# Tabela simplificada de percentis de estatura e corte de PA para Meninas (Tabela 2 - SBP)
TABELA_MENINAS = {
    1: {
        'alturas': [75.4, 76.6, 78.6, 80.8, 83.0, 84.9, 86.1],
        'pas': {'p50': [84, 85, 86, 86, 87, 88, 88], 'p90': [98, 99, 99, 100, 102, 101, 102], 'p95': [101, 102, 102, 103, 104, 105, 105], 'p95_12': [113, 114, 114, 115, 116, 117, 117]},
        'pad': {'p50': [41, 42, 42, 44, 43, 45, 46], 'p90': [54, 55, 56, 58, 56, 57, 58], 'p95': [59, 59, 60, 62, 60, 61, 62], 'p95_12': [71, 71, 72, 73, 74, 72, 74]}
    },
    5: {
        'alturas': [103.6, 105.3, 108.2, 111.5, 114.9, 118.1, 120.0],
        'pas': {'p50': [90, 91, 92, 93, 94, 95, 96], 'p90': [104, 105, 106, 107, 108, 109, 110], 'p95': [108, 109, 109, 110, 112, 111, 113], 'p95_12': [120, 121, 121, 122, 124, 123, 125]},
        'pad': {'p50': [52, 52, 53, 56, 55, 57, 57], 'p90': [64, 65, 66, 68, 67, 69, 70], 'p95': [68, 69, 70, 73, 71, 72, 73], 'p95_12': [81, 80, 82, 83, 85, 84, 85]}
    },
    10: {
        'alturas': [129.7, 132.2, 136.3, 141.0, 145.8, 150.2, 152.8],
        'pas': {'p50': [96, 97, 98, 99, 102, 101, 103], 'p90': [109, 110, 111, 112, 115, 113, 116], 'p95': [113, 114, 116, 114, 117, 119, 120], 'p95_12': [125, 126, 128, 126, 131, 129, 132]},
        'pad': {'p50': [58, 60, 61, 61, 59, 59, 61], 'p90': [72, 73, 73, 73, 73, 73, 73], 'p95': [75, 76, 76, 76, 76, 75, 76], 'p95_12': [87, 88, 88, 88, 88, 87, 88]}
    },
    12: {
        'alturas': [142.8, 145.5, 149.9, 154.8, 159.6, 163.8, 166.4],
        'pas': {'p50': [102, 102, 104, 105, 107, 108, 108], 'p90': [114, 115, 118, 116, 122, 120, 122], 'p95': [118, 119, 122, 120, 125, 124, 126], 'p95_12': [130, 131, 134, 132, 137, 136, 138]},
        'pad': {'p50': [61, 64, 61, 65, 61, 62, 65], 'p90': [75, 76, 76, 75, 75, 75, 76], 'p95': [78, 79, 78, 78, 79, 78, 79], 'p95_12': [90, 91, 90, 90, 90, 91, 91]}
    }
}

# Tabela 4 - Neonatos / Lactentes de 26 a 44 semanas pós-concepção (Dionne et al.)
TABELA_NEONATOS = {
    40: {'pas': {'p50': 80, 'p95': 95, 'p99': 100}, 'pad': {'p50': 50, 'p95': 65, 'p99': 70}},
    42: {'pas': {'p50': 85, 'p95': 98, 'p99': 102}, 'pad': {'p50': 50, 'p95': 65, 'p99': 70}},
    44: {'pas': {'p50': 88, 'p95': 105, 'p99': 110}, 'pad': {'p50': 50, 'p95': 68, 'p99': 73}}
}


def encontrar_coluna_estatura(altura_cm, lista_alturas):
    """Encontra o índice da altura mais próxima na tabela de percentis."""
    diferencas = [abs(altura_cm - alt) for alt in lista_alturas]
    return diferencas.index(min(diferencas))


def calcular_imc(peso_kg, altura_cm):
    """Calcula o Índice de Massa Corporal (IMC)."""
    altura_m = altura_cm / 100.0
    return round(peso_kg / (altura_m ** 2), 2)


def determinar_diagnostico(c_pas, c_pad):
    """
    Compara as classificações da PAS e PAD e retorna a classificação com base na maior gravidade.
    Se ambas forem do mesmo nível de gravidade, prioriza a PAS.
    
    Níveis de gravidade:
    0: Normal
    1: Pre-Hipertensão
    2: HAS-1
    3: HAS-2
    """
    labels_pas = {0: "Normal", 1: "Pre-Hipertensão PAS", 2: "HAS-1 PAS", 3: "HAS-2 PAS"}
    labels_pad = {0: "Normal", 1: "Pre-Hipertensão PAD", 2: "HAS-1 PAD", 3: "HAS-2 PAD"}
    
    if c_pas == 0 and c_pad == 0:
        return "Normal"
    elif c_pas >= c_pad:
        return labels_pas[c_pas]
    else:
        return labels_pad[c_pad]


def classificar_pressao_arterial(idade_anos, sexo, altura_cm, peso_kg, pas_medida, pad_medida, idade_pos_concepcao_semanas=None):
    """
    Classifica a Pressão Arterial de acordo com as diretrizes da SBP (2019).
    Classificações possíveis: 'Normal', 'Pre-Hipertensão PAS', 'Pre-Hipertensão PAD',
    'HAS-1 PAS', 'HAS-1 PAD', 'HAS-2 PAS', 'HAS-2 PAD'.
    """
    imc = calcular_imc(peso_kg, altura_cm)
    
    # -------------------------------------------------------------
    # 1. Recém-nascidos e lactentes (< 1 ano)
    # -------------------------------------------------------------
    if idade_anos < 1:
        semanas = idade_pos_concepcao_semanas or 40
        ref = TABELA_NEONATOS.get(semanas, TABELA_NEONATOS[40])
        
        c_pas = 3 if pas_medida >= ref['pas']['p99'] else (2 if pas_medida >= ref['pas']['p95'] else 0)
        c_pad = 3 if pad_medida >= ref['pad']['p99'] else (2 if pad_medida >= ref['pad']['p95'] else 0)
        
        classificacao = determinar_diagnostico(c_pas, c_pad)
        
        return {
            'faixa_etaria': 'Neonato/Lactente (< 1 ano)',
            'imc': imc,
            'classificacao': classificacao
        }

    # -------------------------------------------------------------
    # 2. Crianças e Adolescentes >= 13 anos (Valores Fixos de Adulto)
    # -------------------------------------------------------------
    if idade_anos >= 13:
        # Classificação PAS
        if pas_medida >= 140:
            c_pas = 3  # HAS-2
        elif 130 <= pas_medida <= 139:
            c_pas = 2  # HAS-1
        elif 120 <= pas_medida <= 129:
            c_pas = 1  # Pre-Hipertensão
        else:
            c_pas = 0  # Normal

        # Classificação PAD
        if pad_medida >= 90:
            c_pad = 3  # HAS-2
        elif 80 <= pad_medida <= 89:
            c_pad = 2  # HAS-1
        else:
            c_pad = 0  # Normal

        classificacao = determinar_diagnostico(c_pas, c_pad)
        
        return {
            'faixa_etaria': 'Adolescente (>= 13 anos)',
            'imc': imc,
            'classificacao': classificacao
        }

    # -------------------------------------------------------------
    # 3. Crianças de 1 a 12 anos (Percentis por Sexo, Idade e Estatura)
    # -------------------------------------------------------------
    tabela = TABELA_MENINOS if sexo.upper() == 'M' else TABELA_MENINAS
    
    idades_disponiveis = sorted(tabela.keys())
    idade_ref = min(idades_disponiveis, key=lambda x: abs(x - idade_anos))
    dados_idade = tabela[idade_ref]
    
    idx_altura = encontrar_coluna_estatura(altura_cm, dados_idade['alturas'])
    
    # Limites calculados pelos percentis da tabela
    p90_pas = dados_idade['pas']['p90'][idx_altura]
    p95_pas = dados_idade['pas']['p95'][idx_altura]
    p95_12_pas = dados_idade['pas']['p95_12'][idx_altura]
    
    p90_pad = dados_idade['pad']['p90'][idx_altura]
    p95_pad = dados_idade['pad']['p95'][idx_altura]
    p95_12_pad = dados_idade['pad']['p95_12'][idx_altura]
    
    # Aplica a regra do menor valor entre o percentil e o teto absoluto de adulto
    limite_estagio2_pas = min(p95_12_pas, 140)
    limite_estagio2_pad = min(p95_12_pad, 90)
    
    limite_estagio1_pas = min(p95_pas, 130)
    limite_estagio1_pad = min(p95_pad, 80)
    
    limite_elevada_pas = min(p90_pas, 120)
    limite_elevada_pad = min(p90_pad, 80)
    
    # Avaliação da PAS
    if pas_medida >= limite_estagio2_pas:
        c_pas = 3  # HAS-2 PAS
    elif pas_medida >= limite_estagio1_pas:
        c_pas = 2  # HAS-1 PAS
    elif pas_medida >= limite_elevada_pas:
        c_pas = 1  # Pre-Hipertensão PAS
    else:
        c_pas = 0  # Normal
        
    # Avaliação da PAD
    if pad_medida >= limite_estagio2_pad:
        c_pad = 3  # HAS-2 PAD
    elif pad_medida >= limite_estagio1_pad:
        c_pad = 2  # HAS-1 PAD
    elif pad_medida >= limite_elevada_pad:
        c_pad = 1  # Pre-Hipertensão PAD
    else:
        c_pad = 0  # Normal
        
    classificacao = determinar_diagnostico(c_pas, c_pad)
    
    return {
        'faixa_etaria': 'Criança (1 a 12 anos)',
        'idade_referencia_tabela': idade_ref,
        'imc': imc,
        'classificacao': classificacao,
        'valores_corte': {
            'P90_PAS_PAD': (limite_elevada_pas, limite_elevada_pad),
            'P95_PAS_PAD': (limite_estagio1_pas, limite_estagio1_pad),
            'P95_12_PAS_PAD': (limite_estagio2_pas, limite_estagio2_pad)
        }
    }


# =====================================================================
# Exemplos de Teste
# =====================================================================
if __name__ == "__main__":
    # Exemplo 1: Criança de 5 anos com PAS elevada
    res1 = classificar_pressao_arterial(5, 'M', 112.0, 19.0, 105, 60)
    print("Resultado 1:", res1['classificacao'])  # Esperado: Pre-Hipertensão PAS

    # Exemplo 2: Adolescente de 14 anos com PAD elevada (HAS-1)
    res2 = classificar_pressao_arterial(14, 'F', 165.0, 55.0, 118, 85)
    print("Resultado 2:", res2['classificacao'])  # Esperado: HAS-1 PAD

    # Exemplo 3: Criança de 10 anos normal
    res3 = classificar_pressao_arterial(10, 'M', 141.0, 35.0, 100, 60)
    print("Resultado 3:", res3['classificacao'])  # Esperado: Normal