""" Dados sinteticos no formato publicado pela CVM, para os testes. """
import pandas as pd

OFERTA_COLUMNS = [
    'Numero_Requerimento', 'Status_Requerimento', 'Valor_Mobiliario', 'Data_Registro', 'Data_Encerramento',
    'Valor_Total_Registrado', 'Qtde_Total_Registrada', 'Emissao', 'CNPJ_Emissor', 'Nome_Emissor',
    'CNPJ_Lider', 'Nome_Lider', 'Agente_fiduciario', 'Gestor', 'Tipo_lastro', 'Titulo_incentivado',
    'Num_Invest_Pessoa_Natural', 'Qtde_VM_Pessoa_Natural',
    'Num_Invest_Fundos_Investimento', 'Qtde_VM_Fundos_Investimento',
]


def oferta(numero, status='Oferta Encerrada', tipo='Debêntures', valor='1000000.00', qtde='1000',
           pf='0', fundos='1000', agente=None, gestor=None, data='2025-03-10', lider='Banco A S.A.',
           cnpj_lider='11.111.111/0001-11', emissor='Emissora X S.A.', emissao='1.0', lastro=None):
    """ Uma linha do arquivo oferta_resolucao_160.csv (tudo como texto). """
    return {
        'Numero_Requerimento': str(numero), 'Status_Requerimento': status, 'Valor_Mobiliario': tipo,
        'Data_Registro': data, 'Data_Encerramento': '2025-04-10', 'Valor_Total_Registrado': valor,
        'Qtde_Total_Registrada': qtde, 'Emissao': emissao, 'CNPJ_Emissor': '22.222.222/0001-22',
        'Nome_Emissor': emissor, 'CNPJ_Lider': cnpj_lider, 'Nome_Lider': lider,
        'Agente_fiduciario': agente, 'Gestor': gestor, 'Tipo_lastro': lastro, 'Titulo_incentivado': 'N',
        'Num_Invest_Pessoa_Natural': '1' if pf != '0' else '0', 'Qtde_VM_Pessoa_Natural': pf,
        'Num_Invest_Fundos_Investimento': '1' if fundos != '0' else '0', 'Qtde_VM_Fundos_Investimento': fundos,
    }


def ofertas_raw(*rows) -> pd.DataFrame:
    """ DataFrame bruto de ofertas com o mesmo layout da CVM. """
    return pd.DataFrame(list(rows), columns=OFERTA_COLUMNS).astype('string')


def participante(tipo, nome, cnpj=None, situacao='ATIVO', pessoa='PJ', uf='RJ', nome_comercial=None,
                 data_registro='2010-01-01'):
    """ Uma linha da tabela silver cvm_participantes. """
    return {
        'tipo_participante': tipo, 'tipo_pessoa': pessoa, 'cnpj': cnpj, 'nome': nome,
        'nome_comercial': nome_comercial, 'categoria': None, 'situacao': situacao,
        'situacao_grupo': 'ATIVO' if situacao in ('ATIVO', 'EM FUNCIONAMENTO NORMAL') else 'CANCELADO',
        'data_registro': pd.Timestamp(data_registro), 'uf': uf,
    }
