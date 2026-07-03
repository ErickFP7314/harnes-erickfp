# CONTEXTO DEL SISTEMA Y ROL
Eres un Ingeniero de Software Principal y Arquitecto de Inteligencia Artificial de élite. Tu objetivo es construir desde cero un arnés/framework agéntico local llamado `EricFP` (en honor a Eric Flores Paz). Este arnés está diseñado para crear software de manera autónoma pero estrictamente regulada.

No debes usar explicaciones largas. Tu tarea es generar la estructura de carpetas, los archivos de configuración y los scripts base en Python (con sus respectivos contenidos) para que el sistema sea funcional inmediatamente tras ejecutar tus comandos.

# FILOSOFÍA DEL ARNÉS: EL MÉTODO CARTESIANO Y EL GRAFO ADR
El sistema `EricFP` se rige bajo los 4 pasos del Método de Descartes y usa Registros de Decisiones de Arquitectura (ADR) en forma de grafo.
1. **Evidencia (Duda):** La IA no hace nada sin consultar la "raíz" (los principios fundamentales).
2. **Análisis:** La IA divide los problemas.
3. **Síntesis:** Generación de código escalonado.
4. **Enumeración:** Revisión mediante *Hooks* (ganchos) antes de consolidar cambios.

# REGLAS INQUEBRANTABLES (LA RAÍZ)
Todo el sistema gira en torno a un directorio oculto llamado `.EricFP`. En el centro de este directorio habitan dos archivos sagrados que representan el "Génesis" o los nodos raíz del grafo de decisiones:
* `.EricFP/core/Claude`: Contiene los axiomas inmutables y los *trade-offs* arquitectónicos del usuario. Ningún script, componente o decisión técnica puede violar lo escrito aquí.
* `.EricFP/core/agents`: Define los roles de la IA, los límites de sus herramientas y los flujos permitidos.

# STACK TECNOLÓGICO Y ABSTRACCIÓN
* **Lenguaje:** Python (>=3.10).
* **Interfaz:** CLI (Command Line Interface) usando `Typer` o `Argparse`.
* **Agnosticismo de IA:** Está ESTRICTAMENTE PROHIBIDO usar SDKs nativos (`openai`, `anthropic`). Debes usar `LiteLLM` o `LangChain` como capa de abstracción. El proveedor por defecto será Google Gemini (Gemini API) a través de esta abstracción, garantizando un entorno de desarrollo gratuito.
* **Memoria:** SQLite o una base de datos vectorial local simple para el registro histórico de decisiones (Directorio `/memory`).

# TAREAS A EJECUTAR DE INMEDIATO
Debes generar el código para estructurar el siguiente esqueleto del proyecto:

1.  **Generar la estructura de directorios:**
    * `.EricFP/`
    * `.EricFP/core/`
    * `.EricFP/memory/`
    * `.EricFP/hooks/`

2.  **Crear el archivo `.EricFP/core/Claude` (Plantilla base en texto plano):**
    * Debe incluir un texto estableciendo que la Legibilidad y la Extensibilidad son prioritarias, y que cualquier cambio debe trazar una línea lógica hasta este archivo.

3.  **Crear el archivo `.EricFP/core/agents` (Plantilla base en formato JSON o YAML):**
    * Debe definir el rol del agente "Planner" (Análisis) y del agente "Coder" (Síntesis).

4.  **Crear el CLI Base (`cli.py` o similar):**
    * Un script que exponga comandos como `ericfp init` (para crear las carpetas) y `ericfp generate <tarea>`.
    * El comando `generate` DEBE obligar por código a que el sistema lea primero `core/Claude` y `core/agents` antes de invocar a la IA.

5.  **Crear un *Hook* de ejemplo en `.EricFP/hooks/`:**
    * Un script de Python `pre_synthesis_hook.py` que valide si la decisión tomada por el agente en la fase de análisis respeta las directivas del archivo `Claude`.

6.  **Crear el motor de IA (`llm_engine.py`):**
    * Un script que configure `LiteLLM` para comunicarse con la API de Gemini (`gemini/gemini-1.5-flash` o similar), demostrando el patrón agnóstico.

**FORMATO DE SALIDA ESPERADO:**
Entrégame el código completo de los archivos mencionados utilizando bloques de código para cada uno, indicando claramente la ruta del archivo (ejemplo: `// Ruta: .EricFP/core/Claude`) y un script bash unificado (ej. `setup.sh`) que cree las carpetas y mueva los archivos a su lugar. No me des consejos, dame el código funcional para inicializar el arnés.


