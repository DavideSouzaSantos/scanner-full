import os
import sys
import math
import random
from collections import deque
from datetime import datetime
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QProgressBar, QTextEdit, QGroupBox, QGridLayout,
    QComboBox, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt, Property, QPropertyAnimation, QEasingCurve, QRectF, QPointF, QThread, Signal, QTimer
from PySide6.QtPrintSupport import QPrinter, QPrintDialog
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont,
    QPainterPath, QLinearGradient, QPixmap, QPageSize, QTextDocument
)
import pyqtgraph as pg


# =====================================================================
# 0. ATUALIZADOR AUTOMÁTICO (via GitHub — sem baixar zip manualmente)
# =====================================================================
VERSAO_LOCAL = 10
GITHUB_USUARIO = "DavideSouzaSantos"
GITHUB_REPO = "scanner-full"
URL_VERSAO = f"https://raw.githubusercontent.com/{GITHUB_USUARIO}/{GITHUB_REPO}/main/VERSAO.txt"
URL_ZIP = f"https://github.com/{GITHUB_USUARIO}/{GITHUB_REPO}/archive/refs/heads/main.zip"
ARQUIVOS_UPDATE = ["scanner_full.py", "requirements.txt", "instalar.bat",
                   "iniciar_scanner.bat", "gerar_exe.bat", "LEIA-ME.txt", "VERSAO.txt"]


def ler_versao_local():
    try:
        base = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(base, "VERSAO.txt"), encoding="utf-8") as f:
            return int(f.read().strip().split()[0])
    except Exception:
        return VERSAO_LOCAL


class ThreadVerificacaoUpdate(QThread):
    resultado = Signal(bool, int, str)  # tem_update, versao_remota, mensagem

    def run(self):
        try:
            import urllib.request
            req = urllib.request.Request(URL_VERSAO, headers={"User-Agent": "ScannerFull"})
            with urllib.request.urlopen(req, timeout=15) as r:
                txt = r.read().decode("utf-8", "ignore").strip()
            digitos = "".join(c for c in txt.split()[0] if c.isdigit())
            remota = int(digitos) if digitos else 0
            local = ler_versao_local()
            if remota > local:
                self.resultado.emit(True, remota, f"Nova versão disponível: v{remota} (atual: v{local}).")
            else:
                self.resultado.emit(False, remota, f"Na versão mais recente (v{local}).")
        except Exception as e:
            self.resultado.emit(False, 0, f"Não foi possível verificar: {e}")


class ThreadInstalacaoUpdate(QThread):
    progresso = Signal(str)
    concluido = Signal(bool, str)  # ok, mensagem

    def __init__(self, versao_remota, dest_dir=None):
        super().__init__()
        self.versao_remota = versao_remota
        self._dest = dest_dir

    def run(self):
        import urllib.request
        import zipfile
        import tempfile
        import shutil
        tmpdir = None
        try:
            base = self._dest or os.path.dirname(os.path.abspath(__file__))
            rp = os.path.join(base, "requirements.txt")
            req_antigo = None
            if os.path.exists(rp):
                with open(rp, encoding="utf-8") as f:
                    req_antigo = f.read()
            self.progresso.emit(f"Baixando v{self.versao_remota}…")
            tmpdir = tempfile.mkdtemp(prefix="scannerfull_upd_")
            zippath = os.path.join(tmpdir, "update.zip")
            req = urllib.request.Request(URL_ZIP, headers={"User-Agent": "ScannerFull"})
            with urllib.request.urlopen(req, timeout=120) as r, open(zippath, "wb") as f:
                shutil.copyfileobj(r, f)
            self.progresso.emit("Instalando arquivos…")
            with zipfile.ZipFile(zippath) as z:
                z.extractall(tmpdir)
            origem = os.path.join(tmpdir, f"{GITHUB_REPO}-main")
            if not os.path.isdir(origem):
                subs = [d for d in os.listdir(tmpdir) if os.path.isdir(os.path.join(tmpdir, d))]
                origem = os.path.join(tmpdir, subs[0]) if subs else tmpdir
            copiados = 0
            for nome in ARQUIVOS_UPDATE:
                src = os.path.join(origem, nome)
                if os.path.isfile(src):
                    shutil.copy2(src, os.path.join(base, nome))
                    copiados += 1
            porig = os.path.join(origem, "pecas")
            pdest = os.path.join(base, "pecas")
            if os.path.isdir(porig):
                os.makedirs(pdest, exist_ok=True)
                for arq in os.listdir(porig):
                    if arq.lower().endswith(".png"):
                        shutil.copy2(os.path.join(porig, arq), os.path.join(pdest, arq))
                        copiados += 1
            req_novo = None
            if os.path.exists(rp):
                with open(rp, encoding="utf-8") as f:
                    req_novo = f.read()
            aviso_dep = "\n\nO requirements.txt mudou: rode o instalar.bat de novo." if req_novo != req_antigo else ""
            self.concluido.emit(True,
                                f"Atualizado para v{self.versao_remota} ({copiados} arquivos). Reinicie o app.{aviso_dep}")
        except Exception as e:
            self.concluido.emit(False, f"Falha ao instalar: {e}")
        finally:
            if tmpdir:
                shutil.rmtree(tmpdir, ignore_errors=True)


