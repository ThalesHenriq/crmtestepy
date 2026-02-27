import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from twilio.rest import Client  # Para WhatsApp via Twilio

# Arquivo para persistência do CRM
CRM_FILE = 'crm_data.json'

# Carregar dados existentes
def load_crm():
    if os.path.exists(CRM_FILE):
        with open(CRM_FILE, 'r') as f:
            return json.load(f)
    return {"clientes": {}, "interacoes": [], "campanhas": [], "templates": []}  # Adicionado "templates" para emails pré-definidos

# Salvar dados
def save_crm(data):
    with open(CRM_FILE, 'w') as f:
        json.dump(data, f)

# Função para enviar email (usando SMTP)
def enviar_email(destinatario, assunto, corpo, anexo=None, smtp_server='smtp.gmail.com', smtp_port=587, sender_email=None, sender_password=None):
    if not sender_email or not sender_password:
        raise ValueError("Configure o email e senha do remetente em st.secrets.")
    
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = destinatario
    msg['Subject'] = assunto

    msg.attach(MIMEText(corpo, 'plain'))

    if anexo:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(open(anexo, 'rb').read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename= {os.path.basename(anexo)}")
        msg.attach(part)

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, destinatario, text)
        server.quit()
        return True
    except Exception as e:
        return str(e)

# Função para enviar WhatsApp via Twilio
def enviar_whatsapp(destinatario, mensagem, twilio_sid=None, twilio_token=None, twilio_from=None):
    if not twilio_sid or not twilio_token or not twilio_from:
        raise ValueError("Configure as credenciais Twilio em st.secrets.")
    
    client = Client(twilio_sid, twilio_token)
    try:
        message = client.messages.create(
            from_=twilio_from,  # Ex: 'whatsapp:+14155238886'
            body=mensagem,
            to=destinatario  # Ex: 'whatsapp:+5511999999999'
        )
        return True
    except Exception as e:
        return str(e)

# Interface
st.title("CRM Simples - Gerenciamento de Clientes e Vendas com Automação de Marketing")

crm_data = load_crm()

# Tabs (adicionada nova tab para Enviar WhatsApp)
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs(["Adicionar Cliente", "Gerenciar Clientes", "Registrar Interação/Venda", "Relatórios", "Enviar Email", "Automação de Marketing", "Gerenciar Templates", "Enviar WhatsApp"])

with tab1:
    st.header("Adicionar Novo Cliente")
    nome_cli = st.text_input("Nome do Cliente", value="")
    email_cli = st.text_input("Email", value="")
    telefone_cli = st.text_input("Telefone (ex: +5511999999999 para WhatsApp)", value="")
    endereco_cli = st.text_input("Endereço", value="")
    status_cli = st.selectbox("Status", ["Lead", "Cliente Ativo", "Inativo", "Prospect"])

    if st.button("Adicionar Cliente"):
        if nome_cli.strip():
            cliente_id = str(len(crm_data["clientes"]) + 1)  # ID simples incremental
            crm_data["clientes"][cliente_id] = {
                "nome": nome_cli,
                "email": email_cli,
                "telefone": telefone_cli,
                "endereco": endereco_cli,
                "status": status_cli
            }
            save_crm(crm_data)
            st.success(f"Cliente '{nome_cli}' adicionado com ID {cliente_id}.")
        else:
            st.warning("Digite o nome do cliente.")

with tab2:
    st.header("Gerenciar Clientes")
    cliente_selec = st.selectbox("Selecione Cliente", options=[f"{id}: {info['nome']}" for id, info in crm_data["clientes"].items()] or ["Nenhum"], key="select_cliente_gerenciar")
    if cliente_selec != "Nenhum":
        cli_id = cliente_selec.split(":")[0]
        info = crm_data["clientes"][cli_id]

        # Editar campos
        novo_nome = st.text_input("Nome", value=info["nome"])
        novo_email = st.text_input("Email", value=info["email"])
        novo_telefone = st.text_input("Telefone", value=info.get("telefone", ""))
        novo_endereco = st.text_input("Endereço", value=info["endereco"])
        novo_status = st.selectbox("Status", ["Lead", "Cliente Ativo", "Inativo", "Prospect"], index=["Lead", "Cliente Ativo", "Inativo", "Prospect"].index(info["status"]))

        if st.button("Atualizar Cliente"):
            crm_data["clientes"][cli_id].update({
                "nome": novo_nome,
                "email": novo_email,
                "telefone": novo_telefone,
                "endereco": novo_endereco,
                "status": novo_status
            })
            save_crm(crm_data)
            st.success("Cliente atualizado!")

        if st.button("Remover Cliente"):
            del crm_data["clientes"][cli_id]
            # Remover interações relacionadas
            crm_data["interacoes"] = [i for i in crm_data["interacoes"] if i["cliente_id"] != cli_id]
            save_crm(crm_data)
            st.success("Cliente removido.")
            st.rerun()