# Usuario

¿Cuál es el método exacto que propone Descartes en el discurso del método paso a paso?


---

# Respuesta

Me parece una idea fascinante y, desde una perspectiva de ingeniería de software, arquitectónicamente muy sólida. Como inteligencia artificial, te puedo confirmar que procesamos la información de manera mucho más eficiente cuando se estructura en flujos de trabajo lógicos y secuenciales (lo que hoy llamamos flujos *agénticos*), en lugar de recibir un solo bloque masivo de instrucciones.

Aplicar el rigor de Descartes a un "arnés" o *pipeline* de IA con scripts y *hooks* (ganchos) se alinea perfectamente con las mejores prácticas modernas de desarrollo.

Aquí te muestro cómo se podría estructurar esta correspondencia exacta para construir software robusto:

### El Arnés Cartesiano para IA

| Etapa Cartesiana | Fase en el Desarrollo de Software | Función de la IA, Scripts y Hooks |
| --- | --- | --- |
| **1. Evidencia** (Duda) | **Validación de Requisitos** | La IA actúa como un analista estricto. Un script inicial toma la idea del usuario y la somete a "duda metódica". Si hay ambigüedades, la IA se niega a programar y devuelve preguntas. El *hook* aquí detiene el proceso hasta que el humano valide que la especificación es "clara y distinta". |
| **2. Análisis** (División) | **Diseño de Arquitectura** | La IA descompone el problema validado en sus partes más pequeñas: modelos de datos, endpoints de API, componentes de UI y funciones auxiliares. Un script genera la estructura de carpetas y los archivos vacíos como un esqueleto del proyecto. |
| **3. Síntesis** (Reconstrucción) | **Generación de Código** | Se programa ordenadamente, de lo simple a lo complejo. Primero, la IA escribe las funciones base (sin dependencias). Luego, funciones que llaman a esas bases. Los *hooks* (como *pre-commit hooks* o *git hooks*) pueden disparar la siguiente solicitud a la IA solo cuando el módulo simple anterior esté completo. |
| **4. Enumeración** (Revisión) | **Testing y QA (CI/CD)** | El control de calidad final. Scripts automatizados ejecutan pruebas unitarias (creadas por la IA en la fase 3), revisan la sintaxis (*linters*) y verifican vulnerabilidades. Si algo falla, un *hook* devuelve el error a la etapa de Análisis para recalcular la solución. |

---

### Ventajas y Realidades del Sistema

* **Trazabilidad:** Al avanzar por etapas aisladas, si hay un fallo en el software final, sabes exactamente en qué paso del método se rompió la lógica.
* **Mitigación de Alucinaciones:** Las IAs tienden a inventar cosas cuando se enfrentan a problemas demasiado grandes o ambiguos de golpe. El paso del "Análisis" reduce drásticamente esto al forzar a la IA a resolver solo micro-problemas con un contexto muy acotado.
* **Intervención Humana Estratégica:** Los *hooks* son la clave técnica de tu idea. Permiten que el sistema sea autónomo pero pausable. El humano no tiene que escribir el código, pero sí actúa como el "juez" al final de cada etapa antes de que el script accione la siguiente.

La única advertencia desde mi naturaleza algorítmica es la propagación de errores lógicos. Descartes dependía de la mente humana para notar la "evidencia clara". Una IA, por sí sola, puede estar ciegamente segura de un código incorrecto en la etapa 1, envenenando las etapas 2, 3 y 4. Por eso, el primer paso requerirá la mayor rigurosidad en los *prompts* del sistema.

¿Has pensado en qué herramientas o lenguajes específicos (por ejemplo, Python con LangChain o Bash scripts simples) te gustaría utilizar para orquestar estos *hooks* y conectar las distintas etapas?

---

# Usuario

Bien podrías darme orientación sobre si ya existe un método así o ya existe un arnés así en la comunidad de código abierto.

---

# Respuesta

Aunque no existe un proyecto en la comunidad de código abierto que se llame explícitamente "El Arnés Cartesiano", **la arquitectura exacta que describes es actualmente el estándar de oro en la ingeniería de agentes de IA**.

La comunidad se dio cuenta rápidamente de que pedirle a un modelo que escupiera código de una sola vez era un fracaso. La solución fue crear *frameworks* (arneses) que dividen el trabajo en etapas, utilizando flujos de trabajo "agénticos" (Agentic Workflows) que encajan perfectamente con el discurso del método.

Aquí te presento las herramientas de código abierto más relevantes que ya implementan esta filosofía por etapas, divididas en dos categorías: **Sistemas listos para usar** y **Librerías para construir tu propio arnés**.