# =====================================================================
# 1. BASE DE CONHECIMENTO UNIVERSAL (LEVE, PESADA E AGRÍCOLA)
# =====================================================================
BANCO_DEFEITOS = {
    "LINHA_LEVE": {
        "nome": "🚗 Linha Leve (Ciclo Otto / Flex / Gasolina)",
        "gauge1_nome": "RPM MOTOR", "g1_min": 0, "g1_max": 8000, "g1_passo": 1000, "g1_unidade": "RPM",
        "gauge2_nome": "VÁCUO / MAP", "g2_min": 100, "g2_max": 1100, "g2_passo": 200, "g2_unidade": "mbar",
        "scope_nome": "Osciloscópio Sonda Lambda Pré-Cat (0.0V - 1.0V)", "scope_min": 0.0, "scope_max": 1.0, "scope_unidade": "V",
        "veiculo": {"modelo": "VW Gol 1.6 MSI Flex", "ano": "2022", "placa": "BRA2E19", "km": "87.400 km"},
        "referencias": [
            ("Bateria (motor desligado)", "12,4 – 12,8 V"),
            ("Bateria (na partida)", "acima de 9,6 V"),
            ("Bateria (motor ligado)", "13,5 – 14,7 V"),
            ("Queda de tensão no aterramento", "ideal 0,00–0,20 V · máx. 0,50 V"),
            ("Fusível (continuidade)", "bom: 0–1 Ω · queimado: OL"),
            ("Relé — bobina (85–86)", "50 – 120 Ω"),
            ("Relé — contatos (87–30)", "0 Ω acionado · OL desligado"),
            ("Vela — folga dos eletrodos", "0,7 – 1,3 mm"),
            ("Cabo de vela (resistência)", "3 – 12 kΩ"),
            ("Bobina — primário / secundário", "0,3–3 Ω / 6–20 kΩ"),
            ("Pressão da linha (flex)", "3 – 4 bar"),
            ("Bico injetor (alta impedância)", "12 – 16 Ω"),
            ("Sensor CKP (resistência)", "500 – 1.500 Ω"),
            ("TPS — fechado / aberto", "0,4–0,8 V / 4,0–4,8 V"),
        ],
        "indicador1": "Saúde Sonda Lambda:", "indicador2": "Integridade do Trim de Combustível:",
        "falhas": {
            "LEVE_NORMAL": {
                "nome": "Operação Normal (Estequiometria Correta)",
                "peca": {"nome": "Sonda Lambda pré-catalisador", "referencia": "Bosch LSU 4.9", "localizacao": "Rosqueada no coletor de escape, antes do catalisador", "imagem": "sonda_lambda.png", "defeito": False},
                "dtc": [], "rpm": 850, "g2_val": 340, "stft": 1.2, "ltft": 2.1, "telemetria_scope": 0.45,
                "scope_amp": 0.38, "scope_freq": 2.8, "saude1": 98.0, "saude2": 95.0,
                "status1": "Saudável (0.45V) - Comutação rápida", "status2": "Saudável - Correção estequiométrica precisa",
                "laudo": {
                    "titulo": "MISTURA AR/COMBUSTÍVEL IDEAL (LAMBDA ~ 1.00)",
                    "detalhes": "Leituras nominais em marcha lenta estável com motor em regime operacional (90°C).",
                    "causas": ["Nenhuma falha ativa registrada."],
                    "roteiro": ["Manter manutenções preventivas regulares de troca de filtros e lubrificantes."]
                }
            },
            "LEVE_MISFIRE": {
                "nome": "Falha de Ignição / Cilindro Morto (P0300 / P0302)",
                "peca": {"nome": "Bobina de ignição — cilindro 2", "referencia": "Bosch F 000 ZS0 210", "localizacao": "Sobre a vela do cilindro 2, sob a tampa do cabeçote", "imagem": "bobina_ignicao.png", "defeito": True},
                "dtc": [("P0300", "Falha de Ignição Múltipla / Aleatória"), ("P0302", "Cilindro 2 - Falha de Combustão Detectada")],
                "rpm": 780, "g2_val": 460, "stft": 18.0, "ltft": 14.5, "telemetria_scope": 0.20,
                "scope_amp": 0.12, "scope_freq": 1.2, "saude1": 35.0, "saude2": 20.0,
                "status1": "Atenção (Oxigênio livre no escape)", "status2": "PONTO CRÍTICO - Mistura descompensada",
                "laudo": {
                    "titulo": "COMBUSTÃO INCOMPLETA COM VIBRAÇÃO MECÂNICA",
                    "detalhes": "Ausência de centelha ou compressão no cilindro 2. Oxigênio puro é expelido ao escape, induzindo a central a crer em mistura pobre.",
                    "causas": ["Bobina plástica de ignição com fuga de centelha.", "Vela com gap excessivo ou cerâmica trincada.", "Bico 2 travado fechado ou sem pulso da ECU."],
                    "roteiro": [
                        "1. Inverter a bobina do cilindro 2 com o cilindro 1 e testar se o DTC migra para P0301.",
                        "2. Medir resistência e isolamento do cabo/bobina.",
                        "3. Realizar teste de compressão de cilindro no orifício da vela (mínimo 140 PSI)."
                    ]
                }
            },
            "LEVE_TBI": {
                "nome": "Corpo de Borboleta com Pista Descalibrada (P0120 / P0220)",
                "peca": {"nome": "Corpo de borboleta eletrônico", "referencia": "Magneti Marelli 50101902", "localizacao": "Entre o filtro de ar e o coletor de admissão", "imagem": "corpo_borboleta.png", "defeito": True},
                "dtc": [("P0120", "Sensor de Posição da Borboleta A (TPS 1) - Sinal Incoerente"), ("P0220", "Sensor TPS 2 - Correlação Inválida")],
                "rpm": 1250, "g2_val": 520, "stft": 4.5, "ltft": 5.0, "telemetria_scope": 0.50,
                "scope_amp": 0.25, "scope_freq": 1.5, "saude1": 80.0, "saude2": 75.0,
                "status1": "Atenção (Marcha lenta elevada)", "status2": "Atenção - Modo de emergência (Limp Home)",
                "laudo": {
                    "titulo": "DIVERGÊNCIA ENTRE PISTAS RESISTIVAS DO CORPO TBI",
                    "detalhes": "A central corta a resposta do acelerador eletrônico por segurança devido à discrepância de voltagem entre a Pista 1 e Pista 2.",
                    "causas": ["Pista potenciométrica do corpo gasta ou com resíduo de carvão.", "Conector do chicote TBI com oxidação ou folga nos pinos fêmea."],
                    "roteiro": [
                        "1. Desmontar a mangueira e efetuar descarbonização com produto específico.",
                        "2. Monitorar a tensão contínua das pistas (P1 + P2 deve somar 5.0V constante durante a abertura).",
                        "3. Executar o procedimento de aprendizado de batente de borboleta via scanner."
                    ]
                }
            },
            "LEVE_VELA_DESGASTE": {
                "nome": "Velas com Eletrodos Gastos / Folga Excessiva (P0301)",
                "peca": {"nome": "Jogo de velas de ignição", "referencia": "NGK BKR6E-11", "localizacao": "No cabeçote, uma vela por cilindro", "imagem": "vela_ignicao.png", "defeito": True},
                "dtc": [("P0301", "Cilindro 1 - Falha de Combustão Detectada")],
                "rpm": 800, "g2_val": 430, "stft": 9.5, "ltft": 8.0, "telemetria_scope": 0.32,
                "scope_amp": 0.22, "scope_freq": 1.8, "saude1": 55.0, "saude2": 45.0,
                "status1": "Atenção (comutação lenta da sonda)", "status2": "Atenção - Correção de mistura elevada",
                "laudo": {
                    "titulo": "CENTELHA FRACA POR DESGASTE DOS ELETRODOS",
                    "detalhes": "Folga excessiva entre os eletrodos exige tensão maior da bobina; sob carga a centelha falha de forma intermitente no cilindro 1, com marcha lenta irregular.",
                    "causas": ["Velas além do intervalo de troca (erosão dos eletrodos).", "Folga fora do especificado (acima de 1,1 mm)."],
                    "roteiro": [
                        "1. Remover as velas e medir a folga com cálibre de lâminas.",
                        "2. Inspecionar a cor da cerâmica e sinais de carbonização ou óleo.",
                        "3. Substituir o jogo completo e reapertar com torquímetro (25 N·m)."
                    ]
                }
            },
            "LEVE_CABO_FUGA": {
                "nome": "Cabo de Vela com Fuga para a Massa (P0303)",
                "peca": {"nome": "Jogo de cabos de vela", "referencia": "NGK SC-T120", "localizacao": "Entre as bobinas e as velas, sobre o cabeçote", "imagem": "cabo_vela.png", "defeito": True},
                "dtc": [("P0303", "Cilindro 3 - Falha de Combustão Detectada")],
                "rpm": 790, "g2_val": 450, "stft": 14.0, "ltft": 11.0, "telemetria_scope": 0.25,
                "scope_amp": 0.15, "scope_freq": 1.4, "saude1": 45.0, "saude2": 30.0,
                "status1": "Atenção (fuga de alta tensão)", "status2": "PONTO CRÍTICO - Cilindro 3 falhando intermitente",
                "laudo": {
                    "titulo": "ARCO ELÉTRICO DO CABO PARA O CABEÇOTE",
                    "detalhes": "Isolamento do cabo do cilindro 3 rompido; parte da energia da centelha escapa para a massa antes de chegar à vela. O sintoma piora com umidade.",
                    "causas": ["Capa de silicone do cabo ressecada ou rachada.", "Terminal frouxo ou oxidado no encaixe da bobina ou da vela."],
                    "roteiro": [
                        "1. Com o motor ligado no escuro, observar arcos azulados ao longo do cabo.",
                        "2. Borrifar água com borrifador para evidenciar a fuga.",
                        "3. Medir a resistência do cabo (esperado 3–12 kΩ) e substituir o jogo se estiver fora da faixa."
                    ]
                }
            },
            "LEVE_CKP_FALHA": {
                "nome": "Sensor de Rotação CKP Sem Sinal (P0335)",
                "peca": {"nome": "Sensor de rotação do virabrequim (CKP)", "referencia": "Bosch 0 261 210 170", "localizacao": "No bloco, próximo à polia do virabrequim", "imagem": "sensor_ckp.png", "defeito": True},
                "dtc": [("P0335", "Sensor de Posição do Virabrequim A - Falha no Circuito")],
                "rpm": 0, "g2_val": 1000, "stft": 0.0, "ltft": 0.0, "telemetria_scope": 0.45,
                "scope_amp": 0.01, "scope_freq": 0.1, "saude1": 10.0, "saude2": 10.0,
                "status1": "PONTO CRÍTICO - Sem referência de rotação", "status2": "PONTO CRÍTICO - ECU não comanda centelha",
                "laudo": {
                    "titulo": "ECU CEGA: SEM SINAL DE ROTAÇÃO NÃO HÁ CENTELHA",
                    "detalhes": "O motor gira na partida mas a ECU não recebe o sinal do sensor de rotação; sem a referência do PMS ela não dispara bobinas nem bicos. O motor não pega.",
                    "causas": ["Sensor CKP aberto ou em curto.", "Roda fônica danificada ou com dente quebrado.", "Chicote do CKP partido ou conector oxidado."],
                    "roteiro": [
                        "1. Com osciloscópio, verificar o sinal do CKP durante a partida (onda senoidal ou quadrada).",
                        "2. Medir a resistência do sensor e comparar com o valor de fábrica.",
                        "3. Inspecionar a roda fônica por danos ou limalha aderida."
                    ]
                }
            },
            "LEVE_KNOCK": {
                "nome": "Sensor de Detonação Sem Sinal (P0325)",
                "peca": {"nome": "Sensor de detonação (knock)", "referencia": "Bosch 0 261 231 170", "localizacao": "Rosqueado no bloco do motor, entre os cilindros", "imagem": "sensor_detonacao.png", "defeito": True},
                "dtc": [("P0325", "Sensor de Detonação 1 - Falha no Circuito")],
                "rpm": 900, "g2_val": 360, "stft": 3.0, "ltft": 4.0, "telemetria_scope": 0.44,
                "scope_amp": 0.35, "scope_freq": 2.6, "saude1": 92.0, "saude2": 60.0,
                "status1": "Saudável", "status2": "Atenção - Avanço travado em mapa conservador",
                "laudo": {
                    "titulo": "ECU TRABALHANDO NO ESCURO CONTRA A DETONAÇÃO",
                    "detalhes": "Sem o 'microfone' da detonação, a ECU adota um avanço de ignição conservador para proteger o motor: há perda de potência e aumento de consumo, sem falha de combustão aparente.",
                    "causas": ["Sensor de detonação em curto ou aberto.", "Torque de aperto incorreto do sensor no bloco.", "Chicote com mal contato."],
                    "roteiro": [
                        "1. Conferir o torque de fixação do sensor (geralmente 20 N·m).",
                        "2. Com o scanner, provocar leve batida e observar a resposta do PID de knock.",
                        "3. Medir a continuidade do chicote até a ECU."
                    ]
                }
            },
            "LEVE_RELE_BOMBA": {
                "nome": "Relé da Bomba de Combustível Queimado (P0230)",
                "peca": {"nome": "Relé da bomba de combustível", "referencia": "Relé automotivo 12V 30A — 4 pinos", "localizacao": "Caixa de relés e fusíveis no cofre do motor", "imagem": "rele_automotivo.png", "defeito": True},
                "dtc": [("P0230", "Circuito Primário da Bomba de Combustível - Falha")],
                "rpm": 240, "g2_val": 990, "stft": 0.0, "ltft": 0.0, "telemetria_scope": 0.45,
                "scope_amp": 0.02, "scope_freq": 0.2, "saude1": 90.0, "saude2": 8.0,
                "status1": "Saudável (sonda íntegra)", "status2": "PONTO CRÍTICO - Sem pressão de combustível",
                "laudo": {
                    "titulo": "MOTOR GIRA NA PARTIDA MAS NÃO PEGA: BOMBA SEM ALIMENTAÇÃO",
                    "detalhes": "O relé que alimenta a bomba elétrica está com os contatos queimados: ao girar a chave não se ouve o 'zumbido' de pressurização de ~2 segundos e a linha permanece em 0 bar.",
                    "causas": ["Contatos internos do relé carbonizados.", "Bobina do relé aberta (sem clique ao acionar).", "Soquete do relé com pinos oxidados ou alargados."],
                    "roteiro": [
                        "1. Girar a chave sem dar partida e ouvir se a bomba pressuriza por ~2 s.",
                        "2. Trocar o relé suspeito por outro idêntico da caixa (ex.: relé da buzina) e testar.",
                        "3. Medir a bobina do relé (terminais 85–86): esperado 50–120 Ω; contatos (87–30): 0 Ω acionado, OL desligado.",
                        "4. Conferir a pressão na linha: esperado 3–4 bar em sistema flex."
                    ]
                }
            },
            "LEVE_FUSIVEL_ECU": {
                "nome": "Fusível de Alimentação da ECU / Injeção Rompido (U0100)",
                "peca": {"nome": "Fusível de lâmina — circuito da injeção", "referencia": "Fusível lâmina 15 A", "localizacao": "Caixa de fusíveis no cofre do motor", "imagem": "fusivel_lamina.png", "defeito": True},
                "dtc": [("U0100", "Perda de Comunicação com a ECU do Motor")],
                "rpm": 0, "g2_val": 1000, "stft": 0.0, "ltft": 0.0, "telemetria_scope": 0.45,
                "scope_amp": 0.01, "scope_freq": 0.1, "saude1": 15.0, "saude2": 10.0,
                "status1": "PONTO CRÍTICO - ECU sem alimentação", "status2": "PONTO CRÍTICO - Sem comunicação",
                "laudo": {
                    "titulo": "ECU MORTA: FUSÍVEL DA INJEÇÃO ABERTO",
                    "detalhes": "Sem alimentação, a ECU não gerencia centelha, bicos nem bomba: a luz da injeção pode nem acender e o scanner acusa perda de comunicação (U0100).",
                    "causas": ["Fusível de 15 A do circuito de injeção rompido.", "Curto no chicote (fio descascado encostando na massa).", "Bomba de combustível em curto derrubando o fusível."],
                    "roteiro": [
                        "1. Localizar o fusível da injeção/ECU na caixa do cofre e inspecionar o filamento.",
                        "2. Medir continuidade: fusível bom marca 0–1 Ω; queimado marca OL.",
                        "3. NUNCA substituir por amperagem maior — investigar o curto antes de trocar.",
                        "4. Com o fusível novo, monitorar se ele volta a queimar (curto intermitente no chicote)."
                    ]
                }
            },
            "LEVE_ATERRAMENTO": {
                "nome": "Mau Aterramento — Defeitos Fantasmas Intermitentes",
                "peca": {"nome": "Cabo e pontos de aterramento do motor/chassi", "referencia": "Cabo de massa 25 mm² — terminais olhal", "localizacao": "Entre o bloco do motor, o chassi e o polo negativo da bateria", "imagem": "cabo_aterramento.png", "defeito": True},
                "dtc": [("P0300", "Falha de Ignição Aleatória (intermitente)"), ("P0131", "Sonda Lambda — sinal baixo (intermitente)"), ("U0100", "Perda de comunicação (intermitente)")],
                "rpm": 850, "g2_val": 340, "stft": 6.5, "ltft": -4.0, "telemetria_scope": 0.45,
                "scope_amp": 0.30, "scope_freq": 3.5, "saude1": 55.0, "saude2": 50.0, "instavel": True,
                "status1": "Intermitente — sinal oscilando", "status2": "Intermitente — códigos que vão e voltam",
                "laudo": {
                    "titulo": "DEFEITOS FANTASMAS: MASSA RUIM GERA CÓDIGOS ALEATÓRIOS",
                    "detalhes": "Aterramento oxidado ou frouxo faz a referência de 0V da ECU flutuar: sensores leem errado, códigos aparecem e somem sozinhos e o motor falha de forma imprevisível.",
                    "causas": ["Ponto de massa do motor oxidado ou com tinta por baixo do terminal.", "Cabo de massa rompido internamente ou terminal frouxo.", "Massa da ECU compartilhada com acessórios de alto consumo."],
                    "roteiro": [
                        "1. Com motor ligado e acessórios acesos, medir a QUEDA DE TENSÃO entre o bloco e o negativo da bateria: ideal 0,00–0,20 V; acima de 0,50 V está ruim.",
                        "2. Desmontar os pontos de massa, lixar até o metal limpo e reapertar.",
                        "3. Conferir o cabo de massa da bateria ao chassi e do chassi ao motor.",
                        "4. Apagar os DTCs e rodar — o defeito fantasma some quando a massa volta a 0V."
                    ]
                }
            }
        }
    },
    "LINHA_PESADA": {
        "nome": "🚛 Linha Pesada (Caminhões e Ônibus Diesel Common Rail)",
        "gauge1_nome": "RPM MOTOR DIESEL", "g1_min": 0, "g1_max": 3000, "g1_passo": 500, "g1_unidade": "RPM",
        "gauge2_nome": "PRESSÃO COMMON RAIL", "g2_min": 0, "g2_max": 2200, "g2_passo": 400, "g2_unidade": "bar",
        "scope_nome": "Diferencial de Pressão do Filtro DPF (0 a 300 mbar)", "scope_min": 0.0, "scope_max": 300.0, "scope_unidade": "mbar",
        "veiculo": {"modelo": "Volvo FH 540 6x4 Globetrotter", "ano": "2021", "placa": "QWE7R45", "km": "342.000 km"},
        "referencias": [
            ("Baterias 24V (desligado)", "~25,0 – 25,6 V"),
            ("Baterias 24V (motor ligado)", "27,6 – 29,0 V"),
            ("Queda de tensão no aterramento", "ideal 0,00–0,20 V · máx. 0,50 V"),
            ("Fusível (continuidade)", "bom: 0–1 Ω · queimado: OL"),
            ("Relé — bobina (85–86)", "50 – 120 Ω"),
            ("Motor de partida (diesel)", "300 – 800 A"),
            ("Pressão common rail (lenta)", "250 – 400 bar"),
            ("Pressão common rail (carga)", "até 2.500 bar"),
            ("Bomba de alta (teste de partida)", "acima de 1.000 bar"),
            ("Diferencial DPF (lenta)", "abaixo de 180 mbar"),
        ],
        "indicador1": "Eficiência Sistema Redução SCR / Arla 32:", "indicador2": "Saúde do Sistema de Alta Pressão Rail:",
        "falhas": {
            "PESADA_NORMAL": {
                "nome": "Operação Normal (Common Rail Estável)",
                "peca": {"nome": "Jogo de injetores Common Rail", "referencia": "Bosch CRI 2.2", "localizacao": "No cabeçote, um injetor por cilindro", "imagem": "injetor_common_rail.png", "defeito": False},
                "dtc": [], "rpm": 650, "g2_val": 450, "stft": 0.0, "ltft": 0.0, "telemetria_scope": 25.0,
                "scope_amp": 3.0, "scope_freq": 0.5, "saude1": 96.0, "saude2": 98.0,
                "status1": "Saudável (Catalisador SCR ativo)", "status2": "Saudável (Rail nominal: 450 bar lenta)",
                "laudo": {
                    "titulo": "SISTEMA DIESEL EURO 5 / EURO 6 EM PERFEITA ORDEM",
                    "detalhes": "Pressão de rail em conformidade com o mapa da ECU. Filtro de partículas (DPF) desobstruído e bomba de reagente Arla dosando rigorosamente.",
                    "causas": ["Sem avarias na rede SAE J1939."],
                    "roteiro": ["Inspecionar nível de líquido no reservatório de Arla 32 e dreno do filtro separador de água (Sedimentador)."]
                }
            },
            "PESADA_RAIL_LEAK": {
                "nome": "Válvula MPROP Travada / Fuga no Rail (P0087)",
                "peca": {"nome": "Válvula reguladora MPROP", "referencia": "Bosch 0 928 400 724", "localizacao": "No corpo da bomba de alta pressão", "imagem": "valvula_mprop.png", "defeito": True},
                "dtc": [("P0087", "Pressão do Trilho de Combustível Insuficiente")],
                "rpm": 610, "g2_val": 220, "stft": 0.0, "ltft": 0.0, "telemetria_scope": 30.0,
                "scope_amp": 2.0, "scope_freq": 0.3, "saude1": 90.0, "saude2": 22.0,
                "status1": "Saudável", "status2": "PONTO CRÍTICO - Queda severa de pressão",
                "laudo": {
                    "titulo": "PRESSÃO INSUFICIENTE NO COLETOR DE ALTA (SUB-ALIMENTAÇÃO)",
                    "detalhes": "O caminhão apresenta perda severa de potência sob carga e desligamento súbito do motor em subidas fortes.",
                    "causas": [
                        "Válvula reguladora de vazão de combustível (MPROP/FCA) com micropartículas de limalha metálica travando o êmbolo.",
                        "Válvula mecânica de alívio limitadora do rail com assentamento cônico vazando para o retorno.",
                        "Bomba de engrenagens de baixa pressão sem sucção."
                    ],
                    "roteiro": [
                        "1. Instalar tampões nas saídas dos bicos injetores para teste de compressão máxima da bomba de alta (esperado: > 1000 bar em partida).",
                        "2. Medir o retorno de combustível dos injetores Common Rail em frascos graduados.",
                        "3. Checar presença de limalha de ferro no fundo do copo do filtro principal."
                    ]
                }
            },
            "PESADA_DPF_ENTUPIDO": {
                "nome": "Saturação Extrema de Fuligem no Filtro DPF (P2463)",
                "peca": {"nome": "Filtro de partículas DPF", "referencia": "OEM Euro 5", "localizacao": "Na linha de escape, após o catalisador DOC", "imagem": "filtro_dpf.png", "defeito": True},
                "dtc": [("P2463", "Restrição do Filtro de Partículas Diesel - Acúmulo de Fuligem")],
                "rpm": 660, "g2_val": 460, "stft": 0.0, "ltft": 0.0, "telemetria_scope": 210.0,
                "scope_amp": 8.0, "scope_freq": 0.8, "saude1": 30.0, "saude2": 85.0,
                "status1": "PONTO CRÍTICO - Risco de colapso térmico", "status2": "Saudável",
                "laudo": {
                    "titulo": "COLMÉIA DO ESCAPAMENTO TOTALMENTE OBSTRUÍDA",
                    "detalhes": "O diferencial de pressão do DPF ultrapassou 180 mbar em rotação baixa. O veículo aciona corte de torque de até 40% para preservar a turbina contra contrapressão excessiva.",
                    "causas": ["Uso contínuo em trechos urbanos sem atingir temperatura de auto-regeneração (600°C).", "Mangueiras de silicone do sensor delta de pressão rompidas."],
                    "roteiro": [
                        "1. Inspecionar as linhas de tomada de pressão pré e pós-filtro DPF.",
                        "2. Realizar procedimento de Regeneração Forçada de Bancada via comando de rotina do scanner.",
                        "3. Se a fuligem ultrapassar 100%, realizar limpeza química por fluxo reverso em máquina dedicada."
                    ]
                }
            },
            "PESADA_ATERRAMENTO": {
                "nome": "Mau Aterramento — Falhas Fantasmas na Rede J1939",
                "peca": {"nome": "Cabos de massa do chassi e da cabine", "referencia": "Cabo de massa 50 mm² — malha trançada", "localizacao": "Entre as baterias (24V), o chassi, a cabine e o bloco do motor", "imagem": "cabo_aterramento.png", "defeito": True},
                "dtc": [("SPN 639 / FMI 9", "Rede J1939 — comunicação intermitente"), ("SPN 110 / FMI 2", "Temperatura do arrefecimento — sinal errático")],
                "rpm": 650, "g2_val": 450, "stft": 0.0, "ltft": 0.0, "telemetria_scope": 25.0,
                "scope_amp": 25.0, "scope_freq": 1.2, "saude1": 60.0, "saude2": 55.0, "instavel": True,
                "status1": "Intermitente — módulos caindo da rede", "status2": "Intermitente — pressão oscilando no painel",
                "laudo": {
                    "titulo": "REDE J1939 CAINDO: MASSA RUIM DERRUBA MÓDULOS",
                    "detalhes": "Em sistema 24V, um ponto de massa ruim gera diferença de potencial entre módulos: a rede CAN/J1939 perde pacotes, o painel mostra valores pulando e códigos surgem sem causa real.",
                    "causas": ["Cintas de massa cabine–chassi rompidas ou oxidadas.", "Terminais das duas baterias em série com zinabre.", "Massa da ECU do motor fixada em chassi enferrujado."],
                    "roteiro": [
                        "1. Medir a queda de tensão entre o negativo das baterias e o bloco com a partida acionada: acima de 0,50 V reprova.",
                        "2. Limpar os terminais das baterias e reapertar as cintas de massa da cabine.",
                        "3. Verificar o ponto de massa dedicado da ECU no chassi.",
                        "4. Rodar com o scanner gravando a rede — os SPNs fantasmas devem parar."
                    ]
                }
            },
            "PESADA_FUSIVEL_ARLA": {
                "nome": "Fusível da Bomba Dosadora de Arla 32 Rompido (SPN 3361)",
                "peca": {"nome": "Fusível de lâmina — circuito do sistema SCR", "referencia": "Fusível lâmina 20 A", "localizacao": "Caixa de fusíveis da cabine / chassi", "imagem": "fusivel_lamina.png", "defeito": True},
                "dtc": [("SPN 3361 / FMI 5", "Bomba dosadora de Arla — circuito aberto")],
                "rpm": 640, "g2_val": 445, "stft": 0.0, "ltft": 0.0, "telemetria_scope": 28.0,
                "scope_amp": 3.0, "scope_freq": 0.5, "saude1": 18.0, "saude2": 92.0,
                "status1": "PONTO CRÍTICO - SCR sem dosagem (derate ativo)", "status2": "Saudável",
                "laudo": {
                    "titulo": "SCR PARADO: SEM ARLA, O MOTOR ENTRA EM DERATE",
                    "detalhes": "Com o fusível da bomba dosadora rompido, o sistema SCR não injeta Arla 32: o NOx dispara, a ECU registra o SPN e aplica corte progressivo de torque (derate) até o reparo.",
                    "causas": ["Fusível de 20 A do circuito da bomba dosadora rompido.", "Bomba dosadora travada por cristalização de ureia.", "Chicote do módulo SCR com curto."],
                    "roteiro": [
                        "1. Conferir o fusível do circuito SCR e medir continuidade (0–1 Ω bom / OL queimado).",
                        "2. Ouvir a bomba dosadora no ciclo de ignição — deve pressurizar a linha.",
                        "3. Inspecionar o bico dosador no escapamento por entupimento de cristais.",
                        "4. Após o reparo, rodar o teste de dosagem via scanner e zerar o contador de derate."
                    ]
                }
            }
        }
    },
    "LINHA_AGRICOLA": {
        "nome": "🚜 Maquinário Agrícola e Construção (Tratores, Colheitadeiras e Pás)",
        "gauge1_nome": "RPM DO MOTOR / PTO", "g1_min": 0, "g1_max": 2600, "g1_passo": 400, "g1_unidade": "RPM",
        "gauge2_nome": "PRESSÃO HIDRÁULICA", "g2_min": 0, "g2_max": 350, "g2_passo": 50, "g2_unidade": "bar",
        "scope_nome": "Temperatura Óleo Hidráulico e Transmissão (30°C - 130°C)", "scope_min": 30.0, "scope_max": 130.0, "scope_unidade": "°C",
        "veiculo": {"modelo": "John Deere 6155J", "ano": "2020", "placa": "FROTA 07", "km": "4.850 h"},
        "referencias": [
            ("Bateria (motor desligado)", "12,4 – 12,8 V"),
            ("Bateria (motor ligado)", "13,5 – 14,7 V"),
            ("Queda de tensão no aterramento", "ideal 0,00–0,20 V · máx. 0,50 V"),
            ("Fusível (continuidade)", "bom: 0–1 Ω · queimado: OL"),
            ("Relé — bobina (85–86)", "50 – 120 Ω"),
            ("Motor de partida (diesel)", "300 – 800 A"),
            ("Pressão hidráulica de trabalho", "150 – 300 bar"),
            ("Temperatura do óleo hidráulico", "faixa ideal 60–90 °C"),
        ],
        "indicador1": "Saúde do Sistema Hidráulico Principal:", "indicador2": "Eficiência da Admissão (Restrição de Poeira):",
        "falhas": {
            "AGRICOLA_NORMAL": {
                "nome": "Operação em Campo Nominal (Carga Normal)",
                "peca": {"nome": "Bomba hidráulica principal", "referencia": "Sauer Danfoss Série 90", "localizacao": "Acoplada à tomada de força do motor", "imagem": "bomba_hidraulica.png", "defeito": False},
                "dtc": [], "rpm": 1800, "g2_val": 210, "stft": 0.0, "ltft": 0.0, "telemetria_scope": 68.0,
                "scope_amp": 1.5, "scope_freq": 0.2, "saude1": 95.0, "saude2": 98.0,
                "status1": "Saudável (210 bar - Linha de trabalho)", "status2": "Saudável (Admissão limpa)",
                "laudo": {
                    "titulo": "SISTEMA HIDROSTÁTICO E MOTOR OPERANDO EM FAIXA IDEAL",
                    "detalhes": "Vazão da bomba hidráulica proporcional mantida, temperatura de transmissão controlada e motor diesel respondendo ao regulador isócrono de rotação.",
                    "causas": ["Nenhum alarme no monitor de bordo."],
                    "roteiro": ["Efetuar inspeção visual de engates rápidos e nível do visor de óleo hidráulico."]
                }
            },
            "AGRICOLA_SUPERAQUECIMENTO": {
                "nome": "Colmédias do Radiador Obstruídas por Palha / Cavacos (SPN 110)",
                "peca": {"nome": "Conjunto de radiadores", "referencia": "OEM", "localizacao": "Frontal do trator, atrás da grade", "imagem": "radiador_palha.png", "defeito": True},
                "dtc": [("SPN 110 / FMI 0", "Temperatura do Líquido de Arrefecimento Acima do Limite Crítico")],
                "rpm": 1650, "g2_val": 195, "stft": 0.0, "ltft": 0.0, "telemetria_scope": 118.0,
                "scope_amp": 2.0, "scope_freq": 0.3, "saude1": 55.0, "saude2": 40.0,
                "status1": "Atenção - Óleo degradando viscosidade", "status2": "PONTO CRÍTICO - Risco de travamento térmico",
                "laudo": {
                    "titulo": "SOBREAQUECIMENTO SEVERO POR FALTA DE TROCA TÉRMICA",
                    "detalhes": "A temperatura do motor ultrapassou 115°C e o circuito hidráulico entrou na zona de alerta (> 110°C), provocando cavitação de bomba e perda de força nos pistões da esteira/implemento.",
                    "causas": ["Colmeia do conjunto de radiadores (intercooler, água e óleo) obstruída por palha de colheita.", "Ventilador reversível (Cleanfix) com pás travadas ou hélice viscosa inoperante."],
                    "roteiro": [
                        "1. Parar o maquinário imediatamente em marcha lenta para desaceleração térmica sem desligar a chave.",
                        "2. Executar ciclo de reversão pneumática da hélice ou usar ar comprimido para bater de dentro para fora nas aletas.",
                        "3. Conferir nível e proporção de etilenoglicol no reservatório de expansão."
                    ]
                }
            },
            "AGRICOLA_FILTRO_AR": {
                "nome": "Restrição Crítica no Filtro de Ar Duplo Elemento (SPN 107)",
                "peca": {"nome": "Filtro de ar — elemento primário", "referencia": "Donaldson P781039", "localizacao": "Na caixa do filtro, lateral do capô", "imagem": "filtro_ar.png", "defeito": True},
                "dtc": [("SPN 107 / FMI 15", "Pressão Diferencial de Admissão de Ar Excessiva")],
                "rpm": 1720, "g2_val": 205, "stft": 0.0, "ltft": 0.0, "telemetria_scope": 74.0,
                "scope_amp": 1.0, "scope_freq": 0.2, "saude1": 90.0, "saude2": 15.0,
                "status1": "Saudável", "status2": "PONTO CRÍTICO - Vácuo excessivo na sucção",
                "laudo": {
                    "titulo": "RESTRIÇÃO POR POEIRA FINA NO ELEMENTO PRIMÁRIO",
                    "detalhes": "Sensor vacuômetro de ar acionou alarme no painel. O motor perde rendimento em alta rotação, gera fumaça preta no escape e consome excesso de diesel.",
                    "causas": ["Elemento primário de papel celulose saturado com terra vermelha/poeira de calcário.", "Válvula elastômero do ejetor de pó (Duckbill) ressecada ou entupida."],
                    "roteiro": [
                        "1. Sacar o elemento de ar primário e bater levemente (NUNCA soprar com ar de alta pressão direto que rompa os poros).",
                        "2. Checar integridade do elemento de segurança secundário.",
                        "3. Limpar o copo ciclônico e reinstalar as abraçadeiras sem deformações."
                    ]
                }
            },
            "AGRICOLA_RELE_PARTIDA": {
                "nome": "Relé do Motor de Partida Sem Acionamento (SPN 626)",
                "peca": {"nome": "Relé do motor de partida", "referencia": "Relé automotivo 12V 70 A — 4 pinos", "localizacao": "Caixa de relés próxima às baterias", "imagem": "rele_automotivo.png", "defeito": True},
                "dtc": [("SPN 626 / FMI 7", "Comando de partida — sem resposta mecânica")],
                "rpm": 0, "g2_val": 0, "stft": 0.0, "ltft": 0.0, "telemetria_scope": 62.0,
                "scope_amp": 1.0, "scope_freq": 0.2, "saude1": 92.0, "saude2": 95.0,
                "status1": "Saudável", "status2": "Saudável",
                "laudo": {
                    "titulo": "TRATOR NÃO VIRA: RELÉ DE PARTIDA NÃO ACIONA",
                    "detalhes": "Ao girar a chave, não há clique do relé nem giro do arranque: o circuito de comando do motor de partida está aberto no relé ou no seu soquete.",
                    "causas": ["Bobina do relé de partida aberta.", "Pinos do soquete alargados ou oxidados.", "Chave de ignição ou interruptor de neutro com mau contato."],
                    "roteiro": [
                        "1. Ouvir o clique do relé ao girar a chave — a ausência indica bobina aberta.",
                        "2. Fazer ponte temporária entre 30 e 87 do soquete para confirmar o arranque (somente para teste).",
                        "3. Medir a bobina (85–86): esperado 50–120 Ω.",
                        "4. Conferir o interruptor de ponto neutro / pedal de embreagem do circuito de partida."
                    ]
                }
            },
            "AGRICOLA_ATERRAMENTO": {
                "nome": "Mau Aterramento — Alarmes Fantasmas no Monitor",
                "peca": {"nome": "Cabos de massa do chassi e do motor", "referencia": "Cabo de massa 50 mm² — terminais olhal", "localizacao": "Entre as baterias, o chassi e o bloco do motor", "imagem": "cabo_aterramento.png", "defeito": True},
                "dtc": [("SPN 110 / FMI 2", "Temperatura do arrefecimento — sinal errático"), ("SPN 100 / FMI 2", "Pressão do óleo — sinal errático")],
                "rpm": 1800, "g2_val": 210, "stft": 0.0, "ltft": 0.0, "telemetria_scope": 68.0,
                "scope_amp": 12.0, "scope_freq": 1.0, "saude1": 60.0, "saude2": 65.0, "instavel": True,
                "status1": "Intermitente — leitura hidráulica oscilando", "status2": "Intermitente — sensores com sinal errático",
                "laudo": {
                    "titulo": "SENSORES LOUCOS NO CAMPO: MASSA RUIM GERA ALARMES FALSOS",
                    "detalhes": "Vibração e poeira afrouxam os pontos de massa do trator: o monitor acusa temperatura e pressão erráticas, o operador para a máquina à toa e nenhum defeito real existe.",
                    "causas": ["Terminais de massa com zinabre ou frouxos pela vibração.", "Cabo de massa esfarelado pelo atrito com o chassi.", "Ponto de massa pintado por cima na manutenção."],
                    "roteiro": [
                        "1. Medir a queda de tensão entre o negativo da bateria e o bloco com o motor ligado: acima de 0,50 V reprova.",
                        "2. Refazer os pontos de massa: lixar até o metal, aplicar graxa de cobre e reapertar.",
                        "3. Fixar o chicote para não roçar no chassi.",
                        "4. Limpar os SPNs e trabalhar — os alarmes fantasmas devem sumir."
                    ]
                }
            }
        }
    }
}