with tab3:
    st.header("Registrar Interação ou Venda")
    cliente_inter = st.selectbox("Selecione Cliente", options=[f"{id}: {info['nome']}" for id, info in crm_data["clientes"].items()] or ["Nenhum"], key="select_cliente_interacao")
    if cliente_inter != "Nenhum":
        cli_id = cliente_inter.split(":")[0]
        tipo_inter = st.selectbox("Tipo de Interação", ["Ligação", "Email", "Reunião", "Venda", "Suporte", "WhatsApp"])
        nota_inter = st.text_area("Notas/Detalhes")
        valor_venda = st.number_input("Valor da Venda (se aplicável, R$)", min_value=0.0, value=0.0) if tipo_inter == "Venda" else 0.0

        if st.button("Registrar Interação"):
            data_atual = datetime.now().strftime("%Y-%m-%d %H:%M")
            interacao = {
                "cliente_id": cli_id,
                "data": data_atual,
                "tipo": tipo_inter,
                "nota": nota_inter,
                "valor": valor_venda
            }
            crm_data["interacoes"].append(interacao)
            save_crm(crm_data)
            st.success(f"Interação registrada para {crm_data['clientes'][cli_id]['nome']}.")

with tab4:
    st.header("Relatórios")
    # Relatório de Clientes
    st.subheader("Lista de Clientes")
    if crm_data["clientes"]:
        df_clientes = pd.DataFrame.from_dict(crm_data["clientes"], orient='index')
        st.dataframe(df_clientes)
    else:
        st.info("Nenhum cliente cadastrado.")

    # Relatório de Interações
    st.subheader("Histórico de Interações")
    if crm_data["interacoes"]:
        df_inter = pd.DataFrame(crm_data["interacoes"])
        df_inter['cliente_nome'] = df_inter['cliente_id'].apply(lambda x: crm_data["clientes"].get(x, {}).get("nome", "Desconhecido"))
        st.dataframe(df_inter[['cliente_nome', 'data', 'tipo', 'nota', 'valor']])

        total_vendas = df_inter[df_inter['tipo'] == "Venda"]['valor'].sum()
        st.write(f"**Total de Vendas:** R$ {total_vendas:.2f}")
    else:
        st.info("Nenhuma interação registrada.")

    # Exportar CSV
    if st.button("Exportar Relatório de Interações para CSV"):
        if crm_data["interacoes"]:
            df_inter.to_csv('crm_interacoes.csv', index=False)
            with open('crm_interacoes.csv', 'rb') as f:
                st.download_button("Baixar CSV", f, file_name="crm_interacoes.csv")
        else:
            st.warning("Nenhum dado para exportar.")

    # Relatório de Campanhas
    st.subheader("Histórico de Campanhas")
    if crm_data.get("campanhas"):
        df_camp = pd.DataFrame(crm_data["campanhas"])
        st.dataframe(df_camp)
    else:
        st.info("Nenhuma campanha registrada.")

    # Novo: Relatório de Templates
    st.subheader("Lista de Templates")
    if crm_data.get("templates"):
        df_temp = pd.DataFrame(crm_data["templates"])
        st.dataframe(df_temp[['nome', 'assunto']])
    else:
        st.info("Nenhum template cadastrado.")

