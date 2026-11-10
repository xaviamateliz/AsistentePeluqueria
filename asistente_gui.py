import os
import threading
import tkinter as tk
from tkinter import scrolledtext

from dotenv import load_dotenv
from google import genai
from google.genai import types

# ------------------------------------------------------------
# CONFIGURACIÓN
# ------------------------------------------------------------
# load_dotenv() carga las líneas del archivo .env como variables
# de entorno. os.getenv() lee después la variable API_KEY.
# Así la clave nunca queda escrita en el código ni en GitHub.
load_dotenv()
API_KEY = os.getenv("API_KEY")

MODELO = "gemini-3-flash-preview"
ARCHIVO_SERVICIOS = "servicios.txt"

# Variables de la animación "Respondiendo..."
pensando = False       # interruptor: True mientras esperamos a Gemini
id_animacion = None    # identificador de la próxima animación programada


# ------------------------------------------------------------
# LÓGICA DE LA IA
# ------------------------------------------------------------
def cargar_servicios():
    with open(ARCHIVO_SERVICIOS, "r", encoding="utf-8") as archivo:
        return archivo.read()


def crear_instrucciones():
    """Construye el prompt de sistema: define el rol del asistente,
    lo limita al tema de la peluquería e inyecta los datos."""
    servicios = cargar_servicios()
    return (
        "Eres el asistente virtual de una peluquería. "
        "Responde SOLO con la información de abajo. "
        "Si la pregunta no tiene relación con la peluquería, responde "
        "amablemente que solo puedes ayudar con temas de la peluquería. "
        "Si el dato no aparece en la información, di que no lo sabes. "
        "Responde en español, breve y en texto plano, sin asteriscos "
        "ni formato Markdown.\n\n"
        "INFORMACIÓN DE LA PELUQUERÍA:\n" + servicios
    )


def limpiar_texto(texto):
    """Por si el modelo devuelve Markdown, quitamos los asteriscos."""
    texto = texto.replace("**", "")
    texto = texto.replace("* ", "- ")
    return texto.strip()


def preguntar_a_gemini(pregunta):
    """Envía la pregunta a Gemini y devuelve solo el texto de la respuesta."""
    interaccion = cliente.interactions.create(
        model=MODELO,
        system_instruction=INSTRUCCIONES,
        input=pregunta,
    )
    # output_text extrae solo el texto de la respuesta, que por dentro
    # es un objeto equivalente a un JSON.
    return limpiar_texto(interaccion.output_text)


# ------------------------------------------------------------
# FUNCIONES DE LA INTERFAZ
# ------------------------------------------------------------
def animar_pensando(paso):
    global id_animacion

    if not pensando:
        return

    puntos = "." * (paso % 3 + 1)
    chat.config(state="normal")
    rango = chat.tag_ranges("pensando")  # ¿ya hay una línea de 'Respondiendo'?
    if rango:
        chat.delete(rango[0], rango[1])  # la borramos para escribirla de nuevo
    chat.insert(tk.END, "Respondiendo" + puntos + "\n\n", "pensando")
    chat.config(state="disabled")
    chat.see(tk.END)

    # Programamos el siguiente paso. after no bloquea la ventana.
    id_animacion = ventana.after(400, animar_pensando, paso + 1)


def quitar_pensando():
    """Detiene la animación y borra la línea 'Respondiendo...' del chat."""
    global pensando, id_animacion

    pensando = False
    if id_animacion is not None:
        ventana.after_cancel(id_animacion) 
        id_animacion = None

    chat.config(state="normal")
    rango = chat.tag_ranges("pensando")
    if rango:
        chat.delete(rango[0], rango[1])
    chat.config(state="disabled")


def mostrar_mensaje(texto, etiqueta):
    """Añade un mensaje al chat."""
    quitar_pensando()  # si había un 'Respondiendo...', lo quitamos
    chat.config(state="normal")
    chat.insert(tk.END, texto + "\n\n", etiqueta)
    chat.config(state="disabled")
    chat.see(tk.END)  # baja el scroll al último mensaje


def activar_boton():
    boton.config(state="normal")


def obtener_respuesta(pregunta):
    try:
        texto = preguntar_a_gemini(pregunta)
        ventana.after(0, mostrar_mensaje, "Asistente: " + texto, "asistente")
    except Exception as error:
        # Sin internet, clave incorrecta, timeout...: avisamos en vez de cerrar.
        mensaje = "Error al conectar con el asistente: " + str(error)
        ventana.after(0, mostrar_mensaje, mensaje, "error")
    finally:
        ventana.after(0, activar_boton)


def enviar(evento=None):
    """Se llama al pulsar el botón o la tecla Enter."""
    global pensando

    pregunta = entrada.get().strip()
    if pregunta == "":
        return

    mostrar_mensaje("Tú: " + pregunta, "usuario")
    entrada.delete(0, tk.END)
    boton.config(state="disabled")

    pensando = True                 # encendemos el interruptor
    animar_pensando(0)              # empieza el 'Respondiendo...'

    hilo = threading.Thread(target=obtener_respuesta, args=(pregunta,))
    hilo.daemon = True  # el hilo se cierra si cerramos la ventana
    hilo.start()


# ------------------------------------------------------------
# PROGRAMA PRINCIPAL
# ------------------------------------------------------------
INSTRUCCIONES = crear_instrucciones()
cliente = genai.Client(
    api_key=API_KEY,
    http_options=types.HttpOptions(timeout=30000),  # 30 sec si pasa, salta el except
)

ventana = tk.Tk()
ventana.title("Asistente de Peluquería Xavi")
ventana.geometry("600x500")

# ScrolledText incluye barra de scroll para respuestas largas
chat = scrolledtext.ScrolledText(ventana, wrap=tk.WORD, state="disabled")
chat.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
chat.tag_config("usuario", foreground="blue", font=("Arial", 10, "bold"))
chat.tag_config("asistente", foreground="green")
chat.tag_config("error", foreground="red")
chat.tag_config("pensando", foreground="gray", font=("Arial", 10, "italic"))

marco = tk.Frame(ventana)
marco.pack(padx=10, pady=(0, 10), fill=tk.X)

entrada = tk.Entry(marco, font=("Arial", 11))
entrada.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
entrada.bind("<Return>", enviar)  # Enter también envía
entrada.focus()

boton = tk.Button(marco, text="Enviar", command=enviar)
boton.pack(side=tk.RIGHT)

mostrar_mensaje("Bienvenido al Asistente de Peluquería.\n"
                "Escribe tu pregunta abajo y presiona 'Enviar'.", None)

if not API_KEY:
    mostrar_mensaje("No se encontró API_KEY. Revisa tu archivo .env.", "error")
    boton.config(state="disabled")

ventana.mainloop()