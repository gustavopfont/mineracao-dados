# -*- coding: utf-8 -*-
"""
Classificador de IMC por Idade e Sexo (0 a 19 anos)
Baseado nos gráficos e tabelas de Escore-Z da OMS / SBP
"""

# Tabela simplificada de cortes de IMC por Escore-Z (Meses -> [-3SD, -2SD, +1SD, +2SD, +3SD])
# Meninos de 0 a 5 anos (0 a 60 meses)
TABELA_MENINOS_0_5 = {
    0:  [10.1, 11.1, 15.3, 16.8, 18.5],   # Nascimento
    6:  [12.5, 13.6, 17.5, 18.9, 20.6],   # 6 meses
    12: [12.7, 13.7, 17.2, 18.4, 19.8],   # 1 ano
    24: [12.2, 13.0, 16.0, 17.1, 18.3],   # 2 anos
    36: [11.8, 12.6, 15.4, 16.4, 17.6],   # 3 anos
    48: [11.5, 12.3, 15.1, 16.1, 17.3],   # 4 anos
    60: [11.3, 12.1, 15.0, 16.1, 17.4]    # 5 anos
}

# Meninas de 0 a 5 anos (0 a 60 meses)
TABELA_MENINAS_0_5 = {
    0:  [9.7,  10.6, 14.8, 16.3, 18.0],
    6:  [11.9, 12.9, 16.9, 18.4, 20.2],
    12: [12.1, 13.0, 16.6, 17.9, 19.4],
    24: [11.7, 12.5, 15.6, 16.8, 18.2],
    36: [11.4, 12.2, 15.1, 16.2, 17.5],
    48: [11.1, 11.9, 14.8, 16.0, 17.3],
    60: [10.9, 11.7, 14.8, 16.1, 17.6]
}

# Meninos de 5 a 19 anos (60 a 228 meses)
TABELA_MENINOS_5_19 = {
    60:  [11.3, 12.1, 15.0, 16.1, 17.4],  # 5 anos
    84:  [11.6, 12.3, 15.5, 16.9, 18.8],  # 7 anos
    108: [11.9, 12.7, 16.4, 18.3, 20.9],  # 9 anos
    132: [12.5, 13.4, 17.6, 20.0, 23.3],  # 11 anos
    156: [13.3, 14.3, 19.1, 22.0, 25.8],  # 13 anos
    180: [14.4, 15.5, 20.8, 23.9, 27.7],  # 15 anos
    204: [15.5, 16.7, 22.3, 25.6, 29.3],  # 17 anos
    228: [16.3, 17.6, 23.5, 27.0, 30.6]   # 19 anos
}

# Meninas de 5 a 19 anos (60 a 228 meses)
TABELA_MENINAS_5_19 = {
    60:  [10.9, 11.7, 14.8, 16.1, 17.6],  # 5 anos
    84:  [11.2, 12.0, 15.4, 17.0, 19.2],  # 7 anos
    108: [11.6, 12.5, 16.4, 18.4, 21.3],  # 9 anos
    132: [12.3, 13.3, 17.7, 20.2, 23.7],  # 11 anos
    156: [13.1, 14.2, 19.2, 22.1, 25.9],  # 13 anos
    180: [13.9, 15.0, 20.4, 23.5, 27.3],  # 15 anos
    204: [14.4, 15.6, 21.2, 24.3, 28.0],  # 17 anos
    228: [14.7, 16.0, 21.7, 24.8, 28.5]   # 19 anos
}


def obter_cortes_referencia(idade_meses, sexo):
    """Retorna os limites de corte de IMC [-3SD, -2SD, +1SD, +2SD, +3SD] para o mês mais próximo."""
    if idade_meses <= 60:
        tabela = TABELA_MENINOS_0_5 if sexo.upper() == 'M' else TABELA_MENINAS_0_5
    else:
        tabela = TABELA_MENINOS_5_19 if sexo.upper() == 'M' else TABELA_MENINAS_5_19
        
    mes_proximo = min(tabela.keys(), key=lambda x: abs(x - idade_meses))
    return tabela[mes_proximo], mes_proximo