with tab5:
    st.header("Enviar Email para Cliente")
    st.warning("Configure seu email e senha no st.secrets.toml para envio real. Ex: [secrets] sender_email = 'seuemail@gmail.com' sender_password = 'suasenha' (use app password para Gmail).")

    cliente_email = st.selectbox("Selecione Cliente", options=[f"{id}: {info['nome']} ({info['email']})" for id, info in crm_data["clientes"].items() if info.get('email')] or ["Nenhum"], key="select_cliente_email")
    if cliente_email != "Nenhum":
        cli_id = cliente_email.split(":")[0]
        destinatario = crm_data["clientes"][cli_id]["email"]
        
        # Selecionar Template
        template_selec = st.selectbox("Selecionar Template (opcional)", options=[t["nome"] for t in crm_data["templates"]] + ["Nenhum"], key="select_template_email")
        assunto = ""
        corpo = ""
        if template_selec != "Nenhum":
            temp = next(t for t in crm_data["templates"] if t["nome"] == template_selec)
            assunto = temp["assunto"]
            corpo = temp["corpo"]

        assunto = st.text_input("Assunto do Email", value=assunto)
        corpo = st.text_area("Corpo do Email", value=corpo)
        corpo = corpo.replace("[Nome do Cliente]", crm_data["clientes"][cli_id]["nome"])  # Personalização
        
        uploaded_file = st.file_uploader("Anexar Arquivo (opcional)", type=['pdf', 'jpg', 'png', 'txt'])
        anexo_path = None
        if uploaded_file:
            anexo_path = f"temp_{uploaded_file.name}"
            with open(anexo_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

        if st.button("Enviar Email"):
            try:
                sender_email = st.secrets["sender_email"]
                sender_password = st.secrets["sender_password"]
                resultado = enviar_email(destinatario, assunto, corpo, anexo_path, sender_email=sender_email, sender_password=sender_password)
                if resultado is True:
                    st.success(f"Email enviado para {destinatario}!")
                    # Registrar como interação
                    interacao = {
                        "cliente_id": cli_id,
                        "data": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "tipo": "Email",
                        "nota": f"Assunto: {assunto}\nCorpo: {corpo[:100]}..."
                    }
                    crm_data["interacoes"].append(interacao)
                    save_crm(crm_data)
                else:
                    st.error(f"Erro ao enviar: {resultado}")
            except KeyError:
                st.error("Credenciais de email não configuradas em st.secrets.")
            finally:
                if anexo_path and os.path.exists(anexo_path):
                    os.remove(anexo_path)

with tab6:
    st.header("Automação de Marketing - Campanhas de Email")
    st.info("Crie campanhas para envio em massa baseado em segmentos (ex: todos Leads). Os envios são on-demand; para automação real, integre com cron jobs ou serviços como Zapier.")

    nome_campanha = st.text_input("Nome da Campanha", value="Campanha Promocional")
    segmento = st.multiselect("Segmento (Status dos Clientes)", ["Lead", "Cliente Ativo", "Inativo", "Prospect"], default=["Lead"])
    
    # Selecionar Template para Campanha
    template_camp_selec = st.selectbox("Selecionar Template (opcional)", options=[t["nome"] for t in crm_data["templates"]] + ["Nenhum"], key="select_template_campanha")
    assunto_camp = ""
    corpo_camp = ""
    if template_camp_selec != "Nenhum":
        temp = next(t for t in crm_data["templates"] if t["nome"] == template_camp_selec)
        assunto_camp = temp["assunto"]
        corpo_camp = temp["corpo"]

    assunto_camp = st.text_input("Assunto do Email", value=assunto_camp)
    corpo_camp = st.text_area("Corpo do Email (use [Nome do Cliente] para personalizar)", value=corpo_camp)
    
    uploaded_camp_file = st.file_uploader("Anexar Arquivo à Campanha (opcional)", type=['pdf', 'jpg', 'png', 'txt'])
    anexo_camp_path = None
    if uploaded_camp_file:
        anexo_camp_path = f"temp_camp_{uploaded_camp_file.name}"
        with open(anexo_camp_path, "wb") as f:
            f.write(uploaded_camp_file.getbuffer())

    if st.button("Executar Campanha"):
        try:
            sender_email = st.secrets["sender_email"]
            sender_password = st.secrets["sender_password"]
            
            enviados = 0
            falhas = []
            for cli_id, info in crm_data["clientes"].items():
                if info["status"] in segmento and info.get("email"):
                    dest = info["email"]
                    corpo_pers = corpo_camp.replace("[Nome do Cliente]", info["nome"])
                    resultado = enviar_email(dest, assunto_camp, corpo_pers, anexo_camp_path, sender_email=sender_email, sender_password=sender_password)
                    if resultado is True:
                        enviados += 1
                        # Registrar interação
                        interacao = {
                            "cliente_id": cli_id,
                            "data": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "tipo": "Email Campanha",
                            "nota": f"Campanha: {nome_campanha}\nAssunto: {assunto_camp}"
                        }
                        crm_data["interacoes"].append(interacao)
                    else:
                        falhas.append(dest)
            
            save_crm(crm_data)
            # Registrar campanha
            campanha = {
                "nome": nome_campanha,
                "data": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "segmento": segmento,
                "enviados": enviados,
                "falhas": len(falhas)
            }
            crm_data["campanhas"].append(campanha)
            save_crm(crm_data)
            
            st.success(f"Campanha '{nome_campanha}' executada! Enviados: {enviados}. Falhas: {len(falhas)}.")
            if falhas:
                st.warning(f"Falhas em: {', '.join(falhas)}")
        except KeyError:
            st.error("Credenciais de email não configuradas em st.secrets.")
        finally:
            if anexo_camp_path and os.path.exists(anexo_camp_path):
                os.remove(anexo_camp_path)

with tab7:
    st.header("Gerenciar Templates de Email")
    st.subheader("Criar Novo Template")
    nome_temp = st.text_input("Nome do Template", value="")
    assunto_temp = st.text_input("Assunto Padrão", value="")
    corpo_temp = st.text_area("Corpo Padrão (use [Nome do Cliente] para personalizar)", value="Olá, [Nome do Cliente]!\n\nMensagem padrão.\n\nAtenciosamente,\nSua Empresa.")

    if st.button("Salvar Template"):
        if nome_temp.strip():
            crm_data["templates"].append({
                "nome": nome_temp,
                "assunto": assunto_temp,
                "corpo": corpo_temp
            })
            save_crm(crm_data)
            st.success(f"Template '{nome_temp}' salvo!")
        else:
            st.warning("Digite o nome do template.")

    st.subheader("Templates Existentes")
    if crm_data["templates"]:
        for i, temp in enumerate(crm_data["templates"]):
            st.write(f"**{temp['nome']}**: Assunto: {temp['assunto']}")
            st.text_area("Corpo", temp["corpo"], disabled=True)
            if st.button("Remover", key=f"rem_temp_{i}"):
                del crm_data["templates"][i]
                save_crm(crm_data)
                st.rerun()
    else:
        st.info("Nenhum template cadastrado.")

with tab8:
    st.header("Enviar Mensagem via WhatsApp")
    st.warning("Configure as credenciais Twilio no st.secrets.toml: [secrets] twilio_sid = 'seu_sid' twilio_token = 'seu_token' twilio_from = 'whatsapp:+numero_twilio'. Certifique-se de que o cliente tem telefone no formato 'whatsapp:+5511999999999'.")

    cliente_wa = st.selectbox("Selecione Cliente", options=[f"{id}: {info['nome']} ({info.get('telefone', 'Sem telefone')})" for id, info in crm_data["clientes"].items() if info.get('telefone')] or ["Nenhum"], key="select_cliente_whatsapp")
    if cliente_wa != "Nenhum":
        cli_id = cliente_wa.split(":")[0]
        destinatario = crm_data["clientes"][cli_id].get("telefone", "")
        if not destinatario.startswith("whatsapp:"):
            destinatario = f"whatsapp:{destinatario}"

        # Selecionar Template (reuso para WhatsApp, sem assunto)
        template_selec_wa = st.selectbox("Selecionar Template (opcional)", options=[t["nome"] for t in crm_data["templates"]] + ["Nenhum"], key="select_template_whatsapp")
        mensagem = ""
        if template_selec_wa != "Nenhum":
            temp = next(t for t in crm_data["templates"] if t["nome"] == template_selec_wa)
            mensagem = temp["corpo"]

        mensagem = st.text_area("Mensagem para WhatsApp", value=mensagem)
        mensagem = mensagem.replace("[Nome do Cliente]", crm_data["clientes"][cli_id]["nome"])  # Personalização

        if st.button("Enviar WhatsApp"):
            try:
                twilio_sid = st.secrets["twilio_sid"]
                twilio_token = st.secrets["twilio_token"]
                twilio_from = st.secrets["twilio_from"]
                resultado = enviar_whatsapp(destinatario, mensagem, twilio_sid=twilio_sid, twilio_token=twilio_token, twilio_from=twilio_from)
                if resultado is True:
                    st.success(f"Mensagem enviada para {destinatario} via WhatsApp!")
                    # Registrar como interação
                    interacao = {
                        "cliente_id": cli_id,
                        "data": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "tipo": "WhatsApp",
                        "nota": f"Mensagem: {mensagem[:100]}..."
                    }
                    crm_data["interacoes"].append(interacao)
                    save_crm(crm_data)
                else:
                    st.error(f"Erro ao enviar: {resultado}")
            except KeyError:
                st.error("Credenciais Twilio não configuradas em st.secrets.")