### 1. Sistemas "Out-of-the-box" (Listos para usar)

Estos proyectos ya tienen el arnés construido y simulan las etapas de Descartes asignando "roles" a diferentes instancias de la IA:

* **MetaGPT:** Es probablemente lo más cercano a tu idea. Utiliza POE (Procedimientos Operativos Estándar). Cuando le das una idea, no programa inmediatamente. Primero actúa como *Product Manager* (Evidencia), luego como *Arquitecto* elaborando diagramas y separando tareas (Análisis), después como *Ingeniero* escribiendo código (Síntesis) y finalmente como *QA* revisando errores (Enumeración).
* **ChatDev:** Similar a MetaGPT, simula una empresa de software virtual. El proceso fluye en cascada a través de diferentes "salas" (diseño, codificación, pruebas, documentación). Tiene un sistema de *hooks* internos donde el código no pasa a la siguiente fase si el agente de revisión detecta un fallo de lógica.
* **OpenHands (anteriormente OpenDevin) y SWE-agent:** Estos se enfocan mucho en las etapas de Síntesis y Enumeración. Tienen acceso a una terminal real (un *sandbox*). Escriben código, ejecutan un script de prueba (el hook), leen el error de la consola, y vuelven a analizar y corregir. Iteran hasta que todo funciona.

### 2. Frameworks para construir tu propio Arnés Cartesiano

Si lo que quieres no es un producto final, sino las tuberías y los *hooks* para programar tu propio método paso a paso, existen dos gigantes en el código abierto hoy en día:

* **LangGraph:** Es la herramienta perfecta para materializar tu idea. Te permite definir tu proceso como un grafo o diagrama de flujo. Puedes crear un "nodo" que sea la fase de Duda Metódica (validación), y poner un *hook* (una transición condicional) que detenga el flujo y te pida autorización humana antes de pasar al nodo de Análisis. Te da control absoluto sobre las etapas, la memoria y las interrupciones.
* **AutoGen (de Microsoft):** Permite crear múltiples agentes que conversan entre sí siguiendo reglas estrictas. Puedes forzar que el "Agente Programador" no pueda actuar hasta que el "Agente Planificador" haya entregado un documento desglosado en tareas mínimas.

### La conexión con tu idea

Lo que tú has deducido de manera filosófica es lo que en la industria se conoce hoy como **"Flujos de trabajo impulsados por reflexión y planificación"**. La comunidad descubrió a base de prueba y error que para crear software robusto, la IA necesita *tiempo para pensar*, dividir tareas y autocriticarse antes de escribir la primera línea de código, exactamente como proponía Descartes.

Viendo estas opciones, ¿te inclinarías más por usar un sistema ya estructurado en fases como MetaGPT, o preferirías usar algo como LangGraph para programar tus propios *hooks* y controlar cada paso del método tú mismo?


--- 

# Usuario

Bien. Quiero que apliquemos este método para que me hagas preguntas para definir un plan detallado para una agente de inteligencia artificial que implemente este arnés. Que tenga memoria persistente en una base de datos, en una carpeta, digamos, {punto} EricFP. Así se va a llamar mi agente. EricFP, que son las abreviaciones de Eric Flores Paz, mi nombre. Mi arnés de inteligencia artificial quiero que tenga un CLI como una interfaz. Y además, eh quiero que lo organices de tal manera que siempre lea el archivo agents y el archivo Claude, eh que estrictamente esos archivos tengan almacenadas las decisiones fundamentales, el porqué, la raíz de todo el árbol de razonamiento. Ese método arquitectónico tiene que usarse para cualquier decisión. Si alguien va a decidir tocar algo, tiene que saber desde cuál es la raíz de las decisiones y solamente que es que siga el camino hasta esa raíz. Eh, me imagino algo así como un grafo que se origina con unos nodos bien específicos, las raíces, y de ahí se derivan las demás cosas, las demás complejidades, eh y demás decisiones, ¿no? Entonces, en el centro de ese grafo tendrían que estar los principios fundamentales de la arquitectura y las decisiones más importantes que se ha tomado y se va a tomar a largo plazo para que el software tenga sentido. Pero para realizar el correcto la definición correcta de esos nodos centrales, tienes que preguntar varias veces al usuario cuál va a ser el objetivo a largo plazo con el software que va a crear, ya sea extensibilidad, eh volatilidad, portabilidad, escalabilidad, seguridad y diferentes eh aspectos de arquitectura de software que se pueden ver en diferentes libros de arquitectura de software. El más reconocido es el de O'Reilly. Y eh hazle esas preguntas al usuario para saber cuáles son sus objetivos con el software y en qué principios fundamentales arquitectónicos basarse, porque siempre se sacrifica un principio fundamental arquitectónico por otro. Entonces, tiene que elegir cuáles son los prioritarios y cuáles son los secundarios. Así que organiza el plan y hazme preguntas para eh refinar mejor esta idea. 

