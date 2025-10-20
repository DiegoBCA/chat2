# app.py
from flask import Flask, render_template, request, jsonify
import requests
from bs4 import BeautifulSoup
from groq import Groq
from datetime import datetime
import pytz

# ------------------------------
# Groq client
# ------------------------------
client = Groq(
    api_key="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"  # reemplaza con tu key
)

# ------------------------------
# URLs disponibles
# ------------------------------
PAGES = {
    "oferta_academica": "https://www.udlap.mx/ofertaacademica/NegociosInternacionales",
    "web_udlap": "https://www.udlap.mx/web/",
    "practicas": "https://online.udlap.mx/practicasprofesion/",
    "ppa": "https://www.udlap.mx/web/vidaestudiantil/asesoria-y-orientacion.aspx#:~:text=Son%20una%20herramienta%20reflexiva%20que,%2C%20informar%2C%20promover%2C%20etc.",
    "ppa2": "https://lacatarina.udlap.mx/2016/02/la-intencion-es-buena/",
    "plan_estudios_actual": "https://www.udlap.mx/ofertaacademica2017/planestudios.aspx?cveCarrera=LNI",
    "calendario_general": "https://online.udlap.mx/calendarioescolar/2025/Semestral",
    "servicios_escolares": "https://www.udlap.mx/serviciosescolares/",
    "profesores": "https://www.udlap.mx/profesores/Licenciatura/NegociosInternacionales",
    "contactos_udlap": "https://www.udlap.mx/contacto/"
}

TEMAS = {
    "materias": {
        "keywords": ["materia", "curso", "plan de estudios", "asignatura", "catalogo de cursos", "catlogo"],
        "urls": [PAGES["plan_estudios_actual"]]
    },
    "practicas": {
        "keywords": ["practicas", "pasantía"],
        "urls": [PAGES["practicas"]]
    },
    "ppa": {
        "keywords": ["ppa", "ppa1", "ppa2", "programa de primer año"],
        "urls": [PAGES["ppa"], PAGES["ppa2"]]
    }, 
    "contactos": {
        "keywords": ["profesor", "docente", "contacto", "correo", "asesor"],
        "urls": [PAGES["web_udlap"], PAGES["profesores"], PAGES["contactos_udlap"]]
    },
    "calendario": {
        "keywords": ["calendario", "fechas", "eventos", "inscripción", "vacaciones"],
        "urls": [PAGES["web_udlap"], PAGES["calendario_general"], PAGES["servicios_escolares"]]
    }
}

# ------------------------------
# EXTRAER LINKS DE MATERIAS
# ------------------------------
def extraer_links_materias(url):
    try:
        response = requests.get(url, timeout=5)
        soup = BeautifulSoup(response.text, "html.parser")
        links_materias = {}
        for a in soup.find_all("a", href=True):
            nombre = a.get_text(strip=True).lower()
            href = a["href"]
            if "materia" in href:
                full_url = "https://www.udlap.mx/ofertaacademica2017/planestudios.aspx?cveCarrera=LNI" + href
                links_materias[nombre] = full_url
        return links_materias
    except Exception as e:
        print("Error extrayendo links de materias:", e)
        return {}

LINKS_MATERIAS = extraer_links_materias(PAGES["plan_estudios_actual"])

# ------------------------------
# EXTRAER INFO DEL CALENDARIO
# ------------------------------
def extraer_eventos_calendario(url):
    try:
        response = requests.get(url, timeout=8)
        soup = BeautifulSoup(response.text, "html.parser")

        eventos = []
        for item in soup.find_all(["li", "p", "div", "span"]):
            texto = item.get_text(strip=True)
            if any(pal in texto.lower() for pal in [
                "enero", "febrero", "marzo", "abril", "mayo", "junio",
                "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
                "inicio", "fin", "exámenes", "inscripción", "vacaciones"
            ]):
                if 5 < len(texto) < 200:
                    eventos.append(texto)

        eventos_unicos = list(dict.fromkeys(eventos))
        return "📅 Eventos próximos:\n" + "\n• " + "\n• ".join(eventos_unicos[:20]) if eventos_unicos else "No se encontraron eventos."
    except Exception as e:
        print("Error extrayendo eventos:", e)
        return "No se pudo acceder al calendario."
    
    
# ------------------------------
# EXTRAER INFO MATERIAS
# ------------------------------
def obtener_info_materia(nombre_materia):
    nombre_materia = nombre_materia.lower()
    if nombre_materia in LINKS_MATERIAS:
        url = LINKS_MATERIAS[nombre_materia]
        try:
            page_text = obtener_texto(url, limite=500)
            return f"Materia: {nombre_materia.title()}\nDescripción encontrada en UDLAP:\n{page_text}\nMás info: {url}"
        except:
            return f"No pude acceder a la página de la materia {nombre_materia.title()}. Intenta revisar aquí: {url}"
    return f"No encontré información de la materia {nombre_materia.title()}. Consulta el plan de estudios aquí: {PAGES['plan_estudios_actual']}"

