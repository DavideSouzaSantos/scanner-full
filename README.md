# Scanner Full

Simulador e scanner OBD-II de injeção eletrônica — app desktop em Python (PySide6 + pyqtgraph).

- **3 linhas:** leve (Otto/Flex), pesada (diesel Common Rail) e agrícola
- **20 falhas simuladas** com telemetria animada, osciloscópio e laudo técnico com roteiro de reparo passo a passo
- **Modo carro real** via adaptador ELM327 (python-OBD): RPM, MAP, sonda lambda, STFT/LTFT, leitura de DTCs e VIN
- **Relatório antes/depois** em PDF, pronto para impressão e assinatura
- **Atualização automática:** o próprio app verifica e instala novas versões (botão 🔄 no topo)

## Instalação (Windows)

Baixe o `.zip` da versão mais recente, extraia e execute **`instalar.bat`**
(ele instala o Python se faltar, cria o ambiente e deixa um atalho na Área de Trabalho).

Ou manualmente:

```
pip install -r requirements.txt
python scanner_full.py
```

## Versão atual

Ver `VERSAO.txt` (o app também exibe e verifica sozinho).