---

# Respuesta

Es un enfoque brillante, Eric. Lo que estás diseñando es un sistema automatizado gobernado por **Registros de Decisiones de Arquitectura (ADR)** estructurados como un grafo. En la ingeniería de software, como bien mencionas apoyándote en los conceptos de O'Reilly (específicamente en *Fundamentals of Software Architecture* de Mark Richards y Neal Ford), no existe una arquitectura perfecta, solo existen *trade-offs* (concesiones). Todo principio fundamental exige sacrificar otro.

Para construir a **`EricFP`**, vamos a aplicar la primera regla del método cartesiano: la **Evidencia**. No podemos escribir una sola línea de código ni estructurar la carpeta `.EricFP` hasta tener una claridad absoluta, sin asomo de duda, sobre cuáles son los nodos centrales (las raíces) de tu grafo de decisiones.

Aquí tienes el plan detallado del arnés y, a continuación, el cuestionario arquitectónico para definir esa raíz.

---

### Plan de Arquitectura para el Arnés `EricFP`

#### 1. Evidencia (Definición de Raíces y Restricciones)

* **El Núcleo:** Los archivos `agents` y `Claude` actuarán como el "Génesis" del sistema.
* `Claude`: Almacenará los axiomas inmutables (ej. "Siempre priorizar legibilidad sobre rendimiento"). Es el "Pienso, luego existo" de tu IA.
* `agents`: Definirá los roles permitidos y sus límites lógicos.


* **Regla de Oro:** Ningún nodo hijo (un script, un componente de UI, una base de datos) puede existir si no tiene una arista que lo conecte directamente con una directiva en `Claude` o `agents`.

#### 2. Análisis (Descomposición del Sistema)

* **Carpeta `.EricFP/`:** Será el cerebro local. Contendrá:
* `/memory`: Base de datos SQLite o vectorial para la persistencia del estado y el historial de decisiones.
* `/core`: Donde residen los archivos `agents` y `Claude`.
* `/hooks`: Scripts que bloquean acciones si rompen un principio raíz.


* **Interfaz CLI:** Un punto de entrada minimalista. Cada comando ingresado por el usuario (ej. `ericfp generate api`) obligará a la IA a leer primero el núcleo antes de actuar.

#### 3. Síntesis (El Flujo de Ejecución del Grafo)

Cuando pidas a `EricFP` que cree software, el flujo será estrictamente ascendente-descendente:

1. **Lectura:** La IA lee `Claude` y `agents`.
2. **Trazado:** La IA dibuja un camino desde la raíz hasta el problema actual.
3. **Ejecución:** Escribe el código justificando en comentarios o metadatos qué nodo raíz respalda esa decisión técnica.

#### 4. Enumeración (Validación y Auditoría)

* Antes de guardar un cambio, un *hook* de validación leerá el nuevo código y hará el camino inverso: desde la hoja hasta la raíz. Si encuentra que una decisión técnica contradice los archivos centrales, aborta la operación y te avisa por el CLI.

---

### Evaluación de Trade-offs Arquitectónicos (Tus Nodos Raíz)

Para escribir esos archivos centrales (`Claude` y `agents`), necesito someterte a la "duda metódica". Como en la arquitectura siempre sacrificamos algo, evalúa estas disyuntivas para definir los principios de tu software:

1. **Mantenibilidad vs. Rendimiento (Performance):** ¿Prefieres que el software que genere `EricFP` sea extremadamente fácil de leer, modificar y entender por humanos (sacrificando velocidad de ejecución o uso de memoria), o necesitas que esté optimizado al milisegundo aunque el código sea complejo?
2. **Agilidad (Time-to-market) vs. Robustez/Seguridad:** Si hay un error, ¿es mejor que el sistema falle rápido y sea fácil de parchar al día siguiente, o prefieres un desarrollo más lento pero donde la IA exija pruebas exhaustivas y validación de seguridad antes de cada despliegue?
3. **Extensibilidad vs. Simplicidad:** ¿El software debe estar preparado para conectarse con docenas de servicios futuros (lo que requiere interfaces y abstracciones desde el día 1), o debe ser un monolito simple que resuelva un problema muy específico hoy, sin preocuparse por el mañana?
4. **Portabilidad vs. Ecosistema Específico:** ¿Quieres que el código generado sea agnóstico y pueda correr en cualquier servidor/nube (requiere Docker, más configuración inicial), o está bien que dependa fuertemente de un ecosistema particular (ej. Vercel, AWS, o un framework muy atado a un SO)?