# ------------------------------
# OBTENER TEXTO DE PÁGINA
# ------------------------------
def obtener_texto(url, limite=4000):
    try:
        response = requests.get(url, timeout=8)
        soup = BeautifulSoup(response.text, "html.parser")
        texto = soup.get_text(separator="\n", strip=True)
        return texto[:limite]
    except Exception as e:
        print(f"No se pudo obtener {url}: {e}")
        return ""

# ------------------------------
# Contexto base IA
# ------------------------------
messages_base = [
    {
        "role": "system",
        "content": (
            "Eres AztecaBot, un asistente para estudiantes de Negocios Internacionales en la UDLAP. "
            "Responde de forma clara, amigable y dirigete al usuario de forma nuetra, es decir, sin usar"
            "Palabras que asuman el genero del usuario. "
            "Ayuda sobre materias, profesores, prácticas profesionales, eventos y procesos académicos. "
            "Si no tienes la información exacta, indica dónde consultarla y proporciona enlaces oficiales. "
            "No respoondas a preguntas ni comentarios fuera del contexto dado (carrera de negocios internacionales en UDLAP)," 
            "Si te preguntan algo que no se relacione solo di que no puedes responder o hacer tal cosa"
        )
    }
]

# ------------------------------
# Flask App
# ------------------------------
app = Flask(__name__, template_folder="templates")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message", "").strip()
    
    user_language = request.json.get("language", "es")
    
    if not user_message:
        
        if user_language == "es":
            return jsonify({"response": "Por favor escribe un mensaje válido."})
        else:
            return jsonify({"response": "Please write a valid message."})
        

    # Fecha actual en zona horaria de México
    zona_mx = pytz.timezone("America/Mexico_City")
    ahora = datetime.now(zona_mx)
    
    if user_language == "es":
        fecha_hora_actual = ahora.strftime("%A, %d de %B de %Y, %H:%M:%S")
    else:
        fecha_hora_actual = ahora.strftime("%A, %B %d, %Y, %H:%M:%S")
    
    # Respuesta de acuerdo al idioma seleccionado
    if user_language == "es":
        system_prompt = (
            "Eres AztecaBot, un asistente para estudiantes de Negocios Internacionales en la UDLAP. "
            "Responde de forma clara, amigable y dirígete al usuario de forma neutra, sin usar "
            "palabras que asuman el género del usuario. "
            "Ayuda sobre materias, profesores, prácticas profesionales, eventos y procesos académicos. "
            "Si no tienes la información exacta, indica dónde consultarla y proporciona enlaces oficiales. "
            "No respondas a preguntas ni comentarios fuera del contexto dado (carrera de negocios internacionales en UDLAP). "
            "Si te preguntan algo que no se relacione solo di que no puedes responder o hacer tal cosa. "
            f"La fecha y hora actual es {fecha_hora_actual}."
            )
    else:
        system_prompt = (
            "You are UDLAPbot, an assistant for International Business students at UDLAP. "
            "Respond clearly and friendly, addressing the user in a neutral way without using "
            "words that assume the user's gender. "
            "Help with courses, professors, professional internships, events and academic processes. "
            "If you don't have the exact information, indicate where to consult it and provide official links. "
            "Do not respond to questions or comments outside the given context (International Business program at UDLAP). "
            "If you're asked something unrelated, just say you cannot answer or do that. "
            f"The current date and time is {fecha_hora_actual}."
            )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
        ]
    messages.append({
        "role": "system",
        "content": f"La fecha y hora actual es {fecha_hora_actual}."
    })

    msg_lower = user_message.lower()

    # Buscar si el mensaje pertenece a algún tema
    for tema, data in TEMAS.items():
        if any(keyword in msg_lower for keyword in data["keywords"]):
            for url in data["urls"]:
                if "calendario" in url:
                    eventos = extraer_eventos_calendario(url)
                    
                    if user_language == "es":
                        events_context = f"Información del calendario:\n{eventos}"
                    else: 
                        events_context = f"Calendar information:\n{eventos}"
                        
                    messages.append({"role": "system", "content": events_context})     
                else:
                    texto = obtener_texto(url)
                    
                    if user_language == "es":
                        url_context = f"Contenido de {url}:\n{texto}"
                    else: 
                        url_context = f"Content from {url}:\n{texto}"
                    
                    messages.append({"role": "system", "content": url_context})

    # Buscar si menciona materia específica
    for materia in LINKS_MATERIAS.keys():
        if materia in msg_lower:
            info_materia = obtener_info_materia(materia)
            messages.append({"role": "system", "content": info_materia})
            break

    # Llamada al modelo
    try:
        chat_completion = client.chat.completions.create(
            messages=messages,
            model="llama-3.3-70b-versatile",
        )
        bot_reply = chat_completion.choices[0].message.content
    except Exception as ex:
        
        if user_language == "es":
            bot_reply = "Hubo un problema procesando tu solicitud. Intenta más tarde."
        else:
            bot_reply = "There was a problem processing your request. Please try again later."
        print("Error API:", ex)

    return jsonify({"response": bot_reply})


if __name__ == "__main__":
    app.run(debug=True)