# =====================================================================
# 2. GAUGE MULTIESCALA DINÂMICO
# =====================================================================
class GaugeCircular(QWidget):
    def __init__(self, titulo="GAUGE", unidade="", min_val=0, max_val=8000, 
                 passo_ticks=1000, zonas_alerta=None, parent=None):
        super().__init__(parent)
        self.setMinimumSize(175, 175)
        self.titulo = titulo
        self.unidade = unidade
        self.min_val = min_val
        self.max_val = max_val
        self.passo_ticks = passo_ticks
        self.zonas_alerta = zonas_alerta or []

        self.ang_inicial = 150.0
        self.ang_varredura = 240.0
        self._valor_atual = min_val

        self.anim = QPropertyAnimation(self, b"valor")
        self.anim.setDuration(130)
        self.anim.setEasingCurve(QEasingCurve.OutQuad)

    def reconfigurar(self, titulo, unidade, min_v, max_v, passo, zonas):
        self.titulo = titulo
        self.unidade = unidade
        self.min_val = min_v
        self.max_val = max_v
        self.passo_ticks = passo
        self.zonas_alerta = zonas
        self._valor_atual = min_v
        self.update()

    def get_valor(self):
        return self._valor_atual

    def set_valor(self, val):
        self._valor_atual = max(self.min_val, min(self.max_val, val))
        self.update()

    valor = Property(float, get_valor, set_valor)

    def set_valor_alvo(self, val):
        val_c = max(self.min_val, min(self.max_val, val))
        if self.anim.state() == QPropertyAnimation.Running:
            self.anim.stop()
        self.anim.setStartValue(self._valor_atual)
        self.anim.setEndValue(val_c)
        self.anim.start()

    def _val_to_angulo(self, val):
        proporcao = (val - self.min_val) / max(1.0, (self.max_val - self.min_val))
        return self.ang_inicial + (proporcao * self.ang_varredura)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        lado = min(self.width(), self.height())
        cx = self.width() / 2.0
        cy = self.height() / 2.0
        raio = (lado / 2.0) - 12

        # Bezel escuro
        grad = QLinearGradient(cx, cy - raio, cx, cy + raio)
        grad.setColorAt(0.0, QColor("#1e1e24"))
        grad.setColorAt(1.0, QColor("#0e0e11"))
        painter.setBrush(QBrush(grad))
        painter.setPen(QPen(QColor("#2d2d38"), 2.2))
        painter.drawEllipse(QPointF(cx, cy), raio, raio)

        # Arcos de alerta
        ret_arco = QRectF(cx - raio + 10, cy - raio + 10, (raio - 10) * 2, (raio - 10) * 2)
        for inicio, fim, cor in self.zonas_alerta:
            ang_start = self._val_to_angulo(inicio)
            ang_end = self._val_to_angulo(fim)
            span = ang_end - ang_start
            pen_arco = QPen(cor, 4.0)
            pen_arco.setCapStyle(Qt.FlatCap)
            painter.setPen(pen_arco)
            painter.setBrush(Qt.NoBrush)
            painter.drawArc(ret_arco, int(-ang_start * 16), int(-span * 16))

        # Ticks e números
        painter.save()
        painter.translate(cx, cy)

        val = self.min_val
        while val <= self.max_val:
            ang = self._val_to_angulo(val)
            rad = math.radians(ang)
            p_ini = QPointF((raio - 14) * math.cos(rad), (raio - 14) * math.sin(rad))
            p_fim = QPointF((raio - 8) * math.cos(rad), (raio - 8) * math.sin(rad))
            painter.setPen(QPen(QColor("#707080"), 1.3))
            painter.drawLine(p_ini, p_fim)

            txt_x = (raio - 24) * math.cos(rad)
            txt_y = (raio - 24) * math.sin(rad) + 4
            painter.setFont(QFont("Segoe UI", 7, QFont.Bold))
            painter.setPen(QColor("#a5a5b5"))
            txt = str(int(val / 1000) if self.max_val >= 2000 and self.passo_ticks >= 1000 else int(val))
            painter.drawText(QRectF(txt_x - 12, txt_y - 7, 24, 14), Qt.AlignCenter, txt)
            val += self.passo_ticks

        # Título e Unidade
        painter.setFont(QFont("Segoe UI", 7, QFont.Bold))
        painter.setPen(QColor("#808092"))
        painter.drawText(QRectF(-60, -raio * 0.40, 120, 16), Qt.AlignCenter, self.titulo)

        painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
        painter.setPen(QColor("#ffffff"))
        painter.drawText(QRectF(-60, raio * 0.35, 120, 18), Qt.AlignCenter, f"{int(self._valor_atual)} {self.unidade}")

        # Agulha vermelha
        ang_ponteiro = self._val_to_angulo(self._valor_atual)
        painter.rotate(ang_ponteiro)

        caminho = QPainterPath()
        comp = raio - 20
        caminho.moveTo(-3, 0)
        caminho.lineTo(0, -comp)
        caminho.lineTo(3, 0)
        caminho.closeSubpath()

        painter.rotate(90)
        painter.setBrush(QBrush(QColor("#ff3b30")))
        painter.setPen(Qt.NoPen)
        painter.drawPath(caminho)

        painter.setBrush(QBrush(QColor("#2d2d38")))
        painter.setPen(QPen(QColor("#ff3b30"), 1.2))
        painter.drawEllipse(QPointF(0, 0), 5, 5)
        painter.restore()