def classificar_imc_pediatrico(idade_anos, idade_meses_adicionais, sexo, imc):
    """
    Classifica o IMC de crianças e adolescentes de 0 a 19 anos.
    
    Parâmetros:
    - idade_anos (int): Idade em anos (0 a 19).
    - idade_meses_adicionais (int): Meses além dos anos completos (0 a 11).
    - sexo (str): 'M' para Masculino ou 'F' para Feminino.
    - imc (float): Valor do IMC em kg/m².
    """
    idade_total_meses = (idade_anos * 12) + idade_meses_adicionais
    
    if idade_total_meses < 0 or idade_total_meses > 228:
        raise ValueError("A idade deve estar entre 0 meses e 19 anos (228 meses).")
        
    cortes, mes_ref = obter_cortes_referencia(idade_total_meses, sexo)
    sd3_neg, sd2_neg, sd1_pos, sd2_pos, sd3_pos = cortes

    # Classificação de 0 a 5 anos (<= 60 meses)
    if idade_total_meses <= 60:
        if imc < sd3_neg:
            classificacao = "Magreza acentuada (Z < -3)"
        elif imc < sd2_neg:
            classificacao = "Magreza (-3 <= Z < -2)"
        elif imc <= sd1_pos:
            classificacao = "Eutrofia (-2 <= Z <= +1)"
        elif imc <= sd2_pos:
            classificacao = "Risco de sobrepeso (+1 < Z <= +2)"
        elif imc <= sd3_pos:
            classificacao = "Sobrepeso (+2 < Z <= +3)"
        else:
            classificacao = "Obesidade (Z > +3)"

    # Classificação de 5 a 19 anos (> 60 meses)
    else:
        if imc < sd3_neg:
            classificacao = "Magreza acentuada (Z < -3)"
        elif imc < sd2_neg:
            classificacao = "Magreza (-3 <= Z < -2)"
        elif imc <= sd1_pos:
            classificacao = "Eutrofia (-2 <= Z <= +1)"
        elif imc <= sd2_pos:
            classificacao = "Sobrepeso (+1 < Z <= +2)"
        elif imc <= sd3_pos:
            classificacao = "Obesidade (+2 < Z <= +3)"
        else:
            classificacao = "Obesidade grave (Z > +3)"

    return {
        'idade_total_meses': idade_total_meses,
        'mes_referencia_tabela': mes_ref,
        'sexo': sexo.upper(),
        'imc': imc,
        'classificacao': classificacao,
        'limites_escore_z': {
            '-3SD': sd3_neg,
            '-2SD': sd2_neg,
            '+1SD': sd1_pos,
            '+2SD': sd2_pos,
            '+3SD': sd3_pos
        }
    }


# =====================================================================
# Exemplos de Uso
# =====================================================================
if __name__ == "__main__":
    # Exemplo 1: Menino de 3 anos (36 meses) com IMC 16.8 (Risco de Sobrepeso)
    res1 = classificar_imc_pediatrico(idade_anos=3, idade_meses_adicionais=0, sexo='M', imc=16.8)
    print("Exemplo 1 (3 anos):", res1['classificacao'])

    # Exemplo 2: Menina de 9 anos (108 meses) com IMC 19.5 (Sobrepeso)
    res2 = classificar_imc_pediatrico(idade_anos=9, idade_meses_adicionais=0, sexo='F', imc=19.5)
    print("Exemplo 2 (9 anos):", res2['classificacao'])

    # Exemplo 3: Menino de 13 anos com IMC 26.5 (Obesidade)
    res3 = classificar_imc_pediatrico(idade_anos=13, idade_meses_adicionais=0, sexo='M', imc=26.5)
    print("Exemplo 3 (13 anos):", res3['classificacao'])