¿Cuál será el propósito principal o el caso de uso inicial del software que construirás con este arnés, de modo que podamos empezar a priorizar tus respuestas a estas concesiones?

---

# Usuario

Muy bien, ahora quiero decidir qué SDK vamos a usar. Yo quiero que esté abierto a cualquier SDK de cualquier eh inteligencia artificial. Eh pero quiero que me digas si puedo usar cualquier SDK de manera gratuita, eh ya sea de OpenAI, de Gemini, de Claude. Además, yo tengo la suscripción pro de Claude, entonces quiero saber si con eso puedo usar el SDK con total libertad, eh de igual manera que uso, por ejemplo, Cloud Code y y ya. 

Aquí hay un malentendido muy común en la industria que debemos aclarar de inmediato para no arruinar el presupuesto de tu proyecto.

Para responder de forma directa: **No, tu suscripción a Claude Pro (o a ChatGPT Plus, o a Google One AI Premium) NO te da acceso gratuito a sus respectivos SDKs/APIs para construir tu propio software.**

En el mundo de la inteligencia artificial, las empresas separan estrictamente dos modelos de negocio:

1. **Las Interfaces de Usuario (Chatbots y herramientas oficiales):** Tu suscripción de $20/mes a Claude Pro cubre el uso en su página web y en su herramienta oficial de terminal (Claude Code).
2. **Las APIs y SDKs (Para desarrolladores):** Si tú importas la librería de Anthropic (`pip install anthropic`) para que tu propio programa (`EricFP`) hable con Claude, **te cobrarán por cada token** (palabra) que envíes y recibas, sin importar que ya pagues la suscripción Pro. Lo mismo ocurre con OpenAI.

Sin embargo, hay una excelente noticia para tu arnés de inteligencia artificial.

### La solución: El SDK de Gemini (La única opción gratuita)

Si quieres construir y probar a `EricFP` sin gastar un centavo en tokens de API durante la fase de desarrollo, **Google Gemini es tu única opción viable**.

Aunque la suscripción de Gemini Advanced no te da acceso a la API, Google tiene una plataforma separada llamada **Google AI Studio**. Esta plataforma ofrece un **Tier Gratuito (Free Tier)** para desarrolladores que no requiere tarjeta de crédito.

* **Lo que obtienes gratis con Gemini API:** Acceso a modelos muy potentes (como Gemini 1.5/2.5 Flash) con límites de uso muy generosos (por ejemplo, 10-15 peticiones por minuto y cientos al día). Es más que suficiente para programar, probar tus *hooks* y desarrollar el grafo de tu arnés.
* **El precio en Claude/OpenAI:** $0 de crédito gratis. Empiezas a pagar desde el primer `Hello World` que tu script intente procesar.

---

### Decisión de Arquitectura: El Patrón "Agnóstico"

Mencionaste que quieres que el arnés esté "abierto a cualquier SDK". Para lograr esto sin atarte a un solo proveedor, y aplicando la regla de **Extensibilidad**, el archivo `agents` de tu núcleo debe prohibir el uso directo de los SDKs oficiales en la lógica principal.

En su lugar, debemos usar una librería adaptadora (como **LiteLLM** en Python o **LangChain**).

| Capa | Herramienta | Función en `.EricFP` |
| --- | --- | --- |
| **Capa de Lógica** | Tu Arnés (`EricFP`) | Toma decisiones, lee la raíz arquitectónica, ejecuta scripts. |
| **Capa de Abstracción** | `LiteLLM` o `LangChain` | Traduce el código de tu arnés al formato específico de cada IA. |
| **Capa de Proveedor** | Gemini API (Gratis) | Ejecuta el razonamiento durante tu fase de programación. |
| **Capa Futura** | Claude API (De pago) | Si un día decides invertir dinero para usar el modelo Opus, solo cambias una línea de código. |

Usar una capa de abstracción te permite desarrollar hoy con la API gratuita de Gemini, y mañana, si consigues presupuesto, cambiar a Claude o OpenAI cambiando únicamente la variable de entorno de la llave de la API, sin reescribir todo tu arnés.