# =====================================================================
# 3. THREAD MOTOR DE SIMULAÇÃO DINÂMICA
# =====================================================================
class MotorUniversalThread(QThread):
    telemetria_atualizada = Signal(float, float, float, float, float, float, float) # g1_val, g2_val, scope_val, saude1, saude2, stft, ltft

    def __init__(self):
        super().__init__()
        self.executando = True
        self.categoria_atual = "LINHA_LEVE"
        self.falha_atual = "LEVE_NORMAL"
        self.tempo = 0.0

    def definir_estado(self, categoria, falha):
        self.categoria_atual = categoria
        self.falha_atual = falha

    def run(self):
        while self.executando:
            cat_dict = BANCO_DEFEITOS.get(self.categoria_atual, BANCO_DEFEITOS["LINHA_LEVE"])
            falhas_dict = cat_dict["falhas"]
            f_dados = falhas_dict.get(self.falha_atual, list(falhas_dict.values())[0])

            self.tempo += 0.25

            # Dinâmica de variação realista
            g1_val = f_dados["rpm"] + 15 * math.sin(self.tempo * 0.8) + random.uniform(-5, 5)
            g2_val = f_dados["g2_val"] + 8 * math.sin(self.tempo * 0.5) + random.uniform(-3, 3)

            scope_val = f_dados["telemetria_scope"] + f_dados["scope_amp"] * math.sin(self.tempo * f_dados["scope_freq"]) + random.uniform(-0.02, 0.02)
            # Jitter leve p/ as barras de saúde parecerem telemetria ao vivo (limitado a 0-100)
            saude1 = max(0.0, min(100.0, f_dados["saude1"] + random.uniform(-1.5, 1.5)))
            saude2 = max(0.0, min(100.0, f_dados["saude2"] + random.uniform(-1.5, 1.5)))
            # Trim de combustível com pequena variação realista
            stft = f_dados["stft"] + random.uniform(-0.4, 0.4)
            ltft = f_dados["ltft"] + random.uniform(-0.3, 0.3)
            # Falhas de aterramento ("defeitos fantasmas"): telemetria instável,
            # com agulhas e valores oscilando de forma errática
            if f_dados.get("instavel"):
                g1_val += random.uniform(-80, 80)
                g2_val += random.uniform(-30, 30)
                stft += random.uniform(-6, 6)
                ltft += random.uniform(-4, 4)
                scope_val += random.uniform(-1, 1) * f_dados["scope_amp"]

            self.telemetria_atualizada.emit(g1_val, g2_val, scope_val, saude1, saude2, stft, ltft)
            self.msleep(180)

    def stop(self):
        self.executando = False
        self.wait()


