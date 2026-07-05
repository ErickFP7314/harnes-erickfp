# Slash Commands Specification

## Purpose

Comandos de control del REPL que se interceptan localmente, sin llegar nunca al modelo.

## Requirements

### Requirement: Comandos reconocidos /help /model /tools /clear

El REPL MUST reconocer `/help`, `/model`, `/tools` y `/clear` como comandos locales: `/help` lista comandos disponibles, `/model` muestra/permite cambiar el modelo activo, `/tools` lista las tools registradas, `/clear` limpia el historial de la sesión en curso.

#### Scenario: /help lista comandos

- GIVEN una sesión de chat activa
- WHEN el usuario escribe `/help`
- THEN el sistema muestra la lista de comandos disponibles y sus descripciones.

#### Scenario: /tools lista tools registradas

- GIVEN un tool-registry poblado
- WHEN el usuario escribe `/tools`
- THEN el sistema muestra el nombre de cada tool registrada, en el orden estable del registry.

#### Scenario: /clear limpia el historial

- GIVEN una sesión con turnos previos
- WHEN el usuario escribe `/clear`
- THEN el historial de la sesión en curso se vacía y el siguiente turno inicia sin contexto previo.

### Requirement: Entradas con "/" nunca se envían al modelo

Cualquier entrada del usuario que comience con `/` MUST ser interceptada por el REPL y resuelta localmente. El sistema MUST NOT reenviar esa entrada al Provider.

#### Scenario: Comando válido interceptado

- GIVEN el usuario escribe `/model`
- WHEN el REPL procesa la entrada
- THEN el comando se ejecuta localmente y ninguna llamada al Provider ocurre para ese turno.

#### Scenario: Comando desconocido

- GIVEN el usuario escribe `/foo` (comando no reconocido)
- WHEN el REPL procesa la entrada
- THEN el sistema MUST mostrar un mensaje de error local indicando comando desconocido, y MUST NOT enviar la entrada al Provider.