def buscar_laudo_por_dtc(codigo):
    """Procura na base de conhecimento um laudo cujo DTC bata com o código lido do carro real."""
    alvo = (codigo or "").strip().upper()
    for cat in BANCO_DEFEITOS.values():
        for f in cat["falhas"].values():
            for cod, _desc in f.get("dtc", []):
                if cod.strip().upper() == alvo:
                    return f
    return None


# =====================================================================
# 3b. LEITOR OBD-II REAL (ELM327 via python-OBD)
# Emite o MESMO sinal da simulação, mas com dados lidos do carro de verdade.
# =====================================================================
class LeitorOBDThread(QThread):
    telemetria_atualizada = Signal(float, float, float, float, float, float, float) # g1_val, g2_val, scope_val, saude1, saude2, stft, ltft
    status_conexao = Signal(bool, str)   # conectado, mensagem
    dtcs_lidos = Signal(list)            # [(codigo, descricao), ...]
    veiculo_detectado = Signal(str)      # VIN

    def __init__(self, porta=None):
        super().__init__()
        self.executando = True
        self.porta = porta
        self.conn = None
        self._ok = deque([1] * 20, maxlen=20)

    def _parse_dtcs(self, resposta):
        itens = []
        for item in (resposta.value or []):
            if isinstance(item, (tuple, list)):
                cod = item[0]
                desc = item[1] if len(item) > 1 else ""
            else:
                cod = getattr(item, "code", str(item))
                desc = getattr(item, "description", "")
            itens.append((str(cod), str(desc)))
        return itens

    def ler_dtcs(self):
        """Lê os DTCs reais (Modo 03). Pode ser chamado da thread da UI (bloqueia ~1s)."""
        import obd as obd_lib
        try:
            r = self.conn.query(obd_lib.commands.GET_DTC)
            if r and not r.is_null():
                return self._parse_dtcs(r)
        except Exception:
            pass
        return []

    def run(self):
        try:
            import obd as obd_lib
            obd_lib.logger.setLevel(obd_lib.logging.WARNING)
        except ImportError:
            self.status_conexao.emit(False, "Biblioteca 'obd' não instalada. Rode: pip install obd")
            return
        try:
            self.conn = obd_lib.OBD(self.porta) if self.porta else obd_lib.OBD()
        except Exception as e:
            self.status_conexao.emit(False, f"Falha ao abrir a conexão: {e}")
            return
        if not self.conn.is_connected():
            self.status_conexao.emit(False, "ELM327 não encontrado. Plugue na OBD2 e pareie o Bluetooth.")
            return

        self.status_conexao.emit(True, f"Conectado em {self.conn.port_name()} ({self.conn.protocol_name()})")

        # VIN (Modo 09) para a ficha do veículo
        try:
            rv = self.conn.query(obd_lib.commands.VIN)
            vin = rv.value if (rv and not rv.is_null()) else ""
        except Exception:
            vin = ""
        self.veiculo_detectado.emit(str(vin or "não informado"))

        # DTCs iniciais (Modo 03)
        self.dtcs_lidos.emit(self.ler_dtcs())

        cmds = {
            "rpm": obd_lib.commands.RPM,                    # PID 0x0C
            "map": obd_lib.commands.INTAKE_PRESSURE,        # PID 0x0B (kPa)
            "o2": obd_lib.commands.O2_B1S1,                 # PID 0x14 (V)
            "stft": obd_lib.commands.SHORT_FUEL_TRIM_1,     # PID 0x06 (%)
            "ltft": obd_lib.commands.LONG_FUEL_TRIM_1,      # PID 0x08 (%)
        }
        while self.executando:
            vals = {}
            for nome, cmd in cmds.items():
                try:
                    r = self.conn.query(cmd)
                    if r is not None and not r.is_null():
                        vals[nome] = float(r.value.magnitude)
                        self._ok.append(1)
                    else:
                        self._ok.append(0)
                except Exception:
                    self._ok.append(0)
            qualidade = sum(self._ok) / len(self._ok) * 100.0
            g1_val = vals.get("rpm", 0.0)
            g2_val = vals.get("map", 0.0) * 10.0  # kPa -> mbar (escala do gauge)
            scope_val = vals.get("o2", 0.45)
            stft = vals.get("stft", 0.0)
            ltft = vals.get("ltft", 0.0)
            # Barras de "saúde" viram qualidade do enlace OBD-II no modo real
            self.telemetria_atualizada.emit(g1_val, g2_val, scope_val, qualidade, qualidade, stft, ltft)
            self.msleep(500)

    def stop(self):
        self.executando = False
        try:
            if self.conn and hasattr(self.conn, "close"):
                self.conn.close()
        except Exception:
            pass
        self.wait()


# =====================================================================
# 4. INTERFACE PRINCIPAL
# =====================================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Scanner e Simulador Universal de Injeção Eletrônica (Leve, Pesada e Agrícola)")
        self.resize(1180, 1090)
        self.setStyleSheet("""
            QMainWindow { background-color: #111114; }
            QGroupBox { color: #f0f0f5; font-weight: bold; border: 1px solid #282833; border-radius: 6px; margin-top: 8px; padding: 10px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 6px; }
            QLabel { color: #d0d0e0; font-size: 13px; }
            QComboBox { background-color: #1e1e26; color: #ffffff; border: 1px solid #363645; border-radius: 4px; padding: 6px 10px; font-weight: bold; font-size: 13px; }
            QComboBox::drop-down { border: none; }
            QPushButton { background-color: #2b5b84; color: white; border: none; padding: 8px 14px; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background-color: #3872a5; }
            QTextEdit { background-color: #09090b; color: #a9b7c6; border: 1px solid #22222a; font-family: Segoe UI, sans-serif; font-size: 13px; }
            QProgressBar { border: 1px solid #333; border-radius: 4px; text-align: center; color: white; font-weight: bold; height: 18px; }
        """)

        self.dados_grafico = deque([0.0] * 80, maxlen=80)
        self.modo_real = False
        self.thread_obd = None
        self._rel_antes = None
        self._rel_depois = None
        self._ultima_telemetria = None
        self._ultimos_dtcs_reais = []
        self._vin_real = ""
        self._ultimo_relatorio_html = ""
        self._construir_interface()

        self.simulador = MotorUniversalThread()
        self.simulador.telemetria_atualizada.connect(self.atualizar_telemetria)
        self.simulador.start()

        self.ao_trocar_categoria()

        # Checagem silenciosa de atualização 3s após abrir
        QTimer.singleShot(3000, lambda: self.verificar_updates(manual=False))

    def _construir_interface(self):
        central = QWidget()
        layout_raiz = QVBoxLayout(central)

        # Barra Superior de Seleção de Categoria e Falha
        painel_topo = QGroupBox("Painel de Seleção de Frota e Injeção de Falhas")
        lay_topo = QGridLayout(painel_topo)

        lay_topo.addWidget(QLabel("Categoria de Maquinário:"), 0, 0)
        self.cb_categoria = QComboBox()
        for k, v in BANCO_DEFEITOS.items():
            self.cb_categoria.addItem(v["nome"], k)
        self.cb_categoria.currentIndexChanged.connect(self.ao_trocar_categoria)
        lay_topo.addWidget(self.cb_categoria, 0, 1)

        lay_topo.addWidget(QLabel("Falha a Simular:"), 0, 2)
        self.cb_falhas = QComboBox()
        self.cb_falhas.currentIndexChanged.connect(self.ao_trocar_falha)
        lay_topo.addWidget(self.cb_falhas, 0, 3)

        self.btn_reset = QPushButton("Reset de Memória (Modo 04 / Limpar DTC)")
        self.btn_reset.setStyleSheet("background-color: #7b1fa2;")
        self.btn_reset.clicked.connect(self.reset_dtc)
        lay_topo.addWidget(self.btn_reset, 0, 4)

        # Linha 2: alternância Simulação x Carro Real (OBD-II)
        self.btn_modo = QPushButton("🎮 Modo: SIMULAÇÃO (clique p/ carro real)")
        self.btn_modo.clicked.connect(self.alternar_modo)
        lay_topo.addWidget(self.btn_modo, 1, 0, 1, 2)
        self.lbl_obd_status = QLabel("OBD-II: desconectado")
        self.lbl_obd_status.setStyleSheet("font-size: 12px; color: #8e8ea0;")
        lay_topo.addWidget(self.lbl_obd_status, 1, 2)
        self.btn_ler_dtc = QPushButton("↻ Ler DTCs (Modo 03)")
        self.btn_ler_dtc.clicked.connect(self._botao_ler_dtcs)
        self.btn_ler_dtc.setVisible(False)
        lay_topo.addWidget(self.btn_ler_dtc, 1, 3)

        # Linha 3: atualizador automático
        self.btn_update = QPushButton("🔄 Verificar atualizações")
        self.btn_update.clicked.connect(lambda: self.verificar_updates(manual=True))
        lay_topo.addWidget(self.btn_update, 2, 0, 1, 2)
        self.lbl_update_status = QLabel("")
        self.lbl_update_status.setStyleSheet("font-size: 12px; color: #8e8ea0;")
        lay_topo.addWidget(self.lbl_update_status, 2, 2, 1, 3)

        layout_raiz.addWidget(painel_topo)

        # Ficha do veículo em análise
        self.grp_veiculo = QGroupBox("Veículo em Análise")
        lay_veiculo = QHBoxLayout(self.grp_veiculo)
        self.lbl_veiculo = QLabel("—")
        self.lbl_veiculo.setStyleSheet("font-size: 13px;")
        lay_veiculo.addWidget(self.lbl_veiculo)
        layout_raiz.addWidget(self.grp_veiculo)

        # Painel Central: Gauges Circulares e Barras de Saúde
        painel_meio = QHBoxLayout()

        # Gauge 1 (RPM)
        self.grp_g1 = QGroupBox("Rotação")
        lay_g1 = QVBoxLayout(self.grp_g1)
        self.gauge1 = GaugeCircular(titulo="RPM", unidade="RPM", min_val=0, max_val=8000, passo_ticks=1000)
        lay_g1.addWidget(self.gauge1)
        painel_meio.addWidget(self.grp_g1)

        # Gauge 2 (Pressão variável: MAP, Common Rail ou Hidráulico)
        self.grp_g2 = QGroupBox("Pressão")
        lay_g2 = QVBoxLayout(self.grp_g2)
        self.gauge2 = GaugeCircular(titulo="PRESSÃO", unidade="bar", min_val=0, max_val=2200, passo_ticks=400)
        lay_g2.addWidget(self.gauge2)
        painel_meio.addWidget(self.grp_g2)

        # Barras de Saúde 0% a 100%
        grp_saude = QGroupBox("Status de Integridade dos Sensores")
        lay_saude = QVBoxLayout(grp_saude)

        self.lbl_ind1 = QLabel("Indicador 1:")
        lay_saude.addWidget(self.lbl_ind1)
        self.prog_ind1 = QProgressBar()
        self.prog_ind1.setRange(0, 100)
        lay_saude.addWidget(self.prog_ind1)
        self.lbl_status1 = QLabel("Status: Analisando...")
        self.lbl_status1.setStyleSheet("font-size: 11px; color: #8e8ea0;")
        lay_saude.addWidget(self.lbl_status1)

        lay_saude.addSpacing(6)

        self.lbl_ind2 = QLabel("Indicador 2:")
        lay_saude.addWidget(self.lbl_ind2)
        self.prog_ind2 = QProgressBar()
        self.prog_ind2.setRange(0, 100)
        lay_saude.addWidget(self.prog_ind2)
        self.lbl_status2 = QLabel("Status: Analisando...")
        self.lbl_status2.setStyleSheet("font-size: 11px; color: #8e8ea0;")
        lay_saude.addWidget(self.lbl_status2)

        lay_saude.addSpacing(6)

        lbl_trim_titulo = QLabel("Trim de Combustível (tempo real):")
        lbl_trim_titulo.setStyleSheet("font-weight: bold; color: #f0f0f5;")
        lay_saude.addWidget(lbl_trim_titulo)
        self.lbl_stft = QLabel("STFT: -- %")
        self.lbl_ltft = QLabel("LTFT: -- %")
        for _lbl in (self.lbl_stft, self.lbl_ltft):
            _lbl.setStyleSheet("font-size: 12px; font-family: Consolas, monospace; color: #8e8ea0;")
            lay_saude.addWidget(_lbl)

        painel_meio.addWidget(grp_saude)
        layout_raiz.addLayout(painel_meio)

        # Peça em análise (foto + ficha)
        self.grp_peca = QGroupBox("Peça em Análise")
        lay_peca = QHBoxLayout(self.grp_peca)
        self.lbl_foto = QLabel()
        self.lbl_foto.setFixedSize(200, 160)
        self.lbl_foto.setStyleSheet("background-color: #09090b; border: 1px solid #22222a; border-radius: 4px;")
        self.lbl_foto.setAlignment(Qt.AlignCenter)
        lay_peca.addWidget(self.lbl_foto)
        lay_info = QVBoxLayout()
        self.lbl_peca_nome = QLabel("—")
        self.lbl_peca_nome.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
        lay_info.addWidget(self.lbl_peca_nome)
        self.lbl_peca_ref = QLabel("—")
        self.lbl_peca_ref.setStyleSheet("font-size: 12px; color: #8e8ea0;")
        lay_info.addWidget(self.lbl_peca_ref)
        self.lbl_peca_local = QLabel("—")
        self.lbl_peca_local.setWordWrap(True)
        self.lbl_peca_local.setStyleSheet("font-size: 12px; color: #d0d0e0;")
        lay_info.addWidget(self.lbl_peca_local)
        self.lbl_peca_status = QLabel("—")
        self.lbl_peca_status.setStyleSheet("font-size: 13px; font-weight: bold;")
        lay_info.addWidget(self.lbl_peca_status)
        lay_info.addStretch()
        lay_peca.addLayout(lay_info, 1)
        layout_raiz.addWidget(self.grp_peca)

        # Osciloscópio / Gráfico Temporal
        self.grp_scope = QGroupBox("Osciloscópio de Diagnóstico")
        lay_scope = QVBoxLayout(self.grp_scope)
        self.plot_scope = pg.PlotWidget()
        self.plot_scope.setBackground('#09090b')
        self.plot_scope.showGrid(x=True, y=True, alpha=0.25)
        self.plot_scope.setMaximumHeight(160)
        self.curva_scope = self.plot_scope.plot(pen=pg.mkPen(color='#00e5ff', width=2))
        lay_scope.addWidget(self.plot_scope)
        layout_raiz.addWidget(self.grp_scope)

        # Laudo Técnico e Solução Guiada
        grp_laudo = QGroupBox("Laudo Técnico de Oficina & Roteiro de Reparo Passo a Passo")
        lay_laudo = QVBoxLayout(grp_laudo)
        self.txt_laudo = QTextEdit()
        self.txt_laudo.setReadOnly(True)
        self.txt_laudo.setMaximumHeight(200)
        lay_laudo.addWidget(self.txt_laudo)
        layout_raiz.addWidget(grp_laudo)

        # Relatório de serviço — Antes / Depois (PDF e impressão)
        grp_rel = QGroupBox("Relatório de Serviço — Antes / Depois")
        lay_rel = QHBoxLayout(grp_rel)
        self.btn_cap_antes = QPushButton("📸 Capturar ANTES")
        self.btn_cap_antes.clicked.connect(lambda: self._capturar_estado("antes"))
        lay_rel.addWidget(self.btn_cap_antes)
        self.btn_cap_depois = QPushButton("📸 Capturar DEPOIS")
        self.btn_cap_depois.clicked.connect(lambda: self._capturar_estado("depois"))
        lay_rel.addWidget(self.btn_cap_depois)
        self.btn_gerar_pdf = QPushButton("📄 Gerar PDF")
        self.btn_gerar_pdf.clicked.connect(self._gerar_pdf)
        lay_rel.addWidget(self.btn_gerar_pdf)
        self.btn_imprimir = QPushButton("🖨️ Imprimir")
        self.btn_imprimir.clicked.connect(self._imprimir_relatorio)
        lay_rel.addWidget(self.btn_imprimir)
        self.lbl_rel_status = QLabel("Nenhum estado capturado.")
        self.lbl_rel_status.setStyleSheet("font-size: 12px; color: #8e8ea0;")
        lay_rel.addWidget(self.lbl_rel_status, 1)
        layout_raiz.addWidget(grp_rel)
        self._atualizar_status_relatorio()

        self.setCentralWidget(central)

    def ao_trocar_categoria(self):
        cat_chave = self.cb_categoria.currentData()
        cat_dados = BANCO_DEFEITOS[cat_chave]

        # 1. Reconfigurar Manômetro 1
        self.grp_g1.setTitle(cat_dados["gauge1_nome"])
        self.gauge1.reconfigurar(
            cat_dados["gauge1_nome"], cat_dados["g1_unidade"],
            cat_dados["g1_min"], cat_dados["g1_max"], cat_dados["g1_passo"],
            [(0, int(cat_dados["g1_max"] * 0.7), QColor("#2ecc71")),
             (int(cat_dados["g1_max"] * 0.7), int(cat_dados["g1_max"] * 0.85), QColor("#f1c40f")),
             (int(cat_dados["g1_max"] * 0.85), cat_dados["g1_max"], QColor("#e74c3c"))]
        )

        # 2. Reconfigurar Manômetro 2
        self.grp_g2.setTitle(cat_dados["gauge2_nome"])
        self.gauge2.reconfigurar(
            cat_dados["gauge2_nome"], cat_dados["g2_unidade"],
            cat_dados["g2_min"], cat_dados["g2_max"], cat_dados["g2_passo"],
            [(cat_dados["g2_min"], int(cat_dados["g2_max"] * 0.6), QColor("#2ecc71")),
             (int(cat_dados["g2_max"] * 0.6), int(cat_dados["g2_max"] * 0.85), QColor("#f39c12")),
             (int(cat_dados["g2_max"] * 0.85), cat_dados["g2_max"], QColor("#e74c3c"))]
        )

        # 3. Reconfigurar Nomes dos Indicadores
        self.lbl_ind1.setText(cat_dados["indicador1"])
        self.lbl_ind2.setText(cat_dados["indicador2"])

        # 4. Reconfigurar Escala do Gráfico
        v = cat_dados.get("veiculo", {})
        self.lbl_veiculo.setText(
            f"🚗 <b>{v.get('modelo', '—')}</b> &nbsp;·&nbsp; Ano {v.get('ano', '—')}"
            f" &nbsp;·&nbsp; Placa {v.get('placa', '—')} &nbsp;·&nbsp; {v.get('km', '—')}"
        )
        self.grp_scope.setTitle(cat_dados["scope_nome"])
        self.plot_scope.setYRange(cat_dados["scope_min"], cat_dados["scope_max"])
        self.plot_scope.setLabel("left", "Valor", units=cat_dados.get("scope_unidade", ""))
        self.plot_scope.setLabel("bottom", "Amostras")
        self.dados_grafico.clear()
        self.dados_grafico.extend([cat_dados["scope_min"]] * 80)

        # 5. Atualizar Lista de Falhas
        self.cb_falhas.blockSignals(True)
        self.cb_falhas.clear()
        for k_falha, v_falha in cat_dados["falhas"].items():
            self.cb_falhas.addItem(v_falha["nome"], k_falha)
        self.cb_falhas.blockSignals(False)

        self.ao_trocar_falha()

    def ao_trocar_falha(self):
        cat_chave = self.cb_categoria.currentData()
        falha_chave = self.cb_falhas.currentData()
        if not falha_chave:
            return

        self.simulador.definir_estado(cat_chave, falha_chave)
        self.exibir_laudo(cat_chave, falha_chave)
        self.atualizar_peca(cat_chave, falha_chave)

    def _atualizar_trim(self, rotulo: QLabel, nome: str, valor: float):
        av = abs(valor)
        cor = "#2ecc71" if av < 5.0 else ("#f39c12" if av < 12.0 else "#e74c3c")
        rotulo.setText(f"{nome}: {valor:+.1f} %")
        rotulo.setStyleSheet(
            f"font-size: 12px; font-family: Consolas, monospace; color: {cor}; font-weight: bold;"
        )

    def _estilizar_barra(self, barra: QProgressBar, valor: float):
        barra.setValue(int(valor))
        if valor >= 80:
            cor = "#2ecc71"
        elif valor >= 50:
            cor = "#f39c12"
        else:
            cor = "#e74c3c"
        barra.setStyleSheet(f"QProgressBar::chunk {{ background-color: {cor}; border-radius: 3px; }}")

    def atualizar_telemetria(self, g1_val, g2_val, scope_val, saude1, saude2, stft=0.0, ltft=0.0):
        self._ultima_telemetria = (g1_val, g2_val, scope_val, saude1, saude2, stft, ltft)
        self.gauge1.set_valor_alvo(g1_val)
        self.gauge2.set_valor_alvo(g2_val)

        self._atualizar_trim(self.lbl_stft, "STFT", stft)
        self._atualizar_trim(self.lbl_ltft, "LTFT", ltft)

        self.dados_grafico.append(scope_val)
        self.curva_scope.setData(list(self.dados_grafico))

        self._estilizar_barra(self.prog_ind1, saude1)
        self._estilizar_barra(self.prog_ind2, saude2)

        # Obter descrições do estado atual
        if self.modo_real:
            # No carro real não há "falha simulada": só indica leitura ao vivo
            self.lbl_status1.setText("Status: 🔴 AO VIVO via OBD-II")
            self.lbl_status2.setText("Status: 🔴 AO VIVO via OBD-II")
            return
        cat_chave = self.cb_categoria.currentData()
        falha_chave = self.cb_falhas.currentData()
        if cat_chave and falha_chave:
            f_dados = BANCO_DEFEITOS[cat_chave]["falhas"].get(falha_chave)
            if f_dados:
                self.lbl_status1.setText(f"Status: {f_dados['status1']} ({saude1:.0f}%)")
                self.lbl_status2.setText(f"Status: {f_dados['status2']} ({saude2:.0f}%)")

    def _carregar_foto_peca(self, nome_arquivo: str):
        base = os.path.dirname(os.path.abspath(__file__))
        caminho = os.path.join(base, "pecas", nome_arquivo or "")
        if nome_arquivo and os.path.exists(caminho):
            pm = QPixmap(caminho)
            if not pm.isNull():
                return pm.scaled(self.lbl_foto.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        # Placeholder quando a foto ainda não existe
        pm = QPixmap(self.lbl_foto.size())
        pm.fill(QColor("#141418"))
        p = QPainter(pm)
        p.setPen(QColor("#8e8ea0"))
        p.setFont(QFont("Segoe UI", 11, QFont.Bold))
        p.drawText(pm.rect(), Qt.AlignCenter, "FOTO\nEM BREVE")
        p.end()
        return pm

    def atualizar_peca(self, cat_chave, falha_chave):
        f_dados = BANCO_DEFEITOS[cat_chave]["falhas"][falha_chave]
        peca = f_dados.get("peca", {})
        self.lbl_peca_nome.setText(peca.get("nome", "—"))
        self.lbl_peca_ref.setText(f"Referência: {peca.get('referencia', '—')}")
        self.lbl_peca_local.setText(f"Localização: {peca.get('localizacao', '—')}")
        if peca.get("defeito"):
            self.lbl_peca_status.setText("● COM DEFEITO")
            self.lbl_peca_status.setStyleSheet("font-size: 13px; font-weight: bold; color: #e74c3c;")
        else:
            self.lbl_peca_status.setText("● EM ANÁLISE — OK")
            self.lbl_peca_status.setStyleSheet("font-size: 13px; font-weight: bold; color: #2ecc71;")
        self.lbl_foto.setPixmap(self._carregar_foto_peca(peca.get("imagem", "")))

    def exibir_laudo(self, cat_chave, falha_chave):
        f_dados = BANCO_DEFEITOS[cat_chave]["falhas"][falha_chave]
        laudo = f_dados["laudo"]
        dtcs = f_dados["dtc"]

        html = "<div style='font-family: Arial; font-size: 13px; line-height: 1.5;'>"
        if not dtcs:
            html += "<p style='color: #2ecc71; font-weight: bold; font-size: 14px;'>[OK] SISTEMA LIVRE DE FALHAS NA MEMÓRIA DA ECU</p>"
        else:
            html += f"<p style='color: #e74c3c; font-weight: bold; font-size: 14px;'>[!] CÓDIGOS DE FALHA IDENTIFICADOS ({len(dtcs)} DTCs):</p>"
            for cod, desc in dtcs:
                html += f"&nbsp;&nbsp;&bull; <b style='color: #ffffff; background-color: #c0392b; padding: 2px 6px; border-radius: 3px;'>{cod}</b> - <span style='color: #ffffff;'>{desc}</span><br>"

        html += f"<p style='margin-top: 8px;'><b style='color: #3498db;'>DIAGNÓSTICO TÉCNICO:</b> {laudo['titulo']}</p>"
        html += f"<p style='color: #d1d1e0;'>{laudo['detalhes']}</p>"

        html += "<p style='color: #f1c40f; font-weight: bold; margin-bottom: 2px;'>CAUSAS PROVÁVEIS MAPEADAS:</p><ul>"
        for causa in laudo["causas"]:
            html += f"<li style='color: #e0e0e0;'>{causa}</li>"
        html += "</ul>"

        html += "<p style='color: #2ecc71; font-weight: bold; margin-bottom: 2px;'>ROTEIRO DE REPARO PASSO A PASSO:</p><ol>"
        for passo in laudo["roteiro"]:
            html += f"<li style='color: #e0e0e0;'>{passo}</li>"
        html += "</ol>"

        refs = BANCO_DEFEITOS[cat_chave].get("referencias", [])
        if refs:
            html += "<p style='color: #9b59b6; font-weight: bold; margin-bottom: 2px;'>VALORES DE REFERÊNCIA (MULTÍMETRO / SCANNER):</p>"
            html += "<table style='border-collapse: collapse; font-size: 12px;'>"
            for item, valor in refs:
                html += (
                    "<tr>"
                    f"<td style='color: #e0e0e0; padding: 2px 12px 2px 0; border-bottom: 1px solid #22222a;'>{item}</td>"
                    f"<td style='color: #00e5ff; font-family: Consolas, monospace; padding: 2px 0; border-bottom: 1px solid #22222a;'>{valor}</td>"
                    "</tr>"
                )
            html += "</table>"
        html += "</div>"

        self.txt_laudo.setHtml(html)

    def reset_dtc(self):
        if self.modo_real and self.thread_obd and self.thread_obd.conn:
            # Carro real: envia de verdade o comando Modo 04 (apagar DTCs)
            try:
                import obd as obd_lib
                self.thread_obd.conn.query(obd_lib.commands.CLEAR_DTC)
                dtcs = self.thread_obd.ler_dtcs()
                self._obd_dtcs(dtcs)
                self.txt_laudo.setHtml(
                    self.txt_laudo.toHtml().replace(
                        "</body>",
                        "<p style='color:#2ecc71;font-weight:bold;'>[+] Comando Modo 04 executado no veículo: DTCs apagados e luz de injeção desativada. Se a causa persistir, os códigos retornam.</p></body>",
                    )
                )
            except Exception as e:
                self.txt_laudo.setHtml(f"<p style='color:#e74c3c;font-weight:bold;'>Falha ao enviar o Modo 04: {e}</p>")
            return
        # Zera de verdade o estado visível da simulação: limpa o buffer do
        # osciloscópio e o laudo. A falha selecionada continua ativa (como numa
        # ECU real, o DTC pode retornar se a causa persistir).
        cat_chave = self.cb_categoria.currentData()
        base = BANCO_DEFEITOS.get(cat_chave, BANCO_DEFEITOS["LINHA_LEVE"])["scope_min"] if cat_chave else 0.0
        self.dados_grafico.clear()
        self.dados_grafico.extend([base] * 80)
        self.curva_scope.setData(list(self.dados_grafico))
        self.txt_laudo.setHtml("<p style='color: #2ecc71; font-weight: bold; font-size: 14px;'>[+] COMANDO EXECUTADO: Registros de falha apagados, lâmpadas de alerta desativadas e parâmetros autoadaptativos redefinidos.</p>")

    def closeEvent(self, event):
        try:
            self.simulador.stop()
        except Exception:
            pass
        if self.thread_obd:
            try:
                self.thread_obd.stop()
            except Exception:
                pass
        event.accept()

    # ------------------------- MODO REAL (OBD-II) -------------------------
    def alternar_modo(self):
        if not self.modo_real:
            # Entrar no modo carro real
            self.modo_real = True
            try:
                self.simulador.stop()
            except Exception:
                pass
            self.cb_categoria.setEnabled(False)
            self.cb_falhas.setEnabled(False)
            idx = self.cb_categoria.findData("LINHA_LEVE")  # PIDs OBD-II padrão: só linha leve
            if idx >= 0:
                self.cb_categoria.setCurrentIndex(idx)
            self.lbl_obd_status.setText("OBD-II: conectando ao ELM327…")
            self.lbl_obd_status.setStyleSheet("font-size: 12px; color: #f39c12;")
            self.grp_scope.setTitle("Osciloscópio — Sonda Lambda B1S1 (tempo real)")
            self.lbl_ind1.setText("Qualidade do enlace OBD-II:")
            self.lbl_ind2.setText("Qualidade do enlace OBD-II:")
            self.lbl_status1.setText("Status: 🔴 AO VIVO via OBD-II")
            self.lbl_status2.setText("Status: 🔴 AO VIVO via OBD-II")
            self.lbl_veiculo.setText("🚗 <b>Carro real — OBD-II</b> · lendo VIN…")
            self.txt_laudo.setHtml(
                "<p style='color:#f39c12;font-weight:bold;'>Conectando ao adaptador ELM327… "
                "plugue-o na porta OBD2 (embaixo do painel) e pareie o Bluetooth no PC.</p>"
            )
            self.thread_obd = LeitorOBDThread()
            self.thread_obd.telemetria_atualizada.connect(self.atualizar_telemetria)
            self.thread_obd.status_conexao.connect(self._obd_status)
            self.thread_obd.dtcs_lidos.connect(self._obd_dtcs)
            self.thread_obd.veiculo_detectado.connect(self._obd_veiculo)
            self.thread_obd.start()
            self.btn_modo.setText("🔴 Modo: CARRO REAL (clique p/ voltar à simulação)")
            self.btn_ler_dtc.setVisible(True)
            self.grp_peca.setVisible(False)  # peça é conceito da simulação
        else:
            # Voltar à simulação
            self.modo_real = False
            if self.thread_obd:
                try:
                    self.thread_obd.stop()
                except Exception:
                    pass
                self.thread_obd = None
            self.cb_categoria.setEnabled(True)
            self.cb_falhas.setEnabled(True)
            self.btn_ler_dtc.setVisible(False)
            self.grp_peca.setVisible(True)
            self.btn_modo.setText("🎮 Modo: SIMULAÇÃO (clique p/ carro real)")
            self.lbl_obd_status.setText("OBD-II: desconectado")
            self.lbl_obd_status.setStyleSheet("font-size: 12px; color: #8e8ea0;")
            self.simulador = MotorUniversalThread()
            self.simulador.telemetria_atualizada.connect(self.atualizar_telemetria)
            self.simulador.start()
            self.ao_trocar_categoria()

    def _obd_status(self, ok, msg):
        cor = "#2ecc71" if ok else "#e74c3c"
        self.lbl_obd_status.setText(f"OBD-II: {msg}")
        self.lbl_obd_status.setStyleSheet(f"font-size: 12px; color: {cor};")
        if not ok:
            self.txt_laudo.setHtml(
                f"<p style='color:#e74c3c;font-weight:bold;'>Falha na conexão OBD-II:</p>"
                f"<p style='color:#d0d0e0;'>{msg}</p>"
                "<p style='color:#8e8ea0;'>Dica: instale a lib com <b>pip install obd</b>, "
                "plugue o ELM327 na porta OBD2 e pareie o Bluetooth no PC antes de abrir o app.</p>"
            )

    def _obd_veiculo(self, vin):
        self._vin_real = vin
        self.lbl_veiculo.setText(f"🚗 <b>Carro real — OBD-II ao vivo</b> &nbsp;·&nbsp; VIN {vin}")

    def _botao_ler_dtcs(self):
        if self.modo_real and self.thread_obd and self.thread_obd.conn:
            self.txt_laudo.setHtml("<p style='color:#f39c12;font-weight:bold;'>Lendo DTCs (Modo 03)…</p>")
            self._obd_dtcs(self.thread_obd.ler_dtcs())

    def _obd_dtcs(self, dtcs):
        self._ultimos_dtcs_reais = list(dtcs or [])
        html = "<div style='font-family: Arial; font-size: 13px; line-height: 1.5;'>"
        html += "<p style='color:#e74c3c;font-weight:bold;font-size:14px;'>🔴 MODO REAL — LEITURA OBD-II AO VIVO (não é simulação)</p>"
        if not dtcs:
            html += "<p style='color:#2ecc71;font-weight:bold;'>[OK] NENHUM DTC ATIVO — a ECU não registra falhas no momento.</p>"
        else:
            html += f"<p style='color:#e74c3c;font-weight:bold;'>[!] DTCs REAIS LIDOS DO VEÍCULO ({len(dtcs)}):</p>"
            for cod, desc in dtcs:
                html += (
                    "&nbsp;&nbsp;&bull; "
                    f"<b style='color:#ffffff;background-color:#c0392b;padding:2px 6px;border-radius:3px;'>{cod}</b>"
                    f" - <span style='color:#ffffff;'>{desc or '—'}</span><br>"
                )
            html += "<hr style='border-color:#22222a;'>"
            for cod, _desc in dtcs:
                f = buscar_laudo_por_dtc(cod)
                if f:
                    laudo = f["laudo"]
                    html += f"<p style='color:#3498db;font-weight:bold;margin-bottom:2px;'>ROTEIRO PARA {cod} (base de conhecimento):</p>"
                    html += f"<p style='color:#d1d1e0;'><b>{laudo['titulo']}</b><br>{laudo['detalhes']}</p><ol>"
                    for passo in laudo["roteiro"]:
                        html += f"<li style='color:#e0e0e0;'>{passo}</li>"
                    html += "</ol>"
                else:
                    html += f"<p style='color:#8e8ea0;'>Sem roteiro cadastrado para {cod} na base do simulador.</p>"
        refs = BANCO_DEFEITOS["LINHA_LEVE"].get("referencias", [])
        if refs:
            html += "<p style='color:#9b59b6;font-weight:bold;margin-bottom:2px;'>VALORES DE REFERÊNCIA (MULTÍMETRO / SCANNER):</p>"
            html += "<table style='border-collapse:collapse;font-size:12px;'>"
            for item, valor in refs:
                html += (
                    "<tr>"
                    f"<td style='color:#e0e0e0;padding:2px 12px 2px 0;border-bottom:1px solid #22222a;'>{item}</td>"
                    f"<td style='color:#00e5ff;font-family:Consolas,monospace;padding:2px 0;border-bottom:1px solid #22222a;'>{valor}</td>"
                    "</tr>"
                )
            html += "</table>"
        html += "</div>"
        self.txt_laudo.setHtml(html)

    # ------------------------- RELATÓRIO ANTES / DEPOIS -------------------------
    def _montar_snapshot(self):
        agora = datetime.now().strftime("%d/%m/%Y %H:%M")
        g1, g2, _scope, s1, s2, stft, ltft = self._ultima_telemetria or (0, 0, 0, 0, 0, 0, 0)
        if self.modo_real:
            veiculo_txt = f"Carro real (OBD-II) — VIN {self._vin_real or 'não informado'}"
            falha_nome = "Leitura ao vivo (OBD-II)"
            dtcs = list(self._ultimos_dtcs_reais)
            blocos = []
            for cod, _desc in dtcs:
                f = buscar_laudo_por_dtc(cod)
                if f:
                    blocos.append((cod, f["laudo"]))
            if not blocos:
                blocos = [("", {"titulo": "Sem roteiro cadastrado para os DTCs lidos.",
                                "detalhes": "Os códigos foram registrados acima.",
                                "causas": [], "roteiro": []})]
            g2_un = "mbar"
        else:
            cat_chave = self.cb_categoria.currentData()
            falha_chave = self.cb_falhas.currentData()
            cat_dados = BANCO_DEFEITOS[cat_chave]
            f_dados = cat_dados["falhas"][falha_chave]
            v = cat_dados.get("veiculo", {})
            veiculo_txt = f"{v.get('modelo', '—')} {v.get('ano', '')} · Placa {v.get('placa', '—')} · {v.get('km', '')}"
            falha_nome = f_dados["nome"]
            dtcs = list(f_dados["dtc"])
            blocos = [("", f_dados["laudo"])]
            g2_un = cat_dados.get("g2_unidade", "")
        return {
            "quando": agora,
            "modo": "Carro Real (OBD-II)" if self.modo_real else "Simulação",
            "veiculo": veiculo_txt,
            "falha": falha_nome,
            "dtcs": dtcs,
            "leituras": [
                ("RPM", f"{g1:.0f}"),
                (f"Pressão ({g2_un})", f"{g2:.0f}"),
                ("STFT", f"{stft:+.1f} %"),
                ("LTFT", f"{ltft:+.1f} %"),
                ("Saúde 1", f"{s1:.0f} %"),
                ("Saúde 2", f"{s2:.0f} %"),
            ],
            "blocos": blocos,  # [(codigo, laudo_dict), ...]
            "resumo": f"{falha_nome} — {len(dtcs)} DTC(s) em {agora}",
        }

    def _capturar_estado(self, qual):
        snap = self._montar_snapshot()
        if qual == "antes":
            self._rel_antes = snap
        else:
            self._rel_depois = snap
        self._atualizar_status_relatorio()
        QMessageBox.information(self, "Relatório", f"Estado '{qual.upper()}' capturado:\n{snap['resumo']}")

    def _atualizar_status_relatorio(self):
        a = "✓" if self._rel_antes else "○"
        d = "✓" if self._rel_depois else "○"
        txt = f"ANTES {a}   |   DEPOIS {d}"
        if self._rel_antes:
            txt += f"     (ANTES: {self._rel_antes['resumo']})"
        if self._rel_depois:
            txt += f"     (DEPOIS: {self._rel_depois['resumo']})"
        self.lbl_rel_status.setText(txt)
        self.btn_gerar_pdf.setEnabled(bool(self._rel_antes and self._rel_depois))
        self.btn_imprimir.setEnabled(bool(self._ultimo_relatorio_html))

    def _secao_relatorio(self, titulo, cor, snap):
        h = f"<h2 style='color:{cor};border-bottom:2px solid {cor};'>{titulo}</h2>"
        h += f"<p><b>Data/hora:</b> {snap['quando']} &nbsp;·&nbsp; <b>Modo:</b> {snap['modo']}<br>"
        h += f"<b>Veículo:</b> {snap['veiculo']}<br><b>Condição:</b> {snap['falha']}</p>"
        h += "<p><b>Códigos de falha (DTC):</b></p>"
        if snap["dtcs"]:
            h += "<table border='1' cellspacing='0' cellpadding='4' width='100%'>"
            h += "<tr bgcolor='#eeeeee'><th>Código</th><th>Descrição</th></tr>"
            for cod, desc in snap["dtcs"]:
                h += f"<tr><td><b>{cod}</b></td><td>{desc or '—'}</td></tr>"
            h += "</table>"
        else:
            h += "<p style='color:#2e7d32;'><b>Nenhum DTC registrado.</b></p>"
        h += "<p><b>Leituras no momento da captura:</b></p>"
        h += "<table border='1' cellspacing='0' cellpadding='4' width='100%'>"
        h += "<tr bgcolor='#eeeeee'><th>Parâmetro</th><th>Valor</th></tr>"
        for nome, valor in snap["leituras"]:
            h += f"<tr><td>{nome}</td><td><b>{valor}</b></td></tr>"
        h += "</table>"
        for cod, laudo in snap["blocos"]:
            cab = f" — {cod}" if cod else ""
            h += f"<p><b>Laudo{cab}:</b> {laudo['titulo']}<br>{laudo['detalhes']}</p>"
            if laudo["causas"]:
                h += "<p><b>Causas prováveis:</b></p><ul>"
                for c in laudo["causas"]:
                    h += f"<li>{c}</li>"
                h += "</ul>"
            if laudo["roteiro"]:
                h += "<p><b>Roteiro de reparo executado:</b></p><ol>"
                for p in laudo["roteiro"]:
                    h += f"<li>{p}</li>"
                h += "</ol>"
        return h

    def _html_relatorio(self):
        a, d = self._rel_antes, self._rel_depois
        h = ("<html><body style='font-family:Arial;font-size:12pt;'>"
             "<h1 style='text-align:center;'>RELATÓRIO DE DIAGNÓSTICO E REPARO</h1>"
             "<p style='text-align:center;'>Comparativo <b>ANTES</b> x <b>DEPOIS</b> — Scanner Full</p>"
             f"<p><b>Veículo:</b> {a['veiculo']}</p><hr>")
        h += self._secao_relatorio("ANTES — COM FALHA", "#c0392b", a)
        h += "<br>"
        h += self._secao_relatorio("DEPOIS — REPARO CONCLUÍDO", "#2e7d32", d)
        h += "<br><h2>QUADRO COMPARATIVO</h2>"
        h += ("<table border='1' cellspacing='0' cellpadding='4' width='100%'>"
              "<tr bgcolor='#eeeeee'><th>Parâmetro</th><th>ANTES</th><th>DEPOIS</th></tr>")
        for (nome, va), (_n2, vd) in zip(a["leituras"], d["leituras"]):
            h += f"<tr><td>{nome}</td><td><b>{va}</b></td><td><b>{vd}</b></td></tr>"
        h += "</table>"
        h += (f"<br><p><i>Relatório gerado pelo Scanner Full em "
              f"{datetime.now().strftime('%d/%m/%Y %H:%M')}.</i></p>"
              "<br><br><table width='100%'><tr>"
              "<td>_________________________<br>Técnico responsável</td>"
              "<td>_________________________<br>Cliente</td>"
              "</tr></table></body></html>")
        return h

    def _gerar_pdf(self):
        if not (self._rel_antes and self._rel_depois):
            QMessageBox.warning(self, "Relatório", "Capture o ANTES e o DEPOIS primeiro.")
            return
        html = self._html_relatorio()
        caminho, _ = QFileDialog.getSaveFileName(self, "Salvar relatório PDF",
                                                 "relatorio_scanner_full.pdf", "PDF (*.pdf)")
        if not caminho:
            return
        try:
            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(caminho)
            printer.setPageSize(QPageSize(QPageSize.A4))
            doc = QTextDocument()
            doc.setDefaultFont(QFont("Arial", 12))
            doc.setHtml(html)
            doc.print_(printer)
            self._ultimo_relatorio_html = html
            self._atualizar_status_relatorio()
            QMessageBox.information(self, "Relatório", f"PDF salvo em:\n{caminho}")
        except Exception as e:
            QMessageBox.critical(self, "Relatório", f"Falha ao gerar o PDF:\n{e}")

    def _imprimir_relatorio(self):
        if not self._ultimo_relatorio_html:
            if not (self._rel_antes and self._rel_depois):
                QMessageBox.warning(self, "Relatório", "Capture o ANTES e o DEPOIS primeiro.")
                return
            self._ultimo_relatorio_html = self._html_relatorio()
        printer = QPrinter(QPrinter.HighResolution)
        dlg = QPrintDialog(printer, self)
        if dlg.exec() == QPrintDialog.Accepted:
            doc = QTextDocument()
            doc.setDefaultFont(QFont("Arial", 12))
            doc.setHtml(self._ultimo_relatorio_html)
            doc.print_(printer)
        self._atualizar_status_relatorio()

    # ------------------------- ATUALIZADOR -------------------------
    def verificar_updates(self, manual=True):
        self.lbl_update_status.setText("Verificando atualizações…")
        self.thread_update = ThreadVerificacaoUpdate()
        self.thread_update.resultado.connect(lambda t, v, m: self._update_resultado(t, v, m, manual))
        self.thread_update.start()

    def _update_resultado(self, tem_update, versao_remota, mensagem, manual):
        if tem_update:
            self.lbl_update_status.setText(f"⬆ {mensagem} Clique em 🔄 para instalar.")
            self.lbl_update_status.setStyleSheet("font-size: 12px; color: #f39c12; font-weight: bold;")
            if manual:
                r = QMessageBox.question(self, "Atualização", mensagem + "\n\nBaixar e instalar agora?",
                                         QMessageBox.Yes | QMessageBox.No)
                if r == QMessageBox.Yes:
                    self._instalar_update(versao_remota)
        else:
            self.lbl_update_status.setText(mensagem)
            self.lbl_update_status.setStyleSheet("font-size: 12px; color: #8e8ea0;")
            if manual:
                QMessageBox.information(self, "Atualização", mensagem)

    def _instalar_update(self, versao_remota):
        self.btn_update.setEnabled(False)
        self.thread_inst = ThreadInstalacaoUpdate(versao_remota)
        self.thread_inst.progresso.connect(self.lbl_update_status.setText)
        self.thread_inst.concluido.connect(self._update_concluido)
        self.thread_inst.start()

    def _update_concluido(self, ok, mensagem):
        self.btn_update.setEnabled(True)
        self.lbl_update_status.setText(mensagem.split("\n")[0])
        if ok:
            QMessageBox.information(self, "Atualização", mensagem)
        else:
            QMessageBox.critical(self, "Atualização", mensagem)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    janela = MainWindow()
    janela.show()
    sys.exit(app.exec())
